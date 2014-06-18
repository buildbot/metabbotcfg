status = []

from buildbot.status import words
status.append(words.IRC(host="irc.freenode.net", nick="bb-9-meta",
				notify_events={
					'successToFailure' : 1,
					'failureToSuccess' : 1,
				},
                channels=["#buildbot"]))
