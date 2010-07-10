import sys, os
from buildbot.buildslave import BuildSlave
from buildbot.ec2buildslave import EC2LatentBuildSlave

class MySlave(BuildSlave):
	def __init__(self, name, os, py, has_texinfo=False, use_simple=False,
			test_master=True, **kwargs):
		password = self.get_pass(name)
		BuildSlave.__init__(self, name, password, **kwargs)
		self.slavename = name
		self.os = os
		self.py = py
		# true if this box can build docs
		self.has_texinfo = has_texinfo
		# true if this box should use a 'simple' factory, meaning no virtualenv
		# (basically good for windows)
		self.use_simple = use_simple
		# true if this box can test the buildmaster
		self.test_master = test_master

	def get_pass(self, name):
		# get the password based on the name
		path = os.path.join(os.path.dirname(__file__), "%s.pass" % name)
		pw = open(path).read().strip()
		return pw

class MyEC2LatentBuildSlave(EC2LatentBuildSlave):
	def __init__(self, name, ec2type, os, py, has_texinfo=False, use_simple=False,
			test_master=True, **kwargs):
		password = self.get_pass(name)
		identifier, secret_identifier = self.get_ec2_creds(name)
		EC2LatentBuildSlave.__init__(self, name, password, ec2type,
			identifier=identifier, secret_identifier=secret_identifier, **kwargs)
		self.slavename = name
		self.os = os
		self.py = py
		# true if this box can build docs
		self.has_texinfo = has_texinfo
		# true if this box should use a 'simple' factory, meaning no virtualenv
		# (basically good for windows)
		self.use_simple = use_simple
		# true if this box can test the buildmaster
		self.test_master = test_master

	def get_pass(self, name):
		# get the password based on the name
		path = os.path.join(os.path.dirname(__file__), "%s.pass" % name)
		pw = open(path).read().strip()
		return pw

	def get_ec2_creds(self, name):
		path = os.path.join(os.path.dirname(__file__), "%s.ec2" % name)
		return open(path).read().strip().split(" ")

slaves = [
	# Local
	MySlave('buildbot.net', 'linux', '25',
		has_texinfo=True,
		),

	# Steve 'Ashcrow' Milner
	MySlave('centos_5_python2_4', "linux", "24",
		),

 	# Dustin Mitchell
	MySlave('knuth.r.igoro.us', "linux", "25",
		has_texinfo=True,
		),

	# maruel
	MySlave('xp-cygwin-1.7', 'winxp', '25',
		use_simple=True,
		test_master=False, # master doesn't work on cygwin
		),

	MySlave('win7-py26', 'win7', '26',
		use_simple=True,
		),

	# Mozilla
	MySlave('cm-bbot-linux-002', 'linux', '26',
		),

	MySlave('cm-bbot-linux-003', 'linux', '26',
		),

	# Zmanda (EC2)
	MyEC2LatentBuildSlave('ec2slave', 'm1.small', 'linux', '25',
		ami='ami-5a749c33',
		keypair_name='buildbot-setup',
		security_name='buildslaves',
		),
]

# these are slaves that haven't been up and from whose owners I have not heard in a while
retired_slaves = [
	# Dustin Sallings
	MySlave('ubuntu810-64', "linux", "810", "25"),
	MySlave('minime', "macosx", "250", "25",
		max_builds=1),
	MySlave('minimata', "macosx", "250", "25",
		),
	MySlave('freebsd_7', "freebsd", "820", "25",
		max_builds=1),

	# "Jeremy C. Reed" <reed@reedmedia.net> (emailed 2/2/10)
	MySlave('reed.tx.reedmedia.net', "netbsd", "820", "25"),

	# Tim Hatch <tim@timhatch.com> (emailed 2/3/10)
	MySlave('automan', 'windows-xp-sp2', '900', '26'),
]
