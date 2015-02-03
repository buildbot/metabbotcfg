import textwrap
import itertools

from buildbot.plugins import steps
from buildbot.plugins import util

from metabbotcfg.common import GIT_URL
from metabbotcfg.slaves import slaves, get_slaves, names

builders = []

# slaves seem to have a hard time fetching from github, so retry
gitStep = steps.Git(repourl=GIT_URL, mode='full', method='fresh',
                    retryFetch=True)

####### Custom Steps

# only allow one VirtualenvSetup to run on a slave at a time.  This prevents
# collisions in the shared package cache.
veLock = util.SlaveLock('veLock')

class VirtualenvSetup(steps.ShellCommand):
    def __init__(self, virtualenv_dir='sandbox', virtualenv_python='python',
                 virtualenv_packages=[], no_site_packages=False, **kwargs):
        kwargs['locks'] = kwargs.get('locks', []) + [veLock.access('exclusive')]
        steps.ShellCommand.__init__(self, **kwargs)

        self.virtualenv_dir = virtualenv_dir
        self.virtualenv_python = virtualenv_python
        self.virtualenv_packages = virtualenv_packages
        self.no_site_packages = no_site_packages

        self.addFactoryArguments(
                virtualenv_dir=virtualenv_dir,
                virtualenv_python=virtualenv_python,
                virtualenv_packages=virtualenv_packages,
                no_site_packages=no_site_packages)

    def start(self):
        # set up self.command as a very long sh -c invocation
        command = []
        command.append("PYTHON='%s'" % self.virtualenv_python)
        command.append("VE='%s'" % self.virtualenv_dir)
        command.append("VEPYTHON='%s/bin/python'" % self.virtualenv_dir)
        # this corresponds to ~/www/buildbot.buildbot.net/static/pkgs on the metabuildbot server
        command.append("PKG_URL='%s'" % 'http://buildbot.buildbot.net/static/pkgs')
        command.append("PYGET='import urllib, sys; urllib.urlretrieve("
                       "sys.argv[1], filename=sys.argv[2])'")
        command.append("NSP_ARG='%s'" %
                ('--no-site-packages' if self.no_site_packages else ''))

        command.append(textwrap.dedent("""\
        # first, set up the virtualenv if it hasn't already been done
        if ! test -f "$VE/bin/pip"; then
            echo "Setting up virtualenv $VE"
            mkdir -p "$VE" || exit 1;
            # get the prerequisites for building a virtualenv with no pypi access
            for prereq in virtualenv.py pip-1.5.6-py2.py3-none-any.whl setuptools-7.0-py2.py3-none-any.whl; do
                [ -f "$VE/$prereq" ] && continue
                echo "Fetching $PKG_URL/$prereq"
                $PYTHON -c "$PYGET" "$PKG_URL/$prereq" "$VE/$prereq" || exit 1;
            done;
            echo "Invoking virtualenv.py (this accesses pypi)"
            "$PYTHON" "$VE/virtualenv.py" --distribute --python="$PYTHON" $NSP_ARG "$VE" || exit 1
        else
            echo "Virtualenv already exists"
        fi
        """).strip())

        # now install each requested package
        for pkg in self.virtualenv_packages:
            command.append(textwrap.dedent("""\
            echo "Installing %(pkg)s";
            "$VE/bin/pip" install --no-index --download-cache="$PWD/../.." --find-links="$PKG_URL" %(pkg)s || exit 1
            """).strip() % dict(pkg=pkg))

        # make $VE/bin/trial work, even if we inherited trial from site-packages
        command.append(textwrap.dedent("""\
        if ! test -x "$VE/bin/trial"; then
            echo "adding $VE/bin/trial";
            ln -s `which trial` "$VE/bin/trial";
        fi
        """).strip())
        # and finally, straighten out some preferred versions
        command.append(textwrap.dedent("""\
        echo "Checking for simplejson or json";
        "$VEPYTHON" -c 'import json' 2>/dev/null || "$VEPYTHON" -c 'import simplejson' ||
                    "$VE/bin/pip" install --no-index --download-cache="$PWD/.." --find-links="$PKG_URL" simplejson || exit 1;
        echo "Checking for sqlite3, including pysqlite3 on Python 2.5";
        "$VEPYTHON" -c 'import sqlite3, sys; assert sys.version_info >= (2,6)' 2>/dev/null ||
                    "$VEPYTHON" -c 'import pysqlite2.dbapi2' ||
                    "$VE/bin/pip" install --no-index --download-cache="$PWD/.." --find-links="$PKG_URL" pysqlite || exit 1
        """).strip())

        self.command = ';\n'.join(command)
        return steps.ShellCommand.start(self)

