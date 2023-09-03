# please follow docker best practices
# https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/
# Dockerfile customizations for building buildbot's CI test suite.
#
# Provided here as a real life example on how to make a customized
# worker Dockerfile for your project

FROM buildbot/metabbotcfg-python AS python-build

FROM buildbot/buildbot-worker:master
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
        # selenium is a java thing
        default-jre \
        # chromium needs xvfb even with --headless
        xvfb \
        git \
        gconf2 \
        libcairo2-dev \
        locales \
        aspell \
        aspell-en \
        ispell \
        iamerican \
        fontconfig \
        nodejs \
        postgresql-13 \
        sudo \
        python3-dev \
        python3-venv  \
        mariadb-server-10.5 \
    \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && npm install -g yarn \
    && yarn global add protractor coffee-script \
    && webdriver-manager update --chrome --no-gecko \
    && curl -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && (dpkg -i /tmp/chrome.deb || apt-get --fix-broken -y install) \
    && rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

COPY pg_hba.conf /etc/postgresql/12/main/pg_hba.conf
COPY prepare_postgres /prepare_postgres
COPY prepare_mysql /prepare_mysql
RUN sed -i "s/data_directory = '.*'/data_directory = '\/scratch\/postgres'/g" /etc/postgresql/13/main/postgresql.conf
RUN sed -i "s/.*datadir\\s*=.*/datadir='\/scratch\/mysql'/g" /etc/mysql/mariadb.conf.d/50-server.cnf
COPY sudoers /etc/sudoers

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
