import platform


def setupWWW(c):
    if platform.node() == 'nine':
        c['www']['port'] = 'tcp:8010:interface=192.168.80.244'
    c['www']['plugins']['waterfall_view'] = {}
    c['www']['change_hook_dialects'] = {'github': {}}
