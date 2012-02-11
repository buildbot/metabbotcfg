schedulers = []

from buildbot.schedulers.basic import Scheduler
from buildbot.schedulers.forcesched import ForceScheduler, FixedParameter, StringParameter

from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass
from metabbotcfg.slaves import slaves
from metabbotcfg import builders

schedulers.append(Scheduler(name="all", branch='master',
                                 treeStableTimer=10,
                                 builderNames=[ b['name'] for b in builders.builders ]))
schedulers.append(ForceScheduler(name="force",
    repository=FixedParameter(name="repository", default='git://github.com/buildbot/buildbot.git'),
    branch=StringParameter(name="branch", default="master"),
    project=FixedParameter(name="project", default=""),
    properties=[],
    builderNames=[ b['name'] for b in builders.builders ]))
