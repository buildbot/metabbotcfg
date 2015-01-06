from buildbot.plugins import change_source

from metabbotcfg.common import GIT_URL

changesources = [
    change_source.GitPoller(repourl=GIT_URL,
                            branches=['master'],
                            pollInterval=60)
]
