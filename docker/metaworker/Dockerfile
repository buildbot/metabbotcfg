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
# install the DB drivers we need to test against databases, as well as git and nodejs + phantomjs
RUN apt-get update && \
    curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y \
        libmysqlclient-dev \
        libpq-dev \
        git \
        python-virtualenv \
        enchant \
        libenchant-dev \
        aspell \
        aspell-en \
        ispell \
        iamerican \
        fontconfig \
        nodejs \
        postgresql \
        mysql-server && \
    \
    curl -sL https://github.com/paladox/phantomjs/releases/download/2.1.7/phantomjs-2.1.1-linux-x86_64.tar.bz2 | \
    tar  --strip-components=1 -C /usr/local -xj phantomjs-2.1.1-linux-x86_64/bin/phantomjs && \
    rm -rf /var/lib/apt/lists/*

COPY pg_hba.conf /etc/postgresql/9.3/main/pg_hba.conf
COPY sudoers /etc/sudoers

RUN \
    /etc/init.d/mysql start && \
    /etc/init.d/postgresql start && \
    mysql -e "CREATE USER 'travis'@'localhost';" && \
    mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'travis'@'localhost' WITH GRANT OPTION; FLUSH PRIVILEGES;" && \
    mysql -e 'create database bbtest;' && \
    psql -c 'create database bbtest;' -U postgres

# Switch to regular user for security reasons
USER buildbot
