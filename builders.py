import textwrap
import itertools

from buildbot import locks
from buildbot.process import factory
from buildbot.process.properties import Interpolate
from buildbot.steps.source.git import Git
from buildbot.steps.shell import Compile, Test, ShellCommand
from buildbot.steps.slave import RemoveDirectory, MakeDirectory
from buildbot.steps.transfer import FileDownload
from buildbot.steps.python_twisted import Trial
from buildbot.steps.python import PyFlakes

from metabbotcfg.common import GIT_URL
from metabbotcfg.slaves import slaves, get_slaves, names

_PACKAGE_STASH = 'http://ftp.buildbot.net/pub/metabuildbot/python-packages/'

builders = []

# slaves seem to have a hard time fetching from github, so retry
gitStep = Git(repourl=GIT_URL, mode='full', method='fresh', retryFetch=True)

####### Custom Steps

# only allow one VirtualenvSetup to run on a slave at a time.  This prevents
# collisions in the shared package cache.
veLock = locks.SlaveLock('veLock')

class VirtualenvSetup(ShellCommand):
    def __init__(self, virtualenv_dir='sandbox', virtualenv_python='python',
                 virtualenv_packages=[], no_site_packages=False, **kwargs):
        kwargs['locks'] = kwargs.get('locks', []) + [veLock.access('exclusive')]
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
        command.append("PKG_URL='%s'" % _PACKAGE_STASH)
        command.append("PYGET='import urllib, sys; urllib.urlretrieve("
                       "sys.argv[1], filename=sys.argv[2])'")
        command.append("NSP_ARG='%s'" %
                ('--no-site-packages' if self.no_site_packages else ''))

        command.append(textwrap.dedent("""\
        # first, set up the virtualenv if it hasn't already been done, or if it's
        # broken (as sometimes happens when a slave's Python is updated)
        if ! test -f "$VE/bin/pip" || ! "$VE/bin/python" -c 'import math'; then
            echo "Setting up virtualenv $VE";
            rm -rf "$VE";
            test -d "$VE" && { echo "$VE couldn't be removed"; exit 1; };
            mkdir -p "$VE" || exit 1;
            # get the prerequisites for building a virtualenv with no pypi access (including both tarballs and wheels)
            for prereq in virtualenv.py pip-1.5.6.tar.gz setuptools-5.8-py2.py3-none-any.whl pip-1.5.6-py2.py3-none-any.whl; do
                [ -f "$VE/$prereq" ] && continue
                echo "Fetching $PKG_URL/$prereq"
                $PYTHON -c "$PYGET" "$PKG_URL/$prereq" "$VE/$prereq" || exit 1;
            done;
            echo "Invoking virtualenv.py (this accesses pypi)"
            "$PYTHON" "$VE/virtualenv.py" --python="$PYTHON" $NSP_ARG "$VE" || exit 1
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
    gitStep,
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
                sqlalchemy_version='sqlalchemy',  # latest
                sqlalchemy_migrate_version='sqlalchemy-migrate',  # latest
                extra_packages=None, db=None,
                www=False, slave_only=False):
    if not extra_packages:
        extra_packages = []
    subs = dict(twisted_version=twisted_version, python_version=python_version)
    ve = "../sandbox-%(python_version)s-%(twisted_version)s" % subs
    if sqlalchemy_version != 'sqlalchemy':
        ve += '-' + sqlalchemy_version
    if sqlalchemy_migrate_version != 'sqlalchemy-migrate':
        ve += sqlalchemy_migrate_version.replace('sqlalchemy-migrate==', 'samigr-')
    subs['ve'] = ve

    if www:
        extra_packages.append('--editable=pkg')
        extra_packages.append('--editable=www/base')
        extra_packages.append('--editable=www/console_view')
        extra_packages.append('--editable=www/waterfall_view')

    virtualenv_packages = [twisted_version, sqlalchemy_version,
        sqlalchemy_migrate_version, 'multiprocessing==2.6.2.1', 'mock==0.8.0',
        '--editable=slave'] + extra_packages
    if python_version > 'python2.5':
        # because some of the dependencies don't work on 2.5
        virtualenv_packages.extend(['moto==0.3.1', 'boto==2.29.1'])
    if python_version in ('python2.4', 'python2.5'):
        # and, because the latest versions of these don't work on <2.5, and the version of
        # pip that works on 2.5 doesn't understand that '==' means 'I want this version'
        virtualenv_packages.insert(0, _PACKAGE_STASH + 'zope.interface-3.6.1.tar.gz')
        virtualenv_packages.insert(0, _PACKAGE_STASH + 'setuptools-1.4.2.tar.gz')
    else:
        virtualenv_packages.insert(0, _PACKAGE_STASH + 'zope.interface-4.1.1.tar.gz')
    if not slave_only:
        virtualenv_packages.append('--editable=master')
    f = factory.BuildFactory()
    f.addSteps([
    gitStep,
    VirtualenvSetup(name='virtualenv setup',
        no_site_packages=True,
        virtualenv_python=python_version,
        virtualenv_packages=virtualenv_packages,
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
    if db:
        # for DB, just test the master (the slave doesn't use the db)
        f.addSteps([
    DatabaseTrial(workdir="build/master", testpath='.',
        db=db,
        tests='buildbot.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test master'),
    ])
    elif www:
        # for www, run 'grunt ci'; this needs the virtualenv path in PATH
        f.addSteps([
    ShellCommand(workdir="build/www",
        command=['./node_modules/.bin/grunt', 'ci'],
        usePTY=False,
        name='grunt ci',
        env={'PATH':'../%(ve)s/bin/:${PATH}' % subs}),
    ])
    else:
        f.addSteps([
    Trial(workdir="build/slave", testpath='.',
        tests='buildslave.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test slave'),
    ])
    if not slave_only and not db:
        f.addSteps([
    Trial(workdir="build/master", testpath='.',
        tests='buildbot.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test master'),
    ])
    return f

def mkcoveragefactory():
    f = factory.BuildFactory()
    f.addSteps([
    gitStep,
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
            -d /home/buildbot/www/buildbot.buildbot.net/static/coverage \
            || exit 1;
        chmod -R a+rx /home/buildbot/www/buildbot.buildbot.net/static/coverage || exit 1
    """),
        description='coverage',
        descriptionDone='coverage',
        name='coverage report'),
    ])
    return f

