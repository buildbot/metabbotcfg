# please follow docker best practices
# https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/
# Dockerfile customizations for building buildbot's CI test suite.
#
# Provided here as a real life example on how to make a customized
# worker Dockerfile for your project

FROM        buildbot/buildbot-worker:master
MAINTAINER  Buildbot Maintainers

# Switch to root to be able to install stuff
USER root

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

# Switch to root to be able to install stuff
USER root

# on debian postgresql sets default encoding to the one of the distro, so we need to force it for utf8
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG=en_US.utf8

# install the DB drivers we need to test against databases, as well as git and nodejs + phantomjs
RUN apt-get update && \
    curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y \
        libmysqlclient-dev \
        libjpeg-dev \
        libpq-dev \
        git \
        python-virtualenv \
        enchant \
        libenchant-dev \
        locales \
        aspell \
        aspell-en \
        ispell \
        iamerican \
        fontconfig \
        nodejs \
        postgresql \
        sudo \
        mysql-server && \
    \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 &&/
    curl -sL https://github.com/paladox/phantomjs/releases/download/2.1.7/phantomjs-2.1.1-linux-x86_64.tar.bz2 | \
    tar  --strip-components=1 -C /usr/local -xj phantomjs-2.1.1-linux-x86_64/bin/phantomjs && \
    npm install -g yarn && \
    rm -rf /var/lib/apt/lists/*

COPY pg_hba.conf /etc/postgresql/9.3/main/pg_hba.conf
COPY sudoers /etc/sudoers

RUN \
    /etc/init.d/mysql start && \
    mysql -e "CREATE USER 'travis'@'localhost';" && \
    mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'travis'@'localhost' WITH GRANT OPTION; FLUSH PRIVILEGES;" && \
    mysql -e 'create database bbtest;' && \
    /etc/init.d/postgresql start && \
    su postgres -c "createuser buildbot" && \
    su postgres -c "psql -c 'create database bbtest WITH ENCODING UTF8 TEMPLATE template0 ;'"
# Switch to regular user for security reasons
USER buildbot

# generate cache for the buildbot dependencies
RUN \
    mkdir -p /tmp/bb && \
    curl -sL https://github.com/buildbot/buildbot/archive/master.tar.gz | \
    tar  --strip-components=1 -C /tmp/bb -xz && \
    virtualenv /tmp/bb/sandbox && \
    . /tmp/bb/sandbox/bin/activate && \
    pip install -U pip && \
    pip install -e '/tmp/bb/master[test,docs,tls]' && \
    pip install -e /tmp/bb/pkg && \
    pip install -e /tmp/bb/www/base && \
    rm -rf /tmp/bb
