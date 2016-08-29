from buildbot.plugins import reporters as reporters_plugins

reporters = []

reporters.append(
    reporters_plugins.IRC(host="irc.freenode.net",
                          nick="bb-9-meta",
                          notify_events={
                              'successToFailure': 1,
                              'failureToSuccess': 1,
                          },
                          channels=["#buildbot"]))