def mkdocsfactory():
    f = factory.BuildFactory()
    f.addSteps([
        gitStep,
        FileDownload(mastersrc="virtualenv.py", slavedest="virtualenv.py", flunkOnFailure=True),

    # run docs tools in their own virtualenv, otherwise we end up documenting
    # the version of Buildbot running the metabuildbot!
    VirtualenvSetup(name='virtualenv setup',
        no_site_packages=True,
        virtualenv_packages=['sphinx==1.2.2', 'Pygments==2.0.1', '--editable=master', '--editable=slave'],
        virtualenv_dir='sandbox',
        haltOnFailure=True),

    # manual
    ShellCommand(command=Interpolate(textwrap.dedent("""\
        export VERSION=latest &&
        . sandbox/bin/activate &&
        gmake docs
        """)), name="create docs"),

    ])
    return f

def mklintyfactory():
    f = factory.BuildFactory()
    f.addSteps([
        gitStep,

        # run linty tools in their own virtualenv, so we can control the version
        # the version of Buildbot running the metabuildbot!
        VirtualenvSetup(name='virtualenv setup',
            no_site_packages=True,
            virtualenv_packages=['flake8', 'pep9==1.5.7', 'pylint==1.1.0', '--editable=master', '--editable=slave'],
            virtualenv_dir='../sandbox',
            haltOnFailure=True),

        ShellCommand(command="../sandbox/bin/pylint --rcfile common/pylintrc buildbot", name="pylint - master", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/pylint --rcfile common/pylintrc buildslave", name="pylint - slave", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc master/buildbot", name="flake8 - master", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc slave/buildslave", name="flake8 - slave", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc www/*/setup.py www/*/buildbot_*/", name="flake8 - www", flunkOnFailure=True),
    ])
    return f

