schedulers = []

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.forcesched import ForceScheduler, FixedParameter, StringParameter, ChoiceStringParameter

from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass
from metabbotcfg.slaves import slaves
from metabbotcfg import builders

schedulers.append(SingleBranchScheduler(name="all", branch='master',
                                 treeStableTimer=2,
                                 builderNames=[ b['name'] for b in builders.builders ]))

#schedulers.append(SingleBranchScheduler(name="release", branch='buildbot-0.8.9',
#                                 treeStableTimer=10,
#                                 builderNames=[ b['name'] for b in builders.builders if b['name'] not in ('docs',) ]))

schedulers.append(ForceScheduler(name="force",
    codebases=[''], # ?? {'repository': FixedParameter(name="repository", default='git://github.com/buildbot/buildbot.git')},
    #branch=ChoiceStringParameter(name="branch", default="master", choices=["master", "eight"]),
    #project=FixedParameter(name="project", default=""),
    properties=[],
    builderNames=[ b['name'] for b in builders.builders ]))
