schedulers = []

from buildbot.schedulers.basic import Scheduler
from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass
from metabbotcfg.slaves import slaves

schedulers.append(Scheduler(name="all", branch='master',
                                 treeStableTimer=10,
                                 builderNames=
					[ 'docs', ] +
					[ 'slave-%s' % sl.slavename for sl in slaves if sl.run_tests ]))