def mkbuildsfactory():
    f = factory.BuildFactory()
    f.addSteps([
        gitStep,
        VirtualenvSetup(name='virtualenv setup',
            no_site_packages=True,
            virtualenv_packages=[
                # required to build www packages (#2877)
                '--editable=master', '--editable=pkg', 'mock',
                # required to make wheels
                'wheel',
                # ..and this is required to actually build them correctly (#2883)
                'setuptools'
            ],
            virtualenv_dir='../sandbox',
            haltOnFailure=True),
        RemoveDirectory(dir='build/uploads'),
        MakeDirectory(dir='build/uploads'),
    ])

    for name, workdir, command in [
            ('buildbot', 'build/master', 'sdist'),
            ('buildbot-slave', 'build/slave', 'sdist'),
            ('buildbot-pkg', 'build/pkg', 'sdist'),
            ('buildbot-www', 'build/www/base', 'bdist_wheel'),
            ('buildbot-console-view', 'build/www/console_view', 'bdist_wheel'),
            ('buildbot-waterfall-view', 'build/www/waterfall_view', 'bdist_wheel'),
            ('buildbot-codeparameter', 'build/www/codeparameter', 'bdist_wheel'),
        ]:
        levels = workdir.count('/') + 1
        sandbox = "../" * levels + "sandbox"
        extension = {'sdist': '.tar.gz', 'bdist_wheel': '-py2-none-any.whl'}[command]
        pkgname = name
        if command == 'bdist_wheel':
            pkgname = pkgname.replace('-', '_')  # wheels always use _
        f.addSteps([
            # the 'buildbot-www' package requires that the sandbox be *active* so that it
            # can find 'buildbot'
            ShellCommand(command="rm -rf dist/*; . %s/bin/activate; python setup.py %s"
                                 % (sandbox, command), workdir=workdir,
                         name=name, flunkOnFailure=True, haltOnFailure=False,
                         env={'BUILDBOT_VERSION': '1latest'}),  # wheels require a digit
            ShellCommand(command="""
                mv %(workdir)s/dist/%(pkgname)s-1latest%(extension)s build/uploads
            """ % dict(pkgname=pkgname, extension=extension, workdir=workdir),
                         name=name + " mv", flunkOnFailure=True, haltOnFailure=False,
                         workdir='.'),
        ])

    # now upload all of those.  SFTP is annoying to script.
    script = textwrap.dedent("""\
        # get the version from git, since 'buildbot.version' only has the x.y.z prefix
        VERSION=$(git describe --tags --always)

        version=$(mktemp)
        echo $VERSION >${version}

        readme=$(mktemp)
        cat <<EOF >${readme}
        This directory contains the latest versions of Buildbot, packaged as they would
        be for a release.

        These are most useful for developers wishing to use a working web UI without installing Node:

        pip intall http:s//ftp.buildbot.net/latest/buildbot-www-1latest-py2-none-any.whl

        The packages here are for ${VERSION}.

        EOF

        batchfile=$(mktemp)
        cat <<EOF >${batchfile}
        cd pub/latest
        put uploads/*
        put ${readme} README.txt
        chmod 644 README.txt
        put ${version} VERSION.txt
        chmod 644 VERSION.txt
        EOF


        sftp \
            -b ${batchfile} \
            -oPort=2200 \
            -oIdentityFile=~/.ssh/ftp.key \
            buildbot@ftp.int.buildbot.net
        rv=$?

        rm ${batchfile} ${readme} ${version}

        exit $rv""")
    f.addStep(ShellCommand(command=script, flunkOnFailure=True))
    return f

#### docs, coverage, etc.

builders.append({
    'name' : 'docs',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'factory' : mkdocsfactory(),
    'category' : 'docs' })

# Disable for now.
# NOTE(sa2ajj): I'd like to re-enable it later as it's a good example how this
# can be done and it's the best to keep it in a working shape.
#builders.append({
#    'name' : 'coverage',
#    'slavenames' : names(get_slaves(buildbot_net=True)),
#    'factory' : mkcoveragefactory(),
#    'category' : 'docs' })

builders.append({
    'name' : 'linty',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'factory' : mklintyfactory(),
    'category' : 'docs' })

builders.append({
    'name' : 'builds',
    'slavenames' : names(get_slaves(buildbot_net=True)),
    'factory' : mkbuildsfactory(),
    'category' : 'builds' })

#### single-slave builders

