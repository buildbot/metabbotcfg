from buildbot.changes import gitpoller

from metabbotcfg.common import GIT_URL

changesources = []

changesources.append(gitpoller.GitPoller(repourl=GIT_URL,
					 branches=['master'], pollInterval=60))