class DatabaseTrial(steps.Trial):
    def __init__(self, db, **kwargs):
        steps.Trial.__init__(self, **kwargs)
        self.db = db
        self.addFactoryArguments(db=db)

    def setupEnvironment(self, cmd):
        steps.Trial.setupEnvironment(self, cmd)
        # get the appropriate database configuration from the slave
        extra_env = self.buildslave.databases[self.db]
        cmd.args['env'].update(extra_env)

######## BuildFactory Factories

# some slaves just do "simple" builds: get the source, run the tests.  These are mostly
# windows machines where we don't have a lot of flexibility to mess around with virtualenv
def mksimplefactory(test_master=True):
    f = util.BuildFactory()
    f.addSteps([
        gitStep,
        # use workdir instead of testpath because setuptools sticks its own eggs (including
        # the running version of buildbot) into sys.path *before* PYTHONPATH, but includes
        # "." in sys.path even before the eggs
        steps.Trial(workdir="build/slave", testpath=".",
                    tests='buildslave.test',
                    usePTY=False, name='test slave')
    ])
    if test_master:
        f.addStep(steps.Trial(workdir="build/master", testpath=".",
                              tests='buildbot.test', usePTY=False,
                              name='test master'))
    return f

# much like simple buidlers, but it uses virtualenv
def mktestfactory(twisted_version='twisted', python_version='python',
                  sqlalchemy_version='sqlalchemy',
                  sqlalchemy_migrate_version='sqlalchemy-migrate==0.7.1',
                  extra_packages=None, db=None,
                  www=False, slave_only=False):
    if not extra_packages:
        extra_packages = []
    subs = dict(twisted_version=twisted_version, python_version=python_version)
    ve = "../sandbox-%(python_version)s-%(twisted_version)s" % subs
    if sqlalchemy_version != 'sqlalchemy':
        ve += '-' + sqlalchemy_version
    ve += sqlalchemy_migrate_version.replace('sqlalchemy-migrate==', 'samigr-')
    subs['ve'] = ve

    if www:
        extra_packages.append('--editable=www')

    virtualenv_packages = [
        'zope.interface==3.6.1', twisted_version, sqlalchemy_version,
        sqlalchemy_migrate_version, 'multiprocessing==2.6.2.1', 'mock==0.8.0',
        '--editable=slave'
    ] + extra_packages
    if python_version > 'python2.5':
        # because some of the dependencies don't work on 2.5
        virtualenv_packages.extend(['moto==0.3.1', 'boto==2.29.1'])
    if python_version in ('python2.4', 'python2.5'):
        # and, because the latest versions of these don't work on <2.5, and the version of
        # pip that works on 2.5 doesn't understand that '==' means 'I want this version'
        virtualenv_packages.insert(0, 'http://buildbot.buildbot.net/static/pkgs/zope.interface-3.6.1.tar.gz')
        virtualenv_packages.insert(0, 'http://buildbot.buildbot.net/static/pkgs/setuptools-1.4.2.tar.gz')
    else:
        virtualenv_packages.insert(0, 'http://buildbot.buildbot.net/static/pkgs/zope.interface-4.1.1.tar.gz')
    if sqlalchemy_migrate_version:
        virtualenv_packages.append(sqlalchemy_migrate_version)
    if not slave_only:
        virtualenv_packages.append('--editable=master')
    f = util.BuildFactory()
    f.addSteps([
        gitStep,
        VirtualenvSetup(name='virtualenv setup',
                        no_site_packages=True,
                        virtualenv_python=python_version,
                        virtualenv_packages=virtualenv_packages,
                        virtualenv_dir=ve,
                        haltOnFailure=True),
        steps.ShellCommand(command=textwrap.dedent("""
            SANDBOX="%(ve)s";
            PYTHON="$PWD/$SANDBOX/bin/python";
            PIP="$PWD/$SANDBOX/bin/pip";
            $PYTHON -c 'import sys; print "Python:", sys.version; import twisted; print "Twisted:", twisted.version' || exit 1;
            $PIP freeze
            """ % subs),
            usePTY=False,
            description="versions",
            descriptionDone="versions",
            name="versions")
    ])
    # see note above about workdir vs. testpath
    if db:
        # for DB, just test the master (the slave doesn't use the db)
        f.addSteps([
            DatabaseTrial(workdir="build/master", testpath='.',
                          db=db,
                          tests='buildbot.test',
                          trial="../%(ve)s/bin/trial" % subs,
                          usePTY=False,
                          name='test master')
        ])
    elif www:
        # for www, run 'grunt ci'; this needs the virtualenv path in PATH
        f.addSteps([
            steps.ShellCommand(workdir="build/www",
                               command=['./node_modules/.bin/grunt', 'ci'],
                               usePTY=False,
                               name='grunt ci',
                               env={'PATH':'../%(ve)s/bin/:${PATH}' % subs})
        ])
    else:
        f.addSteps([
            steps.Trial(workdir="build/slave", testpath='.',
                        tests='buildslave.test',
                        trial="../%(ve)s/bin/trial" % subs,
                        usePTY=False,
                        name='test slave'),
        ])

    if not slave_only and not db:
        f.addSteps([
            steps.Trial(workdir="build/master", testpath='.',
                        tests='buildbot.test',
                        trial="../%(ve)s/bin/trial" % subs,
                        usePTY=False,
                        name='test master'),
        ])

    return f

