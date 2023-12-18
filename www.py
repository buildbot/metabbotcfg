import json
import os


def setupWWW(c):
    listen_port = os.environ.get("BB_LISTEN_PORT", None)
    buildbot_url = os.environ.get("BB_URL", None)
    if listen_port is not None and buildbot_url is not None:
        c['www']['port'] = listen_port
        c['buildbotURL'] = buildbot_url
    else:  # for testing
        c['buildbotURL'] = "http://localhost:8010/"
    c["www"]["plugins"]["react_console_view"] = {}
    c["www"]["plugins"]["react_grid_view"] = {}
    c["www"]["plugins"]["react_waterfall_view"] = {}

    # read the password that ansible did sent to us, and override what is in the yaml
    creds = json.load(open(os.path.join(os.path.dirname(__file__), "github_oauth.pass")))
    c['www']['auth'].clientId = creds['clientid']
    c['www']['auth'].clientSecret = creds['clientsecret']
    c['www']['ui_default_config'] = {
        'Waterfall.scaling_waterfall': 0.19753086419753088,
        'Builders.show_old_builders': True,
        'Builders.buildFetchLimit': 1000,
    }
