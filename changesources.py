from buildbot.plugins import changes

from metabbotcfg.common import GIT_URL

changesources = [
    changes.GitPoller(repourl=GIT_URL,
                      branches=['master'],
                      pollInterval=60)
]
