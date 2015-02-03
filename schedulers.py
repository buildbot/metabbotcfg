from buildbot.plugins import schedulers as bbsched
from buildbot.plugins import util

from metabbotcfg import builders

schedulers = [
    bbsched.SingleBranchScheduler(
        name="all",
        branch='master',
        treeStableTimer=2,
        builderNames=[b['name'] for b in builders.builders]),
#   SingleBranchScheduler(
#       name="release",
#       branch='buildbot-0.8.9',
#       treeStableTimer=10,
#       builderNames=[b['name'] for b in builders.builders if b['name'] not in ('docs',)])),
    bbsched.ForceScheduler(
        name="force",
        codebases=[''], # ?? {'repository': util.FixedParameter(name="repository", default='git://github.com/buildbot/buildbot.git')},
        #branch=util.ChoiceStringParameter(name="branch", default="master", choices=["master", "eight"]),
        #project=util.FixedParameter(name="project", default=""),
        properties=[],
        builderNames=[b['name'] for b in builders.builders])
]
