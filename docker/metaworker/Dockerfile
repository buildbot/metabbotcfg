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

# install the DB drivers we need to test against databases, as well as git and nodejs
RUN apt-get update && \
    curl -sL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y software-properties-common && \
    # add python3.x repositories
    add-apt-repository -y ppa:deadsnakes/ppa  && \
    apt-get update && \
    apt-get install -y \
        libmysqlclient-dev \
        libjpeg-dev \
        libpq-dev \
        # selenium is a java thing
        default-jre \
        # chromium needs xvfb even with --headless
        xvfb \
        git \
        gconf2 \
        python3.5-venv \
        python3.6-venv \
        python3.7-venv \
        python3.8-venv \
        python3.9-venv \
        enchant \
        libenchant-dev \
        libcairo2-dev \
        locales \
        aspell \
        aspell-en \
        ispell \
        iamerican \
        fontconfig \
        nodejs \
        postgresql-12 \
        sudo \
        python3.5-dev  \
        python3.6-dev  \
        python3.7-dev  \
        python3.8-dev  \
        python3.9-dev  \
        python-dev     \
        mysql-server-8.0 && \
    \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    npm install -g yarn && \
    yarn global add protractor coffee-script && webdriver-manager update --chrome --no-gecko && \
    curl -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    (dpkg -i /tmp/chrome.deb || apt-get --fix-broken -y install) && \
    rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

COPY pg_hba.conf /etc/postgresql/12/main/pg_hba.conf
COPY prepare_postgres /prepare_postgres
COPY prepare_mysql /prepare_mysql
RUN sed -i "s/data_directory = '.*'/data_directory = '\/scratch\/postgres'/g" /etc/postgresql/12/main/postgresql.conf
RUN sed -i "s/.*datadir\\s*=.*/datadir='\/scratch\/mysql'/g" /etc/mysql/mysql.conf.d/mysqld.cnf
COPY sudoers /etc/sudoers

# Switch to regular user for security reasons
USER buildbot

# generate cache for the buildbot dependencies
RUN \
    mkdir -p /tmp/bb && \
    curl -sL https://github.com/buildbot/buildbot/archive/master.tar.gz | \
    tar  --strip-components=1 -C /tmp/bb -xz && \
    python3.7 -m venv /tmp/bb/sandbox && \
    . /tmp/bb/sandbox/bin/activate && \
    pip install -U pip && \
    pip install -e '/tmp/bb/master[test,docs,tls]' && \
    make -C /tmp/bb frontend_deps && \
    rm -rf /tmp/bb
