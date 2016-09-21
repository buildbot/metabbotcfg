from __future__ import absolute_import, division, print_function

import inspect
import json
import logging
import socket
import sys
from datetime import datetime

from twisted import logger
from twisted.internet import endpoints, protocol, reactor, task
from twisted.protocols import basic
from zope import interface


class LogstashBaseFormatter(logging.Formatter):
    def __init__(self, prefix=None, message_type='Logstash', tags=None, fqdn=False):
        self.prefix = prefix
        self.message_type = message_type
        self.tags = tags if tags is not None else []

        if fqdn:
            self.host = socket.getfqdn()
        else:
            self.host = socket.gethostname()

    def get_debug_fields(self, record):
        failure = record['log_failure']

        try:
            traceback = failure.getTraceback()
        except Exception:
            traceback = u"(UNABLE TO OBTAIN TRACEBACK FROM EVENT)\n"

        innermost_frame = failure.frames.pop(0)
        fields = {
            'type': str(failure.type),
            'module': innermost_frame[0],
            'file': innermost_frame[1],
            'lineno': innermost_frame[2],
            'stack': failure.stack,
            'parents': failure.parents,
            'traceback': traceback,
        }

        return fields

    def get_extra_fields(self, record):
        fields = {}
        if sys.version_info < (3, 0):
            easy_types = (basestring, bool, dict, float, int, long, list, type(None))
        else:
            easy_types = (str, bool, dict, float, int, list, type(None))

        if self.prefix is not None:
            for key, value in record:
                if not key.startswith(self.prefix):
                    continue
                if isinstance(value, easy_types):
                    fields[key] = value
                else:
                    fields[key] = repr(value)
        else:

            # get every field that isn't prefixed with log_
            for key, value in record.items():
                if key.startswith('log_'):
                    continue
                if isinstance(value, easy_types):
                    fields[key] = value
                else:
                    fields[key] = repr(value)

        return fields

    @classmethod
    def format_source(cls, message_type, host, path):
        return "%s://%s/%s" % (message_type, host, path)

    @classmethod
    def format_timestamp(cls, time):
        tstamp = datetime.utcfromtimestamp(time)
        return tstamp.strftime("%Y-%m-%dT%H:%M:%S") + ".%03d" % (tstamp.microsecond / 1000) + "Z"

    @classmethod
    def get_namespace(cls, record):
        if 'log_namespace' in record:
            namespace = record['log_namespace']
        elif 'log_logger' in record:
            namespace = record['log_logger'].namespace
        else:
            namespace = '(UNABLE TO OBTAIN THE NAMESPACE)'
        return namespace

    @classmethod
    def serialize(cls, message):
        if sys.version_info < (3, 0):
            return json.dumps(message)
        else:
            return bytes(json.dumps(message), 'utf-8')


class LogstashFormatterVersion1(LogstashBaseFormatter):
    version = 1

    def format(self, record):
        # Create message dict
        message = {
            '@timestamp': self.format_timestamp(record['log_time']),
            '@version': self.version,
            'message': logger.formatEvent(record),
            'host': self.host,
            'path': record['log_stack'][-1][1],
            'tags': self.tags,
            'type': self.message_type,
            'levelname': record['log_level'].name,
            'logger': self.get_namespace(record),
        }

        # extra fields
        message.update(self.get_extra_fields(record))

        # exception infos
        if 'log_failure' in record:
            message.update(self.get_debug_fields(record))

        return self.serialize(message)


class LogstashClient(basic.LineReceiver):
    def connectionMade(self):
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError:
            pass

    def emit(self, event):
        self.sendLine(event)
        self.transport.loseConnection()
        self.factory.eventEmitted(event)


class LogstashFactory(protocol.ReconnectingClientFactory):
    protocol = LogstashClient

    def __init__(self):
        self.clientRequests = []
        self.eventRequests = []
        self.connected = False

    def connectionMade(self, protocol):
        ds = self.clientRequests
        self.clientRequests = []
        for d in ds:
            d.callback(protocol)

    def eventEmitted(self, event):
        ds = self.eventRequests
        self.eventRequests = []
        for d in ds:
            d.callback(event)


# start the logging factory once, it will reconnect automatically
_factory = LogstashFactory()


@interface.implementer(logger.ILogObserver)
class LogstashLogObserver(object):
    def __init__(self, host, port=5959, prefix=None, message_type='logstash',
                 tags=None, fqdn=False):
        self.host = host
        self.port = port
        formatter = LogstashFormatterVersion1
        self.formatter = formatter(prefix, message_type, tags, fqdn)

    def __call__(self, event):
        if 'log_namespace' in event and "LogstashFactory" in event['log_namespace']:
            return
        with open("test.log", "a") as f:
            f.write(repr(event) + "\n")
        # log_ prefix is the one used by twisted, risk of collision...
        # see https://twistedmatrix.com/documents/15.2.1/core/howto/logger.html
        event['log_stack'] = inspect.stack()
        event = self.formatter.format(event)
        d = task.deferLater(reactor, 0, self._connect, reactor)
        d.addCallback(lambda client, event: client.emit(event), event)

    def _connect(self, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        endpoint = endpoints.TCP4ClientEndpoint(reactor, self.host, self.port)
        return endpoint.connect(_factory)
