from buildbot.status import words

status = []

if 0:
    status.append(words.IRC(host="irc.freenode.net",
                            nick="bb-9-meta",
                            notify_events={
                                'successToFailure' : 1,
                                'failureToSuccess' : 1,
                            },
                            channels=["#buildbot"]))