def mkcoveragefactory():
    f = util.BuildFactory()
    f.addSteps([
        gitStep,
        VirtualenvSetup(name='virtualenv setup',
                        no_site_packages=True,
                        virtualenv_packages=['coverage', 'mock',
                                             '--editable=master',
                                             '--editable=slave'],
                        virtualenv_dir='sandbox',
                        haltOnFailure=True),
        steps.ShellCommand(command=textwrap.dedent("""
            PYTHON=sandbox/bin/python;
            sandbox/bin/coverage run --rcfile=common/coveragerc \
                sandbox/bin/trial buildbot.test buildslave.test \
                || exit 1;
            sandbox/bin/coverage html -i --rcfile=.coveragerc \
                -d /home/buildbot/www/buildbot.buildbot.net/static/coverage \
                || exit 1;
            chmod -R a+rx /home/buildbot/www/buildbot.buildbot.net/static/coverage || exit 1
        """),
            usePTY=False,
            description='coverage',
            descriptionDone='coverage',
            name='coverage report')
    ])
    return f

def mkdocsfactory():
    f = util.BuildFactory()
    f.addSteps([
        gitStep,
        steps.FileDownload(mastersrc="virtualenv.py",
                           slavedest="virtualenv.py",
                           flunkOnFailure=True),
        # run docs tools in their own virtualenv, otherwise we end up
        # documenting the version of Buildbot running the metabuildbot!
        VirtualenvSetup(name='virtualenv setup',
                        no_site_packages=True,
                        virtualenv_packages=['sphinx==1.2.2',
                                             '--editable=master',
                                             '--editable=slave'],
                        virtualenv_dir='sandbox', haltOnFailure=True),
        # manual
        steps.ShellCommand(command=util.Interpolate(textwrap.dedent("""\
            source sandbox/bin/activate &&
            make docs
            """)), name="create docs"),
        steps.ShellCommand(command=textwrap.dedent("""\
            export VERSION=latest &&
            tar -C /home/buildbot/www/buildbot.net/buildbot/docs -zvxf master/docs/docs.tgz &&
            chmod -R a+rx /home/buildbot/www/buildbot.net/buildbot/docs/latest &&
            find /home/buildbot/www/buildbot.net/buildbot/docs/latest -name '*.html' | xargs python /home/buildbot/www/buildbot.net/buildbot/add-tracking.py
            """), name="docs to web", flunkOnFailure=True, haltOnFailure=True)
    ])
    return f

