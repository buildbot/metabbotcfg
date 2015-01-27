import sys
import os

from buildbot.plugins import buildslave

class MySlaveBase(object):
    # true if this box is buildbot.net, and can build docs, etc.
    buildbot_net = False

    # true if this box should use a 'simple' factory, meaning no virtualenv
    # (basically good for windows)
    use_simple = False

    # true if this box can test the buildmaster and buildslave, respectively
    test_master = True
    test_slave = True

    # true if this slave should have a single-slave builder of its own
    run_single = True

    # true if this host has PyQt4 installed in its default python
    pyqt4 = False

    # true if this slave can contribute to the virtualenv-managed pool of
    # specific-configuration builders.  Specific supported python versions
    # are given, too
    run_config = False
    py24 = False
    py25 = False
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
        self.slavename = name
        remaining = {}
        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])
            else:
                remaining[k] = kwargs[k]
        return remaining

    def get_pass(self, name):
        # get the password based on the name
        path = os.path.join(os.path.dirname(__file__), "%s.pass" % name)
        pw = open(path).read().strip()
        return pw

    def get_ec2_creds(self, name):
        path = os.path.join(os.path.dirname(__file__), "%s.ec2" % name)
        return open(path).read().strip().split(" ")

class MySlave(MySlaveBase, buildslave.BuildSlave):
    def __init__(self, name, **kwargs):
        password = self.get_pass(name)
        kwargs = self.extract_attrs(name, **kwargs)
        buildslave.BuildSlave.__init__(self, name, password, **kwargs)

#class MyEC2LatentBuildSlave(MySlaveBase, EC2LatentBuildSlave):
#    def __init__(self, name, ec2type, **kwargs):
#        password = self.get_pass(name)
#        identifier, secret_identifier = self.get_ec2_creds(name)
#        kwargs = self.extract_attrs(name, **kwargs)
#        EC2LatentBuildSlave.__init__(self, name, password, ec2type,
#            identifier=identifier, secret_identifier=secret_identifier,
#            **kwargs)

_PG_TEST_DB_URL = 'postgresql+pg8000://metabuildslave@localhost/ninebuildslave'
_MYSQL_TEST_DB_URL = 'mysql+mysqldb://metabuildslave@localhost/ninebuildslave'

slaves = [
    # Local
    # Dustin Mitchell
    MySlave('knuth',
            max_builds=4,
            run_single=False,
            run_config=True,
            tw0810=True,
            py24=True,
            py25=True,
            py26=True,
            py27=True,
            nodejs=True),

    # Mozilla
    MySlave('buildbot-linux4', # buildbot-linux4.community.scl3.mozilla.com
            max_builds=4,
            run_single=False,
            run_config=True,
            py24=False,
            py25=True, # hand-compiled in /usr/local
            py26=True,
            py27=True, # hand-compiled in /usr/local
            pyqt4=True, # installed in system python
            databases={
                'postgres' : dict(BUILDBOT_TEST_DB_URL=_PG_TEST_DB_URL),
                'mysql' : dict(BUILDBOT_TEST_DB_URL=_MYSQL_TEST_DB_URL)
            }),

    # First build slave on Buildbot infrastructure
    MySlave('bslave1',
            max_builds=4,
            run_single=False,
            run_config=True,
            py27=True)
]

def get_slaves(db=None, *args, **kwargs):
    rv = {}
    for arg in args:
        rv.update(arg)
    for sl in slaves:
        if db and db not in sl.databases:
            continue
        for k in kwargs:
            if getattr(sl, k) != kwargs[k]:
                break
        else:
            rv[sl.slavename] = sl
    return rv

def names(slavedict):
    return slavedict.keys()
