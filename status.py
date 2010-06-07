status = []

from buildbot.status import html
status.append(html.WebStatus(http_port=8010, allowForce=False, order_console_by_time=True,
		revlink="http://github.com/djmitche/buildbot/commit/%s",
		changecommentlink=(r'\b#(\d+)\b', r'http://buildbot.net/trac/ticket/\1',
				   r'Ticket \g<0>')))

from buildbot.status import words
status.append(words.IRC(host="irc.freenode.net", nick="metabbot",
				notify_events={
					'successToFailure' : 1,
				},
                              channels=["#buildbot"]))



