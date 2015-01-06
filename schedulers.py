from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.forcesched import ForceScheduler, FixedParameter, StringParameter, ChoiceStringParameter
from buildbot.schedulers.timed import Periodic
from buildbot.schedulers.trysched import Try_Userpass

from metabbotcfg import builders

schedulers = [
    SingleBranchScheduler(name="all", branch='master',
                          treeStableTimer=2,
                          builderNames=[b['name'] for b in builders.builders]),
#   SingleBranchScheduler(name="release", branch='buildbot-0.8.9',
#                         treeStableTimer=10,
#                         builderNames=[b['name'] for b in builders.builders if b['name'] not in ('docs',)])),
    ForceScheduler(name="force",
                   codebases=[''], # ?? {'repository': FixedParameter(name="repository", default='git://github.com/buildbot/buildbot.git')},
                   #branch=ChoiceStringParameter(name="branch", default="master", choices=["master", "eight"]),
                   #project=FixedParameter(name="project", default=""),
                   properties=[],
                   builderNames=[b['name'] for b in builders.builders])
]
