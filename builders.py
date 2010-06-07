import textwrap

from buildbot.process import factory
from buildbot.steps.source import Git
from buildbot.steps.shell import Compile, Test, ShellCommand
from buildbot.steps.transfer import FileDownload
from buildbot.steps.python_twisted import Trial

from metabbotcfg.slaves import slaves

def mkfactory(*tests):
	f = factory.BuildFactory()
	f.addSteps([
	Git(repourl='git://github.com/djmitche/buildbot.git', mode="copy"),
	FileDownload(mastersrc="virtualenv.py", slavedest="virtualenv.py", flunkOnFailure=True),
	ShellCommand(usePTY=False, command=textwrap.dedent("""
		test -z "$PYTHON" && PYTHON=python;
		$PYTHON virtualenv.py --distribute --no-site-packages ../sandbox || exit 1;
		PYTHON=../sandbox/bin/python; PATH=../sandbox/bin:$PATH; 
		export PYTHON_EGG_CACHE=$PWD/..;
		# and somehow the install_requires in setup.py doesn't always work:
		$PYTHON -c 'import json' || $PYTHON -c 'import simplejson' ||
					../sandbox/bin/easy_install simplejson || exit 1;
		$PYTHON -c 'import sqlite3' || $PYTHON -c 'import pysqlite2.dbapi2' ||
					../sandbox/bin/easy_install pysqlite || exit 1;
		../sandbox/bin/easy_install mock || exit 1;
		$PYTHON setup.py build install || exit 1;
	"""),
		flunkOnFailure=True,
		name="virtualenv install and build"),
	ShellCommand(usePTY=False, command=textwrap.dedent("""
		PYTHON=../sandbox/bin/python; PATH=../sandbox/bin:$PATH; 
		export PYTHON_EGG_CACHE=$PWD/..;
		$PYTHON -c 'print "USING VIRTUALENV"; import sys; print sys.version; import twisted; print twisted.version'
	"""),
		name="versions"),
	Trial(testpath=".",
		env={ 'PYTHON_EGG_CACHE' : '../' },
		tests=list(tests),
		trial="../sandbox/bin/trial", usePTY=False),
	])
	return f

def mksimplefactory(*tests):
	f = factory.BuildFactory()
	f.addSteps([
	Git(repourl='git://github.com/djmitche/buildbot.git', mode="copy"),
	Trial(testpath=".",
		env={ 'PYTHON_EGG_CACHE' : '../' },
		tests=list(tests),
		usePTY=False),
	])
	return f

virtualenv_factory = mkfactory('buildbot.test')
simple_factory = mksimplefactory('buildbot.test')

docs_factory = factory.BuildFactory()
docs_factory.addStep(Git(repourl='git://github.com/djmitche/buildbot.git', mode="update"))
docs_factory.addStep(ShellCommand(command="make docs", name="create docs"))

builders = []
builders.append({
	'name' : 'docs',
	'slavenames' : [ sl.slavename for sl in slaves if sl.has_texinfo ],
	'builddir' : 'docs',
	'factory' : docs_factory,
	'category' : 'docs' })

for sl in slaves:
	name = sl.slavename
	fact = virtualenv_factory
	if sl.use_simple:
		fact = simple_factory
	builders.append({
		'name' : 'slave-%s' % name,
		'slavenames' : [ name ],
		'builddir' : 'slave-%s' % name,
		'factory' : fact,
		'category' : 'full' })
