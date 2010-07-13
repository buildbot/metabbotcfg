schedulers = []

from buildbot.scheduler import Scheduler, Periodic
from metabbotcfg.slaves import slaves

schedulers.append(Scheduler(name="all", branch='master',
                                 treeStableTimer=10,
                                 builderNames=
					[ 'docs', ] +
					[ 'slave-%s' % sl.slavename for sl in slaves if sl.run_tests ]))