for sl in get_slaves(run_single=True).values():
    if sl.use_simple:
        f = mksimplefactory(test_master=sl.test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name' : 'slave-%s' % sl.slavename,
        'slavenames' : [ sl.slavename ],
        'factory' : f,
        'category' : 'slave' })

#### operating systems

for opsys in set(sl.os for sl in slaves if sl.os is not None):
    if 'win' in opsys:
        test_master = 'cygwin' not in opsys  # master doesn't work on cygwin
        f = mksimplefactory(test_master=test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name' : 'os-%s' % opsys,
        'slavenames' : names(get_slaves(os=opsys)),
        'factory' : f,
        'category' : 'os' })

#### databases

database_packages = {
    'postgres' : [
        # see http://trac.buildbot.net/ticket/2933#comment:4
        'pg8000==1.9.14',
    ],
    'mysql' : [ 'mysql-python' ],
}

for db in set(itertools.chain.from_iterable(sl.databases.keys() for sl in slaves)):
    f = mktestfactory(extra_packages=database_packages[db], db=db)
    builders.append({
        'name' : 'db-%s' % db,
        'slavenames' : names(get_slaves(db=db)),
        'factory' : f,
        'category' : 'db' })

#### www

# http://trac.buildbot.net/ticket/2877#comment:7
#f = mktestfactory(www=True)
#builders.append({
#    'name' : 'www',
#    'slavenames' : names(get_slaves(nodejs=True)),
#    'factory' : f,
#    'category' : 'www' })

#### config builders

twisted_versions = dict(
    tw0900='Twisted==9.0.0',
    tw1020='Twisted==10.2.0',
    tw1110='Twisted==11.1.0',
    tw1220='Twisted==12.2.0',
    tw1320='Twisted==13.2.0',
    tw1400='Twisted==14.0.0',
)

python_versions = dict(
    py26='python2.6',
    py27='python2.7',
)

# versions of twisted and python only supported by slave
slave_only_twisted = ['tw0900', 'tw1020']
slave_only_python = []

# incompatible versions of twisted and python
incompat_tw_py = [
    ('tw0900', 'py27'),
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
            'name' : name,
            'slavenames' : config_slaves,
            'factory' : f,
            'category' : 'config' })

pypy_versions = dict(
    pypy17='pypy1.7',
    pypy18='pypy1.8',
)

twisted_pypy_versions = dict(
    tw1110='Twisted==11.1.0',
    tw1200='Twisted==12.0.0',
)

for py, python_version in pypy_versions.items():
    config_slaves = names(get_slaves(run_config=True, **{py:True}))
    if not config_slaves:
        continue

    for tw, twisted_version in twisted_pypy_versions.items():
        f = mktestfactory(twisted_version=twisted_version, python_version=python_version)
        name = "%s-%s" % (py, tw)
        builders.append({
            'name' : name,
            'slavenames' : config_slaves,
            'factory' : f,
            'category' : 'config' })

config_slaves = names(get_slaves(run_config=True, py27=True))

sa087 = 'sqlalchemy==0.8.7'
sa099 = 'sqlalchemy==0.9.9'
sa100 = 'sqlalchemy==1.0.0'
sa1011 = 'sqlalchemy==1.0.11'
sam091 = 'sqlalchemy-migrate==0.9.1'
sam098 = 'sqlalchemy-migrate==0.9.8'
sam0100 = 'sqlalchemy-migrate==0.10.0'

sqlalchemy_combos = [
    (sa087, sam091),  (sa087, sam098),  (sa087, sam0100),
    (sa099, sam091),  (sa099, sam098),  (sa099, sam0100),
    (sa100, sam091),  (sa100, sam098),  (sa100, sam0100),
    (sa1011, sam091), (sa1011, sam098), (sa1011, sam0100),
]

for sa, sam in sqlalchemy_combos:
    f = mktestfactory(sqlalchemy_version=sa,
                      sqlalchemy_migrate_version=sam,
                      python_version='python2.7')
    # need to keep this short, as it becomes a filename
    name = ("%s-%s" % (sa, sam)) \
            .replace('sqlalchemy', 'sqla') \
            .replace('-migrate', 'm') \
            .replace('==', '=')
    builders.append({
        'name' : name,
        'slavenames' : config_slaves,
        'factory' : f,
        'category' : 'config' })
