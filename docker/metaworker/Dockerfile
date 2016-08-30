# Dockerfile customizations for building buildbot's CI test suite.
#
# Provided here as a real life example on how to make a customized
# worker Dockerfile for your project

FROM        tardyp/buildbot-worker
MAINTAINER  Buildbot Maintainers

# Switch to root to be able to install stuff
USER root
# install the DB drivers we need to test against databases, as well as git and nodejs + phantomjs
RUN apt-get update && \
    curl -sL https://deb.nodesource.com/setup_6.x | bash - && \
    apt-get install -y libmysqlclient-dev libpq-dev git  python-virtualenv \
                        enchant libenchant-dev \
                        aspell aspell-en ispell iamerican \
                        fontconfig nodejs postgresql mysql-server && \
    curl -sL https://github.com/paladox/phantomjs/releases/download/2.1.7/phantomjs-2.1.1-linux-x86_64.tar.bz2 | \
    tar  --strip-components=1 -C /usr/local -xj phantomjs-2.1.1-linux-x86_64/bin/phantomjs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN /etc/init.d/mysql start && mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'travis'@'localhost' WITH GRANT OPTION; FLUSH PRIVILEGES;"
COPY pg_hba.conf /etc/postgresql/9.3/main/pg_hba.conf
COPY sudoers /etc/sudoers

# Switch to regular user for security reasons
USER buildbot
