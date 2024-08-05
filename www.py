import json
import os

from buildbot.plugins import util


def setupWWW(c):
    listen_port = os.environ.get("BB_LISTEN_PORT", None)
    buildbot_url = os.environ.get("BB_URL", None)
    c['www'] = {
        'change_hook_dialects': {'github': {'codebase': 'buildbot'}},
        'plugins': {'console_view': True, 'waterfall_view': True},
    }
    if listen_port is not None and buildbot_url is not None:
        c['www']['port'] = listen_port
        c['buildbotURL'] = buildbot_url
    else:  # for testing
        c['buildbotURL'] = "http://localhost:8010/"

    # read the password that ansible did sent to us, and override what is in the yaml
    creds = json.load(open(os.path.join(os.path.dirname(__file__), "github_oauth.pass")))

    c['www']['auth'] = util.GitHubAuth(creds['clientid'], creds['clientsecret'])
    c['www']['ui_default_config'] = {
        'Waterfall.scaling_waterfall': 0.19753086419753088,
        'Builders.show_old_builders': True,
        'Builders.buildFetchLimit': 1000,
    }
    c['www']['authz'] = util.Authz(
        [
            util.AnyEndpointMatcher(role='buildbot', defaultDeny=False),
            util.StopBuildEndpointMatcher(role='owner'),
            util.RebuildBuildEndpointMatcher(role='owner'),
            util.AnyControlEndpointMatcher(role='buildbot', defaultDeny=True),
        ],
        [util.RolesFromGroups(groupPrefix='')],
    )