def mklintyfactory():
    f = util.BuildFactory()
    f.addSteps([
        gitStep,
        # run linty tools in their own virtualenv, so we can control the version
        # the version of Buildbot running the metabuildbot!
        VirtualenvSetup(name='virtualenv setup',
                        no_site_packages=True,
                        virtualenv_packages=['pyflakes', 'pylint==1.1.0',
                                             'pep8==1.4.6',
                                             '--editable=master',
                                             '--editable=slave'],
                        virtualenv_dir='sandbox',
                        haltOnFailure=True),
        steps.PyFlakes(command="sandbox/bin/pyflakes master/buildbot",
                       name="pyflakes - master", flunkOnFailure=True),
        steps.PyFlakes(command="sandbox/bin/pyflakes slave/buildslave",
                       name="pyflakes - slave", flunkOnFailure=True),
        steps.ShellCommand(command="sandbox/bin/pylint --rcfile common/pylintrc buildbot",
                           name="pylint - master", flunkOnFailure=True),
        steps.ShellCommand(command="sandbox/bin/pylint --rcfile common/pylintrc buildslave",
                           name="pylint - slave", flunkOnFailure=True),
        steps.ShellCommand(command="sandbox/bin/pep8 --config common/pep8rc master/buildbot",
                           name="pep8 - master", flunkOnFailure=True),
        steps.ShellCommand(command="sandbox/bin/pep8 --config common/pep8rc slave/buildslave",
                           name="pep8 - slave", flunkOnFailure=True),
    ])
    return f

#### single-slave builders

for sl in get_slaves(run_single=True).values():
    if sl.use_simple:
        f = mksimplefactory(test_master=sl.test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name': 'slave-%s' % sl.slavename,
        'slavenames': [sl.slavename],
        'factory': f,
        'tags': ['slave']
    })

#### operating systems

for opsys in set(sl.os for sl in slaves if sl.os is not None):
    if 'win' in opsys:
        test_master = 'cygwin' in opsys
        f = mksimplefactory(test_master=test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name': 'os-%s' % opsys,
        'slavenames': names(get_slaves(os=opsys)),
        'factory': f,
        'tags': ['os']
    })

#### databases

database_packages = {
    'postgres': ['pg8000'],
    'mysql': ['mysql-python'],
}

for db in set(itertools.chain.from_iterable(sl.databases.keys() for sl in slaves)):
    f = mktestfactory(extra_packages=database_packages[db], db=db)
    builders.append({
        'name': 'db-%s' % db,
        'slavenames': names(get_slaves(db=db)),
        'factory': f,
        'tags': ['db']
    })

#### www

f = mktestfactory(www=True)
builders.append({
    'name': 'www',
    'slavenames': names(get_slaves(nodejs=True)),
    'factory': f,
    'tags': ['www']
})

#### config builders

twisted_versions = dict(tw0900='Twisted==9.0.0',
                        tw1020='Twisted==10.2.0',
                        tw1110='Twisted==11.1.0',
                        tw1220='Twisted==12.2.0',
                        tw1320='Twisted==13.2.0',
                        tw1400='Twisted==14.0.0')

python_versions = dict(py25='python2.5',
                       py26='python2.6',
                       py27='python2.7')

# versions of twisted and python only supported by slave
slave_only_twisted = ['tw0900', 'tw1020']
slave_only_python = ['py25']

