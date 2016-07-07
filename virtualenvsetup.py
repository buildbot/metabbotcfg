import textwrap

from buildbot import locks
from buildbot.steps.shell import ShellCommand

# only allow one VirtualenvSetup to run on a slave at a time.  This prevents
# collisions in the shared package cache.
veLock = locks.SlaveLock('veLock')


# we hardcode a decent version of virtualenv here
VIRTUALENV_URL = 'https://pypi.python.org/packages/bf/f4/43525ce41d4de0128460da3dce059c2c969f4d076bbdbac21b6bc1e996e8/virtualenv-15.0.2-py2.py3-none-any.whl'  # noqa
VIRTUALENV_FILENAME = VIRTUALENV_URL.split("/")[-1]


class VirtualenvSetup(ShellCommand):
    def __init__(self, virtualenv_dir='sandbox', virtualenv_python='python2.7',
                 virtualenv_packages=[], **kwargs):
        kwargs['locks'] = kwargs.get('locks', []) + [veLock.access('exclusive')]
        ShellCommand.__init__(self, **kwargs)

        self.virtualenv_dir = virtualenv_dir
        self.virtualenv_python = virtualenv_python
        self.virtualenv_packages = virtualenv_packages

        self.addFactoryArguments(
            virtualenv_dir=virtualenv_dir,
            virtualenv_python=virtualenv_python,
            virtualenv_packages=virtualenv_packages)

    def buildCommand(self):
        # set up self.command as a very long sh -c invocation
        command = textwrap.dedent("""\
        PYTHON='{virtualenv_python}'
        VE='{virtualenv_dir}'
        VEPYTHON='{virtualenv_dir}/bin/python'

        # first, set up the virtualenv if it hasn't already been done, or if it's
        # broken (as sometimes happens when a slave's Python is updated)
        if ! test -f "$VE/bin/pip" || ! test -d "$VE/lib/$PYTHON" || ! "$VE/bin/python" -c 'import math'; then
            wget {VIRTUALENV_URL}
            unzip {VIRTUALENV_FILENAME}
            echo "Setting up virtualenv $VE";
            rm -rf "$VE";
            test -d "$VE" && {{ echo "$VE couldn't be removed"; exit 1; }};
            $PYTHON virtualenv.py -p $PYTHON "$VE" || exit 1;
        else
            echo "Virtualenv already exists"
        fi

        echo "Upgrading pip";
        $VE/bin/pip install -U pip

        echo "Installing {virtualenv_packages}";
        "$VE/bin/pip" install -U {virtualenv_packages} || exit 1

        if ! test -x "$VE/bin/trial"; then
            echo "adding $VE/bin/trial";
            ln -s `which trial` "$VE/bin/trial";
        fi

        echo "Checking for simplejson or json";
        "$VEPYTHON" -c 'import json' 2>/dev/null || "$VEPYTHON" -c 'import simplejson' ||
                    "$VE/bin/pip" install simplejson || exit 1;
        echo "Checking for sqlite3, including pysqlite3 on Python 2.5";
        "$VEPYTHON" -c 'import sqlite3, sys; assert sys.version_info >= (2,6)' 2>/dev/null ||
                    "$VEPYTHON" -c 'import pysqlite2.dbapi2' ||
                    "$VE/bin/pip" install pysqlite || exit 1

        """.format(VIRTUALENV_URL=VIRTUALENV_URL, VIRTUALENV_FILENAME=VIRTUALENV_FILENAME,
                   virtualenv_python=self.virtualenv_python, virtualenv_dir=self.virtualenv_dir,
                   virtualenv_packages=" ".join(self.virtualenv_packages)))
        return command

    def start(self):
        self.command = self.buildCommand()
        return ShellCommand.start(self)
