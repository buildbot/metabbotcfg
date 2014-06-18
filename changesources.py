from buildbot.changes import gitpoller
changesources = []

changesources.append(gitpoller.GitPoller(repourl='https://github.com/buildbot/buildbot.git',
					 branches=['master'], pollInterval=60))
