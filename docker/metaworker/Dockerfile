# please follow docker best practices
# https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/
# Dockerfile customizations for building buildbot's CI test suite.
#
# Provided here as a real life example on how to make a customized
# worker Dockerfile for your project

FROM docker.io/buildbot/metabbotcfg-python AS python-build

FROM docker.io/buildbot/buildbot-worker:master
MAINTAINER  Buildbot Maintainers

# Switch to root to be able to install stuff
USER root

# This will make apt-get install without question
ARG         DEBIAN_FRONTEND=noninteractive

# on debian postgresql sets default encoding to the one of the distro, so we need to force it for utf8
RUN apt-get update \
    && apt-get install -y locales \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

ENV LANG=en_US.utf8

# install the DB drivers we need to test against databases, as well as git and nodejs
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y \
        libmariadb-dev \
        libjpeg-dev \
        libpq-dev \
        postgresql-15 \
        mariadb-server-10.5 \
        # selenium is a java thing
        default-jre \
        # chromium needs xvfb even with --headless
        xvfb \
        git \
        locales \
        enchant-2 \
        libenchant-2-2 \
        libenchant-2-dev \
        aspell \
        aspell-en \
        ispell \
        iamerican \
        nodejs \
        fontconfig \
        gconf2 \
        gstreamer1.0-libav \
        libcairo2-dev \
        libegl1 \
        libenchant-2-2 \
        libevdev2 \
        libevent-2.1-7 \
        libflite1 \
        libgles2 \
        libgstreamer-gl1.0-0 \
        libgstreamer-plugins-bad1.0-0 \
        libgudev-1.0-0 \
        libharfbuzz-icu0 \
        libhyphen0 \
        libmanette-0.2-0 \
        libopenjp2-7 \
        libopus0 \
        libsecret-1-0 \
        libsoup2.4-1 \
        libwebpdemux2 \
        libwoff1 \
        python2-pip-whl \
        python2-setuptools-whl \
        python2-wheel-whl \
        python3-dev \
        python3-venv  \
    \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && npm install -g yarn \
    && yarn global add protractor \
    && curl -sL -o /tmp/chrome.deb https://github.com/p12tic/buildbot-test-data/raw/master/packages/google-chrome-stable_114.0.5735.198-1_amd64.deb \
    && (dpkg -i /tmp/chrome.deb || apt-get --fix-broken -y install) \
    && rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

COPY pg_hba.conf /etc/postgresql/15/main/pg_hba.conf
COPY prepare_postgres /prepare_postgres
COPY prepare_mysql /prepare_mysql

# container runtimes such as runsc (gVisor) do not support elevating privileges via sudo (missing
# setuid support). Therefore the permissions are adjusted to support running the database from the
# same container user as the tests.

RUN sed -i "s/data_directory = '.*'/data_directory = '\/scratch\/postgres'/g" /etc/postgresql/15/main/postgresql.conf
RUN sed -i "s/ssl\\s*=\\s*.*/ssl = off/g" /etc/postgresql/15/main/postgresql.conf
RUN sed -i "s/.*datadir\\s*=.*/datadir='\/scratch\/mysql'/g" /etc/mysql/mariadb.conf.d/50-server.cnf
RUN sed -i "s/.*user\\s*=.*/user=buildbot/g" /etc/mysql/mariadb.conf.d/50-server.cnf
RUN mkdir -p /scratch \
    && mkdir -p /run/mysqld \
    && mkdir -p /run/postgresql \
    && chown buildbot:buildbot /scratch \
    && chown buildbot:buildbot /run/mysqld \
    && chown buildbot:buildbot /run/postgresql \
    && chown buildbot:buildbot /var/log/postgresql \
    && rm -f /var/log/postgresql/* \
    && chown buildbot:buildbot /etc/mysql/debian.cnf

COPY --from=python-build /pyenv /pyenv
ENV PATH="/pyenv/pybin:${PATH}"

# Switch to regular user for security reasons
USER buildbot

# generate cache for the buildbot dependencies
RUN \
    mkdir -p /tmp/bb \
    && curl -sL https://github.com/buildbot/buildbot/archive/master.tar.gz | \
    tar  --strip-components=1 -C /tmp/bb -xz \
    && cd /tmp/bb \
    && python3 -m venv ./sandbox \
    && . ./sandbox/bin/activate \
    && pip install -U pip \
    && pip install -e 'master[test,docs,tls]' \
    && pip install \
        -r requirements-ci.txt \
        -r requirements-cidb.txt \
        -r requirements-cidocs.txt \
    && make frontend_deps \
    && cd / \
    && rm -rf /tmp/bb
