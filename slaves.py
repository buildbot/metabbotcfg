import os
from buildbot.buildslave import BuildSlave

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

class MySlave(MySlaveBase, BuildSlave):
    def __init__(self, name, **kwargs):
        password = self.get_pass(name)
        kwargs = self.extract_attrs(name, **kwargs)
        BuildSlave.__init__(self, name, password, **kwargs)

#class MyEC2LatentBuildSlave(MySlaveBase, EC2LatentBuildSlave):
#    def __init__(self, name, ec2type, **kwargs):
#        password = self.get_pass(name)
#        identifier, secret_identifier = self.get_ec2_creds(name)
#        kwargs = self.extract_attrs(name, **kwargs)
#        EC2LatentBuildSlave.__init__(self, name, password, ec2type,
#            identifier=identifier, secret_identifier=secret_identifier, **kwargs)

slaves = [
    # Local
    MySlave('buildbot.net',
        buildbot_net=True,
        run_config=False,
        run_single=False,
        max_builds=1,
        ),

     # Dustin Mitchell
    MySlave('knuth.r.igoro.us',
        max_builds=4,
        run_single=False,
        run_config=True,
        tw0810 = True,
        py26=True,
        py27=True,
        nodejs=True,
        databases={
            'postgres' : dict(BUILDBOT_TEST_DB_URL=
                'postgresql+pg8000://metabuildslave@localhost/metabuildslave'),
            'mysql' : dict(BUILDBOT_TEST_DB_URL=
                'mysql+mysqldb://metabuildslave@localhost/metabuildslave'),
        },
        ),

    # Mozilla
    MySlave('buildbot-linux4', # buildbot-linux4.community.scl3.mozilla.com
        max_builds=4,
        run_single=False,
        run_config=True,
        py26=True,
        py27=True, # hand-compiled in /usr/local
        pyqt4=True, # installed in system python
        databases={
            'postgres' : dict(BUILDBOT_TEST_DB_URL=
                'postgresql+pg8000://metabuildslave@localhost/metabuildslave'),
            'mysql' : dict(BUILDBOT_TEST_DB_URL=
                'mysql+mysqldb://metabuildslave@localhost/metabuildslave'),
        },
        ),

    # VM on Buildbot hardware
    MySlave('linux',
        max_builds=4,
        run_single=False,
        run_config=True,
        py27=True,
        pyqt4=False,
        databases={
            'postgres' : dict(BUILDBOT_TEST_DB_URL=
                'postgresql+pg8000://${POSTGRESQL_ENV_POSTGRES_USER}:${POSTGRESQL_ENV_POSTGRES_PASSWORD}@${POSTGRESQL_PORT_5432_TCP_ADDR}:${POSTGRESQL_PORT_5432_TCP_PORT}/${POSTGRESQL_ENV_POSTGRES_USER}'),
            'mysql' : dict(BUILDBOT_TEST_DB_URL=
                "mysql+mysqldb://${MYSQL_ENV_MYSQL_USER}:${MYSQL_ENV_MYSQL_PASSWORD}@${MYSQL_PORT_3306_TCP_ADDR}:${MYSQL_PORT_3306_TCP_PORT}/${MYSQL_ENV_MYSQL_DATABASE}"),
        }
    ),

    # koobs - Kubilay Kocak <koobs dot freebsd at gmail.com>
    MySlave('koobs-freebsd9',
        max_builds=4,
        run_single=False,
        run_config=True,
        py26=False,
        py27=True,
        ),

    MySlave('koobs-freebsd10',
        max_builds=4,
        run_single=False,
        run_config=True,
        py26=False,
        py27=True,
        ),

    # tomprince
    MySlave('tomprince-socrates-winxp-1',
        max_builds=1,
        run_single=False,
        os='winxp-msys',
        # note that use_simple is implicit
        ),

    # LSU
    MySlave('bghimi4-2',  # ssh -p 2525 djmitche@josh.cct.lsu.edu
        max_builds=2,
        run_single=False,
        run_config=True,
        py26=True,
        py27=True,
        # os x mountain lion doesn't support old twisteds, it seems
        tw0900=False,
        tw1020=False,
        os='osx-mtnlion',
        ),

    # Reto Sonderegger <reto.sonderegger@gmx.ch>
    MySlave('metrohm-win81',
        max_builds=1,
        run_single=False,
        os='win81',
        # note that use_simple is implicit
        ),

    # (EC2 - kept here as an indication of how to set it up)
#    MyEC2LatentBuildSlave('ec2slave', 'm1.small',
#        ami='ami-5a749c33',
#        keypair_name='buildbot-setup',
#        security_name='buildslaves',
#        ),
    MySlave("debian", run_single=False, run_config=False, max_builds=4)
]

# these are slaves that haven't been up and from whose owners I have not heard in a while
retired_slaves = [
    # Dustin Sallings
    MySlave('ubuntu810-64',
        max_builds=1),
    MySlave('minime',
        max_builds=1),
    MySlave('freebsd_7',
        max_builds=1),
    # (gets command timeouts while doing virtualenv install)
    MySlave('minimata',
        ),

    # maruel
    MySlave('xp-msysgit',
        max_builds=1,
        run_single=False,
        os='winxp-msys',
        # note that use_simple is implicit
        ),

    MySlave('win7-cygwin',
        max_builds=1,
        run_single=False,
        os='win7-cygwin',
        test_master=False, # master doesn't work on cygwin
        # note that use_simple is implicit
        ),


    # tomprince
    MySlave('tomprince-hermes-gentoo-1',
        max_builds=1,
        run_single=False,
        run_config=True,
        pypy17=True,
        pypy18=True,
        ),

    # Steve 'Ashcrow' Milner
    MySlave('centos_5_python2_4',
        ),

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
