import json
import os
import platform


def setupWWW(c):
    # if prod
    if 'nine' in platform.node():
        c['www']['port'] = 'tcp:8010:interface=192.168.80.244'
        c['buildbotURL'] = "https://nine.buildbot.net/"
    elif 'buildbot' in platform.node():
        c['www']['port'] = 'tcp:8010:interface=192.168.80.239'
        c['buildbotURL'] = "https://buildbot.buildbot.net/"
    else:  # for testing
        c['buildbotURL'] = "http://localhost:8010/"
    c['www']['plugins']['waterfall_view'] = {}
    c['www']['plugins']['grid_view'] = {}

    # read the password that ansible did sent to us, and override what is in the yaml
    creds = json.load(open(os.path.join(os.path.dirname(__file__), "github_oauth.pass")))
    c['www']['auth'].clientId = creds['clientid']
    c['www']['auth'].clientSecret = creds['clientsecret']
    c['www']['ui_default_config'] = {
        'Waterfall.scaling_waterfall': 0.19753086419753088,
        'Builders.show_old_builders': True,
        'Builders.buildFetchLimit': 1000,
    }
