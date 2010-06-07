import sys, os
from buildbot.buildslave import BuildSlave

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

slaves = [
	# Steve 'Ashcrow' Milner
	MySlave('centos_5_python2_4', "linux", "24",
		),

 	# Dustin Mitchell
	MySlave('knuth.r.igoro.us', "linux", "25",
		has_texinfo=True,
		),

	MySlave('xp-cygwin-1.7', 'winxp', '25',
		use_simple=True,
		test_master=False, # master doesn't work on cygwin
		),
	MySlave('win7-py26', 'win7', '26',
		use_simple=True,
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
