# Provides a base Ubuntu (14.04) image with latest buildbot slave installed
# (based on twsited dockerfile https://github.com/cyli/docker-twisted)

# djmitche/buildbot-worker is built from https://github.com/buildbot/buildbot/blob/master/master/contrib/docker/slave/Dockerfile
FROM        buildbot/buildbot-worker:latest
MAINTAINER  Buildbot Maintainers

RUN apt-get update
RUN apt-get install -y curl

# Test runs produce a great quantity of dead grandchild processes.  In a
# non-docker environment, these are automatically reaped by init (process 1),
# so we need to simulate that here.  See https://github.com/Yelp/dumb-init
RUN curl -Lo /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.0.0/dumb-init_1.0.0_amd64
RUN chmod +x /usr/local/bin/dumb-init
CMD ["/usr/local/bin/dumb-init", "twistd", "-ny", "buildbot.tac"]

# install the DB drivers we need to test against databases, as well as git
RUN apt-get install -y libmysqlclient-dev libpq-dev git
