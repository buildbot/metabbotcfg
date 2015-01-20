"""
Debian-related components for metabuildbot.
"""
debian_buildbot_git_repo = 'git://github.com/buildbot/debian-buildbot.git'
debian_buildbot_slave_git_repo = 'git://github.com/buildbot/debian-buildbot-slave.git'

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.triggerable import Triggerable

from metabbotcfg.common import GIT_URL

masterTarballScheduler = SingleBranchScheduler(
    name="tarball-master",
    branch="master",
    treeStableTimer=10,
    properties={
        "component": "master"
    },
    builderNames=["tarball-master"])
masterDebScheduler = Triggerable(
    name="deb-master",
    properties={
        "debian-repo": debian_buildbot_git_repo
    },
    builderNames=["deb-master"])
slaveTarballScheduler = SingleBranchScheduler(
    name="tarball-slave",
    branch="master",
    treeStableTimer=10,
    properties={
        "component": "slave"
    },
    builderNames=["tarball-slave"])
slaveDebScheduler = Triggerable(
    name="deb-slave",
    properties={
        "debian-repo": debian_buildbot_slave_git_repo
    },
    builderNames=["deb-slave"])

schedulers = [
    masterTarballScheduler,
    masterDebScheduler,
    slaveTarballScheduler,
    slaveDebScheduler
]

from buildbot.process.factory import BuildFactory
from buildbot.steps.source.git import Git
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import SetPropertyFromCommand
from buildbot.process.properties import WithProperties, Property
from buildbot.steps.trigger import Trigger

from buildbot.steps.transfer import FileDownload, FileUpload

relative_dist_dir = "%(component)s/dist"
remove_old_tarballs = ShellCommand(
    command=["find", ".", "-delete"],
    workdir=WithProperties("build/" + relative_dist_dir))

buildbot_checkout = Git(repourl=GIT_URL)
create_tarball = ShellCommand(
    command=["python", "setup.py", "sdist"],
    workdir=WithProperties("build/%(component)s"))

def tarball_property(rc, stdout, stderr):
    import re
    version_re = re.compile(r'buildbot(-slave)?-(.*)\.(tar|zip).*')
    tarballs = [x.strip() for x in stdout.split()]
    versions = [version_re.match(x).group(2) for x in tarballs]
    return {
        "tarball": tarballs[0],
        "tarball_version":versions[0]
    }

mk_tarball_property = SetPropertyFromCommand(
    command=["ls", "--color=never", WithProperties(relative_dist_dir)],
    extract_fn=tarball_property)

upload_tarball = FileUpload(
    slavesrc=WithProperties(relative_dist_dir + "/%(tarball)s"),
    masterdest=WithProperties("public_html/%(component)s/%(tarball)s"))

trigger_deb_build = Trigger(
    schedulerNames=[WithProperties("deb-%(component)s")],
    waitForFinish=False,
    alwaysUseLatest=True,
    set_properties={
        'branch': ["master", "upstream"]
    },
    copy_properties=['tarball', 'tarball_version', 'component'])

tarball_factory = BuildFactory([
    remove_old_tarballs,
    buildbot_checkout,
    create_tarball,
    mk_tarball_property,
    upload_tarball,
    trigger_deb_build
])

rm_rf = ShellCommand(
    command=["find", ".", "-delete"],
    workdir=Property('workdir'))
debian_checkout = ShellCommand(
    command=["git", "clone", Property("debian-repo"), "-b" "unreleased", "."])
fetch_upstream_branch = ShellCommand(
    command=["git", "branch", "upstream", "origin/upstream"],
    warnOnFailure=True)
download_tarball = FileDownload(
    mastersrc=WithProperties("public_html/%(component)s/%(tarball)s"),
    slavedest=WithProperties("%(workdir)s/%(tarball)s"))
import_orig = ShellCommand(
    command=[
        "git-import-orig",
        WithProperties("--upstream-version=%(tarball_version)s"),
        WithProperties("%(workdir)s/%(tarball)s")
    ])
update_changelog = ShellCommand(
    command=["git-dch", "--auto", "--snapshot"],
    env={"EDITOR":"/bin/true"})
build_deb_package = ShellCommand(
    command=["git-buildpackage", "--git-ignore-new", "-us", "-uc"])

deb_factory = BuildFactory([
    rm_rf,
    debian_checkout,
    fetch_upstream_branch,
    download_tarball,
    import_orig,
    update_changelog,
    build_deb_package
])

builders = [
    dict(name="tarball-master",
         slavenames=["buildbot.net"],
         factory=tarball_factory,
         category='debian'),
    dict(name="tarball-slave",
         slavenames=["buildbot.net"],
         factory=tarball_factory,
         category='debian'),
    dict(name="deb-master",
         slavenames=["debian"],
         factory=deb_factory,
         category='debian'),
    dict(name="deb-slave",
         slavenames=["debian"],
         factory=deb_factory,
         category='debian')
]
