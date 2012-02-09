import textwrap
import itertools

from buildbot.process import factory
from buildbot.steps.source import Git
from buildbot.steps.shell import Compile, Test, ShellCommand
from buildbot.steps.transfer import FileDownload
from buildbot.steps.python_twisted import Trial
from buildbot.steps.python import PyFlakes

from metabbotcfg.slaves import slaves, get_slaves, names

builders = []

# slaves seem to have a hard time fetching from github, so retry every 5
# seconds, 5 times
GIT_RETRY = (5,5)

####### Custom Steps

class VirtualenvSetup(ShellCommand):
    def __init__(self, virtualenv_dir='sandbox', virtualenv_python='python',
                 virtualenv_packages=[], no_site_packages=False, **kwargs):
        ShellCommand.__init__(self, **kwargs)

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
        # this corresponds to ~/www/buildbot.net/pkgs on the metabuildbot server
        command.append("PKG_URL='%s'" % 'http://buildbot.net/pkgs')
        command.append("PYGET='import urllib, sys; urllib.urlretrieve("
                       "sys.argv[1], filename=sys.argv[2])'")
        command.append("NSP_ARG='%s'" %
                ('--no-site-packages' if self.no_site_packages else ''))

        # set up the virtualenv if it does not already exist
        command.append(textwrap.dedent("""\
        # first, set up the virtualenv if it hasn't already been done
        if ! test -f "$VE/bin/pip"; then
            echo "Setting up virtualenv $VE"
            mkdir -p "$VE" || exit 1;
            # get the prerequisites for building a virtualenv with no pypi access 
            for prereq in virtualenv.py pip-0.8.2.tar.gz; do
                [ -f "$VE/$prereq" ] && continue
                echo "Fetching $PKG_URL/$prereq"
                python -c "$PYGET" "$PKG_URL/$prereq" "$VE/$prereq" || exit 1;
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
            "$VE/bin/pip" install --no-index --download-cache="$PWD/.." --find-links="$PKG_URL" %(pkg)s || exit 1 
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
        return ShellCommand.start(self)

class DatabaseTrial(Trial):
    def __init__(self, db, **kwargs):
        Trial.__init__(self, **kwargs)
        self.db = db
        self.addFactoryArguments(db=db)

    def setupEnvironment(self, cmd):
        Trial.setupEnvironment(self, cmd)
        # get the appropriate database configuration from the slave
        extra_env = self.buildslave.databases[self.db]
        cmd.args['env'].update(extra_env)

######## BuildFactory Factories

# some slaves just do "simple" builds: get the source, run the tests.  These are mostly
# windows machines where we don't have a lot of flexibility to mess around with virtualenv
def mksimplefactory(test_master=True):
    f = factory.BuildFactory()
    f.addSteps([
    Git(repourl='git://github.com/buildbot/buildbot.git', mode="copy", retry=GIT_RETRY),
    # use workdir instead of testpath because setuptools sticks its own eggs (including
    # the running version of buildbot) into sys.path *before* PYTHONPATH, but includes
    # "." in sys.path even before the eggs
    Trial(workdir="build/slave", testpath=".",
        tests='buildslave.test',
        usePTY=False,
        name='test slave'),
    ])
    if test_master:
        f.addStep(
        Trial(workdir="build/master", testpath=".",
            tests='buildbot.test',
            usePTY=False,
            name='test master'),
        )
    return f

# much like simple buidlers, but it uses virtualenv
def mktestfactory(twisted_version='twisted', python_version='python',
                sqlalchemy_version='sqlalchemy',
                sqlalchemy_migrate_version='sqlalchemy-migrate==0.7.1',
                extra_packages=[], db=None):
    subs = dict(twisted_version=twisted_version, python_version=python_version)
    ve = "../sandbox-%(python_version)s-%(twisted_version)s" % subs
    if sqlalchemy_version != 'sqlalchemy':
        ve += '-' + sqlalchemy_version
    ve += sqlalchemy_migrate_version.replace('sqlalchemy-migrate==', 'samigr-')
    subs['ve'] = ve

    f = factory.BuildFactory()
    f.addSteps([
    Git(repourl='git://github.com/buildbot/buildbot.git', mode="copy", retry=GIT_RETRY),
    VirtualenvSetup(name='virtualenv setup',
        no_site_packages=True,
        virtualenv_python=python_version,
        virtualenv_packages=[twisted_version, sqlalchemy_version,
            sqlalchemy_migrate_version, 'mock', '--editable=master', '--editable=slave']
            + extra_packages,
        virtualenv_dir=ve,
        haltOnFailure=True),
    ShellCommand(usePTY=False, command=textwrap.dedent("""
        SANDBOX="%(ve)s";
        PYTHON="$PWD/$SANDBOX/bin/python";
        PIP="$PWD/$SANDBOX/bin/pip";
        $PYTHON -c 'import sys; print "Python:", sys.version; import twisted; print "Twisted:", twisted.version' || exit 1;
        $PIP freeze
        """ % subs),
        description="versions",
        descriptionDone="versions",
        name="versions"),
    ])
    # see note above about workdir vs. testpath
    if not db:
        f.addSteps([
    Trial(workdir="build/slave", testpath='.',
        tests='buildslave.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test slave'),
    Trial(workdir="build/master", testpath='.',
        tests='buildbot.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test master'),
    ])
    else:
        f.addSteps([
    DatabaseTrial(workdir="build/master", testpath='.',
        db=db,
        tests='buildbot.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test master'),
    ])
    return f

def mkcoveragefactory():
    f = factory.BuildFactory()
    f.addSteps([
    Git(repourl='git://github.com/buildbot/buildbot.git', mode="update", retry=GIT_RETRY),
    ShellCommand(command=r"find . -name '*.pyc' -exec rm \{} \;"),
    VirtualenvSetup(name='virtualenv setup',
        no_site_packages=True,
        virtualenv_packages=['coverage', 'mock', '--editable=master', '--editable=slave'],
        virtualenv_dir='sandbox',
        haltOnFailure=True),
    ShellCommand(usePTY=False, command=textwrap.dedent("""
        PYTHON=sandbox/bin/python;
        sandbox/bin/coverage run --rcfile=common/coveragerc \
            sandbox/bin/trial buildbot.test buildslave.test \
            || exit 1;
        sandbox/bin/coverage html -i --rcfile=.coveragerc \
            -d /home/buildbot/www/buildbot.net/buildbot/coverage \
            || exit 1;
        chmod -R a+rx /home/buildbot/www/buildbot.net/buildbot/coverage || exit 1
    """),
        description='coverage',
        descriptionDone='coverage',
        name='coverage report'),
    ])
    return f

def mkdocsfactory():
    f = factory.BuildFactory()
    f.addSteps([
        Git(repourl='git://github.com/buildbot/buildbot.git', mode="update", retry=GIT_RETRY),
        FileDownload(mastersrc="virtualenv.py", slavedest="virtualenv.py", flunkOnFailure=True),

    # run docs tools in their own virtualenv, otherwise we end up documenting
    # the version of Buildbot running the metabuildbot!
    VirtualenvSetup(name='virtualenv setup',
        no_site_packages=True,
        virtualenv_packages=['sphinx', 'epydoc', '--editable=master', '--editable=slave'],
        virtualenv_dir='sandbox',
        haltOnFailure=True),

    # apidocs
    ShellCommand(command="source sandbox/bin/activate && make VERSION=latest apidocs", name="create apidocs",
               flunkOnFailure=True, haltOnFailure=True),
    ShellCommand(command=textwrap.dedent("""\
        tar -C /home/buildbot/www/buildbot.net/buildbot/docs/latest -zxf apidocs/reference.tgz &&
        chmod -R a+rx /home/buildbot/www/buildbot.net/buildbot/docs/latest/reference
        """), name="api docs to web", flunkOnFailure=True, haltOnFailure=True),

    # manual
    ShellCommand(command="source sandbox/bin/activate && make VERSION=latest docs", name="create docs"),
    ShellCommand(command=textwrap.dedent("""\
        tar -C /home/buildbot/www/buildbot.net/buildbot/docs -zvxf master/docs/docs.tgz latest/ &&
        chmod -R a+rx /home/buildbot/www/buildbot.net/buildbot/docs/latest &&
        find /home/buildbot/www/buildbot.net/buildbot/docs/latest -name '*.html' | xargs python /home/buildbot/www/buildbot.net/buildbot/add-tracking.py
        """), name="docs to web", flunkOnFailure=True, haltOnFailure=True),

    # notify trac of the new commit
    ShellCommand(command=textwrap.dedent("""\
        cd ~/trac/repos/buildbot.git &&
        git fetch &&
        ~/sandbox/bin/trac-admin ~/trac repository sync Buildbot
        """), name="update trac", flunkOnFailure=True, haltOnFailure=True),
    ])
    return f

def mklintyfactory():
    f = factory.BuildFactory()
    f.addSteps([
        Git(repourl='git://github.com/buildbot/buildbot.git', mode="update", retry=GIT_RETRY),
        PyFlakes(command="/home/buildbot/sandbox/bin/pyflakes master/buildbot", name="pyflakes - master", flunkOnFailure=True),
        PyFlakes(command="/home/buildbot/sandbox/bin/pyflakes slave/buildslave", name="pyflakes - slave", flunkOnFailure=True),
    ])
    return f

#### docs, coverage, etc.

builders.append({
    'name' : 'docs',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'workdir' : 'docs',
    'factory' : mkdocsfactory(),
    'category' : 'docs' })

builders.append({
    'name' : 'coverage',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'workdir' : 'coverage',
    'factory' : mkcoveragefactory(),
    'category' : 'docs' })

builders.append({
    'name' : 'linty',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'workdir' : 'linty',
    'factory' : mklintyfactory(),
    'category' : 'docs' })

#### single-slave builders

for sl in get_slaves(run_single=True).values():
    if sl.use_simple:
        f = mksimplefactory(test_master=sl.test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name' : 'slave-%s' % sl.slavename,
        'slavenames' : [ sl.slavename ],
        'workdir' : 'slave-%s' % sl.slavename,
        'factory' : f,
        'category' : 'slave' })

#### operating systems

for opsys in set(sl.os for sl in slaves if sl.os is not None):
    if 'win' in opsys:
        f = mksimplefactory(test_master=sl.test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name' : 'os-%s' % opsys,
        'slavenames' : names(get_slaves(os=opsys)),
        'workdir' : 'os-%s' % opsys,
        'factory' : f,
        'category' : 'os' })
        
#### databases

database_packages = {
    'postgres' : [ 'pg8000' ],
    'mysql' : [ 'mysql-python' ],
}

for db in set(itertools.chain.from_iterable(sl.databases.keys() for sl in slaves)):
    f = mktestfactory(extra_packages=database_packages[db], db=db)
    builders.append({
        'name' : 'db-%s' % db,
        'slavenames' : names(get_slaves(db=db)),
        'workdir' : 'db-%s' % db,
        'factory' : f,
        'category' : 'db' })
        

#### config builders

twisted_versions = dict(
    tw0810='Twisted==8.1.0',
    tw0820='Twisted==8.2.0',
    tw0900='Twisted==9.0.0',
    tw1020='Twisted==10.2.0',
    tw1100='Twisted==11.0.0',
)

python_versions = dict(
    py24='python2.4',
    py25='python2.5',
    py26='python2.6',
    py27='python2.7',
    pypy17='pypy1.7',
    pypy18='pypy1.8',
)

for py, python_version in python_versions.items():
    config_slaves = names(get_slaves(run_config=True, **{py:True}))
    if not config_slaves:
        continue

    for tw, twisted_version in twisted_versions.items():
        f = mktestfactory(twisted_version=twisted_version, python_version=python_version)
        name = "%s-%s" % (py, tw)
        builders.append({
            'name' : name,
            'slavenames' : config_slaves,
            'factory' : f,
            'category' : 'config' })

sqlalchemy_versions = dict(
    sa060='sqlalchemy==0.6.0',
    sa068='sqlalchemy==0.6.8',
    sa070='sqlalchemy==0.7.0',
    sa074='sqlalchemy==0.7.4',
)

for sa, sqlalchemy_version in sqlalchemy_versions.items():
    f = mktestfactory(sqlalchemy_version=sqlalchemy_version, python_version='python2.7')
    name = "py27-%s" % (sa,)
    builders.append({
        'name' : name,
        'slavenames' : config_slaves,
        'factory' : f,
        'category' : 'config' })

sqlalchemy_migrate_versions = dict(
    sam061='sqlalchemy-migrate==0.6.1',
    #sam070='sqlalchemy-migrate==0.7.0', -- not on pypi..
    sam071='sqlalchemy-migrate==0.7.1',
)

for sa, sqlalchemy_migrate_version in sqlalchemy_migrate_versions.items():
    f = mktestfactory(sqlalchemy_migrate_version=sqlalchemy_migrate_version,
                      python_version='python2.7')
    name = "py27-%s" % (sa,)
    builders.append({
        'name' : name,
        'slavenames' : config_slaves,
        'factory' : f,
        'category' : 'config' })
