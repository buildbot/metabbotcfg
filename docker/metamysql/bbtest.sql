/* create the bbtest DB with the correct default character set, or the tests will fail */
DROP DATABASE IF EXISTS `bbtest`;
CREATE DATABASE `bbtest` DEFAULT CHARACTER SET utf8;
GRANT ALL ON `bbtest`.* to `bbtest`@`%`;