# incompatible versions of twisted and python
incompat_tw_py = [
    ('tw0900', 'py27'),
    ('tw1220', 'py25'),
    ('tw1320', 'py25'),
    ('tw1400', 'py25')
]

for py, python_version in python_versions.items():
    for tw, twisted_version in twisted_versions.items():
        config_slaves = names(get_slaves(run_config=True, **{py:True, tw:True}))
        if not config_slaves:
            continue

        if (tw, py) in incompat_tw_py:
            continue

        slave_only = tw in slave_only_twisted or py in slave_only_python
        f = mktestfactory(twisted_version=twisted_version, python_version=python_version,
                slave_only=slave_only)
        name = "%s-%s" % (py, tw)
        builders.append({
            'name': name,
            'slavenames': config_slaves,
            'factory': f,
            'tags': ['config']
        })

# py24 + tw0810 for slave only
config_slaves = names(get_slaves(run_config=True, py24=True, tw0810=True))
f = mktestfactory(twisted_version='Twisted==8.1.0', python_version='python2.4',
                  sqlalchemy_version='sqlalchemy==0.6.0', slave_only=True)
name = 'py24-tw0810-slave'
builders.append({
    'name': name,
    'slavenames': config_slaves,
    'factory': f,
    'tags': ['config']
})

pypy_versions = dict(pypy17='pypy1.7',
                     pypy18='pypy1.8')

twisted_pypy_versions = dict(tw1110='Twisted==11.1.0',
                             tw1200='Twisted==12.0.0')

for py, python_version in pypy_versions.items():
    config_slaves = names(get_slaves(run_config=True, **{py:True}))
    if not config_slaves:
        continue

    for tw, twisted_version in twisted_pypy_versions.items():
        f = mktestfactory(twisted_version=twisted_version,
                          python_version=python_version)
        name = "%s-%s" % (py, tw)
        builders.append({
            'name': name,
            'slavenames': config_slaves,
            'factory': f,
            'tags': ['config']
        })

config_slaves = names(get_slaves(run_config=True, py27=True))

sqlalchemy_versions = dict(
    sa060='sqlalchemy==0.6.0',
    sa068='sqlalchemy==0.6.8',
    sa070='sqlalchemy==0.7.0',
    sa074='sqlalchemy==0.7.4',
    sa078='sqlalchemy==0.7.8',
    sa0710='sqlalchemy==0.7.10',
    sa086='sqlalchemy==0.8.6',
    sa094='sqlalchemy==0.9.4',
)

sqlalchemy_migrate_versions = dict(
    #sam061='sqlalchemy-migrate==0.6.1', -- not supported
    #sam070='sqlalchemy-migrate==0.7.0', -- not on pypi..
    sam071='sqlalchemy-migrate==0.7.1',
    sam072='sqlalchemy-migrate==0.7.2',
    sam09='sqlalchemy-migrate==0.9',
)
# these versions are not compatible with sa>=0.8
sam_require_old_sa = set(['sam071', 'sam072'])

for sa, sqlalchemy_version in sqlalchemy_versions.items():
    f = mktestfactory(sqlalchemy_version=sqlalchemy_version,
                      sqlalchemy_migrate_version=sqlalchemy_migrate_versions['sam09'],
                      python_version='python2.7')
    name = "py27-%s" % (sa,)
    builders.append({
        'name': name,
        'slavenames': config_slaves,
        'factory': f,
        'tags': ['config']
    })

for sam, sqlalchemy_migrate_version in sqlalchemy_migrate_versions.items():
    sqlalchemy_version = sqlalchemy_versions['sa094']
    if sam in sam_require_old_sa:
        sqlalchemy_version = sqlalchemy_versions['sa0710']
    f = mktestfactory(sqlalchemy_version=sqlalchemy_version,
                      sqlalchemy_migrate_version=sqlalchemy_migrate_version,
                      python_version='python2.7')
    name = "py27-%s" % (sam,)
    builders.append({
        'name': name,
        'slavenames': config_slaves,
        'factory': f,
        'tags': ['config']
    })
