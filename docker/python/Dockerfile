FROM debian:12
LABEL org.opencontainers.image.authors="Buildbot Maintainers"

USER root

RUN apt-get update \
    && apt-get install -y \
        bzip2 \
        curl \
        gcc \
        git \
        make \
        libbz2-dev \
        libdb-dev \
        libexpat1-dev \
        libffi-dev \
        liblzma-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        locales-all \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sL https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer -o pyenv-installer \
    && export PYENV_ROOT=/pyenv \
    && bash pyenv-installer \
    && /pyenv/bin/pyenv install 2.7.18 \
    && /pyenv/bin/pyenv install 3.5.10 \
    && /pyenv/bin/pyenv install 3.6.15 \
    && /pyenv/bin/pyenv install 3.7.17 \
    && /pyenv/bin/pyenv install 3.8.20 \
    && /pyenv/bin/pyenv install 3.9.25 \
    && /pyenv/bin/pyenv install 3.10.22 \
    && /pyenv/bin/pyenv install 3.11.17 \
    && /pyenv/bin/pyenv install 3.12.15 \
    && /pyenv/bin/pyenv install 3.13.16 \
    && /pyenv/bin/pyenv install 3.14.8 \
    && /pyenv/bin/pyenv install pypy3.9-7.3.11 \
    && /pyenv/bin/pyenv install pypy3.9-7.3.16 \
    && /pyenv/bin/pyenv install pypy3.10-7.3.16

RUN mkdir /pyenv/pybin \
    && cd /pyenv/pybin \
    && ln -s /pyenv/versions/2.7.18/bin/python python2.7 \
    && ln -s /pyenv/versions/3.5.10/bin/python python3.5 \
    && ln -s /pyenv/versions/3.6.15/bin/python python3.6 \
    && ln -s /pyenv/versions/3.7.17/bin/python python3.7 \
    && ln -s /pyenv/versions/3.8.20/bin/python python3.8 \
    && ln -s /pyenv/versions/3.9.25/bin/python python3.9 \
    && ln -s /pyenv/versions/3.10.22/bin/python python3.10 \
    && ln -s /pyenv/versions/3.11.17/bin/python python3.11 \
    && ln -s /pyenv/versions/3.12.15/bin/python python3.12 \
    && ln -s /pyenv/versions/3.13.16/bin/python python3.13 \
    && ln -s /pyenv/versions/3.14.8/bin/python python3.14 \
    && ln -s /pyenv/versions/pypy3.9-7.3.11/bin/python pypy3.9-7.3.11 \
    && ln -s /pyenv/versions/pypy3.9-7.3.16/bin/python pypy3.9-7.3.16 \
    && ln -s /pyenv/versions/pypy3.10-7.3.16/bin/python pypy3.10-7.3.16
