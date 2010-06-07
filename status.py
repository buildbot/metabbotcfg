status = []

from buildbot.status import html
from buildbot.status.web.authz import Authz
from buildbot.status.web.auth import BasicAuth

users = [ ('dev', 'bbot!')] # it's not *that* secret..
authz = Authz(auth=BasicAuth(users),
	forceBuild='auth',
)
status.append(html.WebStatus(
		http_port=8010,
		authz=authz,
		order_console_by_time=True,
		revlink="http://github.com/djmitche/buildbot/commit/%s",
		changecommentlink=(r'\b#(\d+)\b', r'http://buildbot.net/trac/ticket/\1',
				   r'Ticket \g<0>')))

from buildbot.status import words
status.append(words.IRC(host="irc.freenode.net", nick="metabbot",
				notify_events={
					'successToFailure' : 1,
				},
                              channels=["#buildbot"]))



