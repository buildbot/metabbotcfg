import shutil

from subprocess import call, check_call

from twisted.trial import unittest
from twisted.python import util

from metabbotcfg.virtualenvsetup import VirtualenvSetup

class VirtualEnv(unittest.SynchronousTestCase):
    def test_virtualenv_command(self):
        shutil.copyfile(util.sibpath(__file__, "virtualenv.whl"), "virtualenv.whl")
        c = VirtualenvSetup(virtualenv_packages=["dictns"])
        command = c.buildCommand()
        call(command, shell=True)
        call(command, shell=True)
        self.assertFalse(check_call([c.virtualenv_dir + "/bin/python", '-c', 'import math']))
