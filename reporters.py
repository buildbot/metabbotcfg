from buildbot.plugins import reporters
from buildbot.plugins import util


def setup_reporters(c):
    with open("metabbotcfg/github_token") as f:
        token = f.read().strip()
    c["services"].append(
        reporters.GitHubStatusPush(
            token,
            context=util.Interpolate(
                "bb%(prop:TESTS:+/)s%(prop:TESTS)s%(prop:TESTS:+/)s%(prop:PYTHON)s"
                "%(prop:TESTS:+/tw:)s%(prop:TWISTED)s%(prop:TESTS:+/sqla:)s"
                "%(prop:SQLALCHEMY)s%(prop:TESTS:+/db:)s%(prop:BUILDBOT_TEST_DB_URL)s"
                "%(prop:TESTS:+/wp:)s%(prop:WORKER_PYTHON)s"
            ),
            verbose=True,
        )
    )
