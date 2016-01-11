# Provides a base Ubuntu (14.04) image with latest buildbot slave installed
# (based on twsited dockerfile https://github.com/cyli/docker-twisted)

# djmitche/buildbot-worker is built from https://github.com/buildbot/buildbot/blob/master/master/contrib/docker/slave/Dockerfile
FROM        djmitche/buildbot-worker
MAINTAINER  Buildbot Maintainers

# install the DB drivers we need to test against databases, as well as git
RUN apt-get install -y libmysqlclient-dev git
