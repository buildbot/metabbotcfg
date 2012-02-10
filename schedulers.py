schedulers = []

from buildbot.schedulers.basic import Scheduler
from buildbot.schedulers.forcesched import ForceScheduler

from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass
from metabbotcfg.slaves import slaves
from metabbotcfg.builders import builders

schedulers.append(Scheduler(name="all", branch='master',
                                 treeStableTimer=10,
                                 builderNames=[ b['name'] for b in builders ]))
schedulers.append(ForceScheduler(name="force",
    builderNames=[ b['name'] for b in builders ]))
