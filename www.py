import json
import os
import platform


def setupWWW(c):
    # if prod
    if platform.node() == 'nine':
        c['www']['port'] = 'tcp:8010:interface=192.168.80.244'
        c['buildbotURL'] = "https://nine.buildbot.net/"
    else:  # for testing
        c['buildbotURL'] = "http://localhost:8010/"
    c['www']['plugins']['waterfall_view'] = {}

    # read the password that ansible did sent to us, and override what is in the yaml
    creds = json.load(open(os.path.join(os.path.dirname(__file__), "github_oauth.pass")))
    c['www']['auth'].clientId = creds['client_id']
    c['www']['auth'].clientSecret = creds['client_secret']
