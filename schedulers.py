schedulers = []

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.forcesched import ForceScheduler, FixedParameter, StringParameter, ChoiceStringParameter

from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass
from metabbotcfg.slaves import slaves
from metabbotcfg import builders

from metabbotcfg.debian import schedulers as deb_schedulers

schedulers.append(SingleBranchScheduler(name="all", branch='master',
                                 treeStableTimer=10,
                                 builderNames=[ b['name'] for b in builders.master_builders ]))

schedulers.append(SingleBranchScheduler(name="release", branch='buildbot-0.8.7',
                                 treeStableTimer=10,
                                 builderNames=[ b['name'] for b in builders.master_builders ]))

#schedulers.append(SingleBranchScheduler(name="nine", branch='nine',
#                    treeStableTimer=5,
#                    builderNames=[ b['name'] for b in builders.nine_builders ]))

schedulers.append(ForceScheduler(name="force",
    repository=FixedParameter(name="repository", default='git://github.com/buildbot/buildbot.git'),
    branch=ChoiceStringParameter(name="branch", default="master", choices=["master", "nine"]),
    project=FixedParameter(name="project", default=""),
    properties=[],
    builderNames=[ b['name'] for b in builders.builders ]))

schedulers += deb_schedulers
