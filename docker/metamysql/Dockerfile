FROM mysql/mysql-server:5.6
MAINTAINER Buildbot Maintainers

# Add an extra setup script
ADD bbtest.sql /docker-entrypoint-initdb.d/bbtest.sql
