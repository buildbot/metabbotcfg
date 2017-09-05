import json
import os
import random
import string

from buildbot.plugins import worker, util


class MyWorkerBase(object):
    # true if this box is buildbot.net, and can build docs, etc.
    buildbot_net = False

    # true if this box should use a 'simple' factory, meaning no virtualenv
    # (basically good for windows)
    use_simple = False

    # true if this box can test the buildmaster and worker, respectively
    test_master = True
    test_worker = True

    # true if this worker should have a single-worker builder of its own
    run_single = True

    # true if this host has PyQt4 installed in its default python
    pyqt4 = False

    # true if this worker can contribute to the virtualenv-managed pool of
    # specific-configuration builders.  Specific supported python versions
    # are given, too
    run_config = False
    py26 = False
    py27 = False
    pypy17 = False
    pypy18 = False

    tw0810 = False
    tw0900 = True
    tw1020 = True
    tw1110 = True
    tw1220 = True
    tw1320 = True
    tw1400 = True

    # true if this has nodejs installed, suitable for www
    nodejs = False

    # dictionary mapping databases to the env vars required to make them go
    databases = {}

    # operating system, for os-specific builders; this should only be used
    # for fleets of machines that are basically interchangebale
    os = None

    def extract_attrs(self, name, **kwargs):
        self.name = name
        remaining = {}
        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])
            else:
                remaining[k] = kwargs[k]
        return remaining

    def get_random_pass(self):
        return ''.join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(20))

    def get_pass(self, name):
        # get the password based on the name
        path = os.path.join(os.path.dirname(__file__), "%s.pass" % name)
        if not os.path.exists(path):
            print "warning {} does not exit. creating one".format(path)
            pw = self.get_random_pass()
            with open(path, 'w') as f:
                f.write(pw)

        pw = open(path).read().strip()
        return pw

    def get_ec2_creds(self, name):
        path = os.path.join(os.path.dirname(__file__), "%s.ec2" % name)
        return open(path).read().strip().split(" ")


class MyWorker(MyWorkerBase, worker.Worker):
    def __init__(self, name, **kwargs):
        password = self.get_pass(name)
        kwargs = self.extract_attrs(name, **kwargs)
        worker.Worker.__init__(self, name, password, **kwargs)


class MyLocalWorker(MyWorkerBase, worker.LocalWorker):

    def __init__(self, name, **kwargs):
        kwargs = self.extract_attrs(name, **kwargs)
        return worker.LocalWorker.__init__(
            self,
            name,
            **kwargs)


if not hasattr(worker, 'HyperLatentWorker'):
    MyHyperWorker = MyLocalWorker
else:
    class MyHyperWorker(MyWorkerBase, worker.HyperLatentWorker):
        creds = json.load(open(os.path.join(os.path.dirname(__file__), "hyper.pass")))

        def __init__(self, name, **kwargs):
            kwargs = self.extract_attrs(name, **kwargs)
            return worker.HyperLatentWorker.__init__(
                self,
                name, str(self.get_random_pass()),
                hyper_host="tcp://us-west-1.hyper.sh:443", image=util.Interpolate("%(prop:DOCKER_IMAGE:-buildbot/metabbotcfg)s"),
                hyper_accesskey=self.creds['access_key'], hyper_secretkey=self.creds['secret_key'],
                hyper_size=util.Interpolate("%(prop:HYPER_SIZE:-m1)s"), masterFQDN="nine.buildbot.net", **kwargs)


_PG_TEST_DB_URL = 'postgresql+pg8000://metabuildslave@localhost/ninebuildslave'
_MYSQL_TEST_DB_URL = 'mysql+mysqldb://metabuildslave@localhost/ninebuildslave'

workers = [
    # Local
    # Dustin Mitchell
    MyWorker(
        'knuth',
        max_builds=4,
        run_single=False,
        run_config=True,
        tw0810=True,
        py26=True,
        py27=True,
        nodejs=True),

    # Mozilla
    MyWorker(
        'buildbot-linux4',  # buildbot-linux4.community.scl3.mozilla.com
        max_builds=4,
        run_single=False,
        run_config=True,
        py26=True,
        py27=True,  # hand-compiled in /usr/local
        pyqt4=True,  # installed in system python
        databases={
            'postgres': dict(BUILDBOT_TEST_DB_URL=_PG_TEST_DB_URL),
            'mysql': dict(BUILDBOT_TEST_DB_URL=_MYSQL_TEST_DB_URL)
        }),
    # Bill Deegan
    MyWorker(
        'bdbaddog-nine',
        max_builds=4,
        run_single=False,
        run_config=True,
        py27=True,
        pyqt4=False,
        databases={
            'postgres': dict(BUILDBOT_TEST_DB_URL='postgresql+pg8000://${POSTGRESQL_ENV_POSTGRES_USER}:'
                             '${POSTGRESQL_ENV_POSTGRES_PASSWORD}@${POSTGRESQL_PORT_5432_TCP_ADDR}:'
                             '${POSTGRESQL_PORT_5432_TCP_PORT}/${POSTGRESQL_ENV_POSTGRES_USER}'),
            'mysql': dict(BUILDBOT_TEST_DB_URL='mysql+mysqldb://${MYSQL_ENV_MYSQL_USER}:'
                          '${MYSQL_ENV_MYSQL_PASSWORD}@${MYSQL_PORT_3306_TCP_ADDR}:'
                          '${MYSQL_PORT_3306_TCP_PORT}/${MYSQL_ENV_MYSQL_DATABASE}'),
        }
    ),

    # First worker on Buildbot infrastructure
    MyWorker(
        'bslave1',
        max_builds=4,
        run_single=False,
        run_config=True,
        py27=True)
] + [
    # add 40 hyper workers
    MyHyperWorker(
        'hyper' + str(i),
        max_builds=1,
        build_wait_timeout=1,
        run_single=False,
        run_config=True,
        py26=True,
        py27=True)
    for i in xrange(40)
] + [
    # add 4 local workers
    MyLocalWorker(
        'local' + str(i),
        max_builds=1,
        run_single=False,
        run_config=True,
        py26=True,
        py27=True)
    for i in xrange(4)
]
