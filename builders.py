import textwrap

from buildbot.process import factory
from buildbot.steps.source import Git
from buildbot.steps.shell import Compile, Test, ShellCommand
from buildbot.steps.transfer import FileDownload
from buildbot.steps.python_twisted import Trial

from metabbotcfg.slaves import slaves

builders = []

#### docs

# build on any of the slaves that can build docs
# TODO: make the results available somewhere

docs_factory = factory.BuildFactory()
docs_factory.addStep(Git(repourl='git://github.com/buildbot/buildbot.git', mode="update"))
docs_factory.addStep(ShellCommand(command="make docs", name="create docs"))
docs_factory.addStep(ShellCommand(command=textwrap.dedent("""\
		tar -C /home/buildbot/html/buildbot/docs -zvxf docs/docs.tgz latest/ &&
		chmod -R a+rx /home/buildbot/html/buildbot/docs/latest
		"""), name="docs to web", flunkOnFailure=True, haltOnFailure=True))
docs_factory.addStep(ShellCommand(command=textwrap.dedent("""\
		cd docs &&
		./gen-reference &&
		tar -cf - reference | tar -C /home/buildbot/html/buildbot/docs/latest -xf - &&
		chmod -R a+rx /home/buildbot/html/buildbot/docs/latest/reference
		"""), name="api docs to web", flunkOnFailure=True, haltOnFailure=True))
builders.append({
	'name' : 'docs',
	'slavenames' : [ 'buildbot.net' ],
	'workdir' : 'docs',
	'factory' : docs_factory,
	'category' : 'docs' })

#### simple slaves

# some slaves just do "simple" builds: get the source, run the tests.  These are mostly
# windows machines where we don't have a lot of flexibility to mess around with virtualenv
def mksimplefactory(slave):
	f = factory.BuildFactory()
	f.addSteps([
	Git(repourl='git://github.com/buildbot/buildbot.git', mode="copy"),
	#FileDownload(mastersrc="bbimport.py", slavedest="bbimport.py", flunkOnFailure=True),
	#ShellCommand(workdir="build/master", env={'PYTHONPATH' : '.;.'}, command=r"python ..\bbimport.py"),
	# use workdir instead of testpath because setuptools sticks its own eggs (including
	# the running version of buildbot) into sys.path *before* PYTHONPATH, but includes
	# "." in sys.path even before the eggs
	Trial(workdir="build/slave", testpath=".",
		env={ 'PYTHON_EGG_CACHE' : '../' },
		tests='buildslave.test',
		usePTY=False,
		name='test slave'),
	])
	if slave.test_master:
		f.addStep(
		Trial(workdir="build/master", testpath=".",
			env={ 'PYTHON_EGG_CACHE' : '../' },
			tests='buildbot.test',
			usePTY=False,
			name='test master'),
		)
	return f

for sl in slaves:
	if not sl.use_simple: continue
	if not sl.run_tests: continue
	name = sl.slavename
	builders.append({
		'name' : 'slave-%s' % name,
		'slavenames' : [ name ],
		'workdir' : 'slave-%s' % name,
		'factory' : mksimplefactory(sl),
		'category' : 'slave' })

#### full slaves

# this will eventually run against a variety of Twisted and Python versions on
# slaves that can support it, but for now it's a lot like the simple builders, except
# that it uses virtualenv
def mkfactory(*tests):
	f = factory.BuildFactory()
	f.addSteps([
	Git(repourl='git://github.com/buildbot/buildbot.git', mode="copy"),
	FileDownload(mastersrc="virtualenv.py", slavedest="virtualenv.py", flunkOnFailure=True),
	ShellCommand(usePTY=False, command=textwrap.dedent("""
		test -z "$PYTHON" && PYTHON=python;
		$PYTHON virtualenv.py --distribute --no-site-packages ../sandbox || exit 1;
		PYTHON=../sandbox/bin/python; PATH=../sandbox/bin:$PATH; 
		export PYTHON_EGG_CACHE=$PWD/..;
		# and somehow the install_requires in setup.py doesn't always work:
		$PYTHON -c 'import json' 2>/dev/null || $PYTHON -c 'import simplejson' ||
					../sandbox/bin/easy_install simplejson || exit 1;
		$PYTHON -c 'import sqlite3, sys; assert sys.version_info >= (2,6)' 2>/dev/null || $PYTHON -c 'import pysqlite2.dbapi2' ||
					../sandbox/bin/easy_install pysqlite || exit 1;
		../sandbox/bin/easy_install twisted || exit 1;
		../sandbox/bin/easy_install jinja2 || exit 1;
		../sandbox/bin/easy_install mock || exit 1;
	"""),
		flunkOnFailure=True,
		haltOnFailure=True,
		name="virtualenv setup"),
	ShellCommand(usePTY=False, command=textwrap.dedent("""
		PYTHON=../sandbox/bin/python; PATH=../sandbox/bin:$PATH; 
		export PYTHON_EGG_CACHE=$PWD/..;
		$PYTHON -c 'import sys; print "Python:", sys.version; import twisted; print "Twisted:", twisted.version'
	"""),
		name="versions"),
	# see note above about workdir vs. testpath
	Trial(workdir="build/slave", testpath='.',
		env={ 'PYTHON_EGG_CACHE' : '../../' },
		tests='buildslave.test',
		trial="../../sandbox/bin/trial",
		usePTY=False,
		name='test slave'),
	Trial(workdir="build/master", testpath='.',
		env={ 'PYTHON_EGG_CACHE' : '../../' },
		tests='buildbot.test',
		trial="../../sandbox/bin/trial",
		usePTY=False,
		name='test master'),
	])
	return f


for sl in slaves:
	if sl.use_simple: continue
	if not sl.run_tests: continue
	name = sl.slavename
	builders.append({
		'name' : 'slave-%s' % name,
		'slavenames' : [ name ],
		'workdir' : 'slave-%s' % name,
		'factory' : mkfactory(sl),
		'category' : 'full' })

##### sdist

# TODO
# build buildbot and buildslave source distributions, then untar them, build/install them into a new
# virtualenv, and run the tests there
