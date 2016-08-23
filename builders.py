import itertools
import textwrap

from buildbot.process import factory
from buildbot.process.properties import Interpolate
from buildbot.steps.python_twisted import Trial
from buildbot.steps.shell import ShellCommand
from buildbot.steps.slave import MakeDirectory, RemoveDirectory
from buildbot.steps.source.git import Git
from buildbot.steps.transfer import FileDownload
from metabbotcfg.common import GIT_URL
from metabbotcfg.slaves import get_slaves, names, slaves
from metabbotcfg.virtualenvsetup import VirtualenvSetup

_PACKAGE_STASH = 'http://ftp.buildbot.net/pub/metabuildbot/python-packages/'

builders = []

# slaves seem to have a hard time fetching from github, so retry
gitStep = Git(repourl=GIT_URL, mode='full', method='fresh', retryFetch=True)
downloadStep = FileDownload(mastersrc="metabbotcfg/virtualenv.whl", slavedest="virtualenv.whl", flunkOnFailure=True)


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


# some slaves just do "simple" builds: get the source, run the tests.  These are mostly
# windows machines where we don't have a lot of flexibility to mess around with virtualenv
def mksimplefactory(test_master=True):
    f = factory.BuildFactory()
    f.addSteps([
        gitStep,
        # use workdir instead of testpath because setuptools sticks its own eggs (including
        # the running version of buildbot) into sys.path *before* PYTHONPATH, but includes
        # "." in sys.path even before the eggs
        Trial(workdir="build/worker", testpath=".",
              tests='buildbot_worker.test',
              usePTY=False,
              name='test worker'),
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
def mktestfactory(twisted_version=None, python_version='python',
                sqlalchemy_version=None,  # latest taken by master's setup.py
                sqlalchemy_migrate_version=None,  # latest taken by master's setup.py
                extra_packages=None, db=None,
                www=False, slave_only=False):
    if not extra_packages:
        extra_packages = []
    subs = dict(twisted_version=twisted_version, python_version=python_version)
    ve = "../sandbox-%(python_version)s-%(twisted_version)s" % subs
    if sqlalchemy_version is not None:
        ve += '-' + sqlalchemy_version
    if sqlalchemy_migrate_version is not None:
        ve += sqlalchemy_migrate_version.replace('sqlalchemy-migrate==', 'samigr-')
    subs['ve'] = ve

    virtualenv_packages = []

    def maybeAppend(*args):
        for v in args:
            if v is not None:
                virtualenv_packages.append(v)

    maybeAppend(twisted_version, sqlalchemy_version,
                sqlalchemy_migrate_version)

    if www:
        maybeAppend('--editable=pkg',
                    '--editable=www/base',
                    '--editable=www/console_view',
                    '--editable=www/waterfall_view')

    if not slave_only:
        maybeAppend('--editable=master[test,tls]')
    # master[test] embeddeds all test deps, but not worker, which only needs mock
    else:
        maybeAppend('mock')
    maybeAppend('--editable=worker')

    f = factory.BuildFactory()
    f.addSteps([
    gitStep, downloadStep,
    VirtualenvSetup(name='virtualenv setup',
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
        env={'PATH': '../%(ve)s/bin/:${PATH}' % subs}),
    ])
    else:
        f.addSteps([
    Trial(workdir="build/worker", testpath='.',
        tests='buildbot_worker.test',
        trial="../%(ve)s/bin/trial" % subs,
        usePTY=False,
        name='test worker'),
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
    gitStep, downloadStep,
    VirtualenvSetup(name='virtualenv setup',
        virtualenv_packages=['coverage', 'mock', '--editable=master[tls,test]', '--editable=worker'],
        virtualenv_dir='sandbox',
        haltOnFailure=True),
    ShellCommand(usePTY=False, command=textwrap.dedent("""
        PYTHON=sandbox/bin/python;
        sandbox/bin/coverage run --rcfile=common/coveragerc \
            sandbox/bin/trial buildbot.test buildbot_worker.test \
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
        gitStep, downloadStep,

    # run docs tools in their own virtualenv, otherwise we end up documenting
    # the version of Buildbot running the metabuildbot!
    VirtualenvSetup(name='virtualenv setup',
        virtualenv_packages=['--editable=master[docs]', '--editable=worker'],
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
        gitStep, downloadStep,

        # run linty tools in their own virtualenv, so we can control the version
        # the version of Buildbot running the metabuildbot!
        VirtualenvSetup(name='virtualenv setup',
            virtualenv_packages=['flake8', 'pep8==1.5.7', 'pylint==1.1.0', '--editable=master[tls,test]', '--editable=worker'],
            virtualenv_dir='../sandbox',
            haltOnFailure=True),

        ShellCommand(command="../sandbox/bin/pylint --rcfile common/pylintrc buildbot", name="pylint - master", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/pylint --rcfile common/pylintrc buildbot_worker", name="pylint - worker", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc master/buildbot", name="flake8 - master", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc worker/buildbot_worker", name="flake8 - worker", flunkOnFailure=True),
        ShellCommand(command="../sandbox/bin/flake8 --config common/flake8rc www/*/setup.py www/*/buildbot_*/", name="flake8 - www", flunkOnFailure=True),
    ])
    return f


def mkbuildsfactory():
    f = factory.BuildFactory()
    f.addSteps([
        gitStep, downloadStep,
        VirtualenvSetup(name='virtualenv setup',
            virtualenv_packages=[
                # required to build www packages (#2877)
                '--editable=master[tls,test]', '--editable=pkg', 'mock',
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
        ('buildbot-worker', 'build/worker', 'sdist'),
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

builders.append({
    'name': 'docs',
    'slavenames': names(get_slaves(buildbot_net=True)),
    'factory': mkdocsfactory(),
    'category': 'docs'
})

# Disable for now.
# NOTE(sa2ajj): I'd like to re-enable it later as it's a good example how this
# can be done and it's the best to keep it in a working shape.
# builders.append({
#     'name': 'coverage',
#     'slavenames': names(get_slaves(buildbot_net=True)),
#     'factory': mkcoveragefactory(),
#     'category': 'docs' })

builders.append({
    'name': 'linty',
    'slavenames': names(get_slaves(buildbot_net=True)),
    'factory': mklintyfactory(),
    'category': 'docs'
})

builders.append({
    'name': 'builds',
    'slavenames': names(get_slaves(buildbot_net=True)),
    'factory': mkbuildsfactory(),
    'category': 'builds'
})

for sl in get_slaves(run_single=True).values():
    if sl.use_simple:
        f = mksimplefactory(test_master=sl.test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name': 'slave-%s' % sl.slavename,
        'slavenames': [sl.slavename],
        'factory': f,
        'category': 'slave'
    })


for opsys in set(sl.os for sl in slaves if sl.os is not None):
    if 'win' in opsys:
        test_master = 'cygwin' not in opsys  # master doesn't work on cygwin
        f = mksimplefactory(test_master=test_master)
    else:
        f = mktestfactory()
    builders.append({
        'name': 'os-%s' % opsys,
        'slavenames': names(get_slaves(os=opsys)),
        'factory': f,
        'category': 'os'
    })

database_packages = {
    'postgres': [
        # see http://trac.buildbot.net/ticket/2933#comment:4
        'pg8000==1.9.14',
    ],
    'mysql': ['mysql-python'],
}

for db in set(itertools.chain.from_iterable(sl.databases.keys() for sl in slaves)):
    f = mktestfactory(extra_packages=database_packages[db], 
                      db=db,
                      python_version='python2.7')
    builders.append({
        'name': 'db-%s' % db,
        'slavenames': names(get_slaves(db=db)),
        'factory': f,
        'category': 'db'
    })

# http://trac.buildbot.net/ticket/2877#comment:7
# f = mktestfactory(www=True)
# builders.append({
#     'name': 'www',
#     'slavenames': names(get_slaves(nodejs=True)),
#     'factory': f,
#     'category': 'www' })

twisted_versions = dict(
    tw0900='Twisted==9.0.0',
    tw1020='Twisted==10.2.0',
    tw1110='Twisted==11.1.0',
    tw1220='Twisted==12.2.0',
    tw1320='Twisted==13.2.0',
    tw1402='Twisted==14.0.2',
    tw1611='Twisted==16.1.1',
)

python_versions = dict(
    py26='python2.6',
    py27='python2.7',
)

# versions of twisted and python only supported by slave
slave_only_twisted = ['tw0900', 'tw1020', 'tw1110', 'tw1220', 'tw1320']
slave_only_python = ['py26']

# incompatible versions of twisted and python
incompat_tw_py = [
    ('tw0900', 'py27'),
    ('tw1611', 'py26'),
]

for py, python_version in python_versions.items():
    for tw, twisted_version in twisted_versions.items():
        config_slaves = names(get_slaves(run_config=True, **{py: True, tw: True}))
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
            'category': 'config'
        })

pypy_versions = dict(
    pypy17='pypy1.7',
    pypy18='pypy1.8',
)

twisted_pypy_versions = dict(
    tw1110='Twisted==11.1.0',
    tw1200='Twisted==12.0.0',
)

for py, python_version in pypy_versions.items():
    config_slaves = names(get_slaves(run_config=True, **{py: True}))
    if not config_slaves:
        continue

    for tw, twisted_version in twisted_pypy_versions.items():
        f = mktestfactory(twisted_version=twisted_version, python_version=python_version)
        name = "%s-%s" % (py, tw)
        builders.append({
            'name': name,
            'slavenames': config_slaves,
            'factory': f,
            'category': 'config'
        })

config_slaves = names(get_slaves(run_config=True, py27=True))

sa087 = 'sqlalchemy==0.8.7'
sa099 = 'sqlalchemy==0.9.9'
sa100 = 'sqlalchemy==1.0.0'
sa1011 = 'sqlalchemy==1.0.11'
sam091 = 'sqlalchemy-migrate==0.9.1'
sam098 = 'sqlalchemy-migrate==0.9.8'
sam0100 = 'sqlalchemy-migrate==0.10.0'

sqlalchemy_combos = [
    (sa087, sam091), (sa087, sam098), (sa087, sam0100),
    (sa099, sam091), (sa099, sam098), (sa099, sam0100),
    (sa100, sam091), (sa100, sam098), (sa100, sam0100),
    (sa1011, sam091), (sa1011, sam098), (sa1011, sam0100),
]

for sa, sam in sqlalchemy_combos:
    f = mktestfactory(sqlalchemy_version=sa,
                      sqlalchemy_migrate_version=sam,
                      python_version='python2.7')
    # need to keep this short, as it becomes a filename
    name = (("%s-%s" % (sa, sam))
            .replace('sqlalchemy', 'sqla')
            .replace('-migrate', 'm')
            .replace('==', '='))
    builders.append({
        'name': name,
        'slavenames': config_slaves,
        'factory': f,
        'category': 'config'
    })
