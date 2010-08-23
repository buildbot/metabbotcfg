import sys, os
from buildbot.buildslave import BuildSlave
from buildbot.ec2buildslave import EC2LatentBuildSlave

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

	# true if this slave can contribute to the virtualenv-managed pool of
	# specific-configuration builders
	run_config = False

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

class MyEC2LatentBuildSlave(MySlaveBase, EC2LatentBuildSlave):
	def __init__(self, name, ec2type, **kwargs):
		password = self.get_pass(name)
		identifier, secret_identifier = self.get_ec2_creds(name)
		kwargs = self.extract_attrs(name, **kwargs)
		EC2LatentBuildSlave.__init__(self, name, password, ec2type,
			identifier=identifier, secret_identifier=secret_identifier, **kwargs)

slaves = [
	# Local
	MySlave('buildbot.net',
		buildbot_net=True,
		run_single=False,
		),

	# Steve 'Ashcrow' Milner
	MySlave('centos_5_python2_4',
		),

 	# Dustin Mitchell
	MySlave('knuth.r.igoro.us',
		run_single=False,
		run_config=True,
		),

	# maruel
	MySlave('xp-cygwin-1.7',
		use_simple=True,
		test_master=False, # master doesn't work on cygwin
		),

	MySlave('win7-py26',
		use_simple=True,
		),

	# Mozilla
	MySlave('cm-bbot-linux-001',
		run_single=False,
		run_config=True,
		),

	MySlave('cm-bbot-linux-002',
		run_single=False,
		run_config=True,
		),

	MySlave('cm-bbot-linux-003',
		run_single=False,
		run_config=True,
		),

	MySlave('cm-bbot-xp-001',
		use_simple=True,
		),

	MySlave('cm-bbot-xp-002',
		use_simple=True,
		),

	MySlave('cm-bbot-xp-003',
		use_simple=True,
		),

	# Zmanda (EC2)
	MyEC2LatentBuildSlave('ec2slave', 'm1.small',
		ami='ami-5a749c33',
		keypair_name='buildbot-setup',
		security_name='buildslaves',
		),
]

# these are slaves that haven't been up and from whose owners I have not heard in a while
retired_slaves = [
	# Dustin Sallings
	MySlave('ubuntu810-64'),
	MySlave('minime',
		max_builds=1),
	MySlave('minimata',
		),
	MySlave('freebsd_7',
		max_builds=1),

	# "Jeremy C. Reed" <reed@reedmedia.net> (emailed 2/2/10)
	MySlave('reed.tx.reedmedia.net'),

	# Tim Hatch <tim@timhatch.com> (emailed 2/3/10)
	MySlave('automan'),
]

def get_slaves(*args, **kwargs):
	rv = {}
	for arg in args:
		rv.update(arg)
	for sl in slaves:
		for k in kwargs:
			if getattr(sl, k) == kwargs[k]:
				rv[sl.slavename] = sl
	return rv

def names(slavedict):
	return slavedict.keys()
