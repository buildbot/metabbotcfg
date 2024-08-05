import os
import random
import string

from buildbot.plugins import util
from buildbot.plugins import worker


class MyWorkerBase:
    # operating system, for os-specific builders; this should only be used
    # for fleets of machines that are basically interchangebale
    os = None

    def extract_attrs(self, name, **kwargs):
        self.name = name
        remaining = {}
        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])
            else:
                remaining[k] = kwargs[k]
        return remaining

    def get_random_pass(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

    def get_pass(self, name):
        # get the password based on the name
        file_name = name
        if name.startswith("p12-pd"):
            file_name = "p12-pd-any"
        if name.startswith("p12-ep2"):
            file_name = "p12-ep2-any"

        path = os.path.join(os.path.dirname(__file__), f"{file_name}.pass")
        if not os.path.exists(path):
            print("warning {} does not exit. creating one".format(path))
            pw = self.get_random_pass()
            with open(path, 'w') as f:
                f.write(pw)

        pw = open(path).read().strip()
        return pw

    def get_ec2_creds(self, name):
        path = os.path.join(os.path.dirname(__file__), "%s.ec2" % name)
        return open(path).read().strip().split(" ")


class MyWorker(MyWorkerBase, worker.Worker):
    def __init__(self, name, **kwargs):
        password = self.get_pass(name)
        kwargs = self.extract_attrs(name, **kwargs)
        worker.Worker.__init__(self, name, password, **kwargs)


class MyLocalWorker(MyWorkerBase, worker.LocalWorker):
    def __init__(self, name, **kwargs):
        kwargs = self.extract_attrs(name, **kwargs)
        return worker.LocalWorker.__init__(self, name, **kwargs)


# has to be the same for all workers
kube_config = util.KubeCtlProxyConfigLoader()


class MyKubeWorker(MyWorkerBase, worker.KubeLatentWorker):
    def getBuildContainerResources(self, build):
        cpu = str(build.getProperty("NUM_CPU", "1"))
        mem = str(build.getProperty("MEMORY_SIZE", "1G"))

        return {"requests": {"cpu": cpu, "memory": mem}}

    def get_build_container_volume_mounts(self, build):
        return [
            {
                "name": "scratch-volume",
                "mountPath": "/scratch",
            }
        ]

    def get_volumes(self, build):
        return [
            {
                "name": "scratch-volume",
                "emptyDir": {
                    "sizeLimit": "500Mi",
                },
            }
        ]

    def get_node_selector(self, props):
        return {"bb-pool-type": "work"}

    def __init__(self, name, **kwargs):
        kwargs = self.extract_attrs(name, **kwargs)

        return worker.KubeLatentWorker.__init__(
            self,
            name,
            kube_config=kube_config,
            image=util.Interpolate(
                "%(prop:DOCKER_IMAGE:-us-west1-docker.pkg.dev/metabuildbot-227920/metabuildbot-worker/worker)s"
            ),
            masterFQDN="buildbot.buildbot.net",
            **kwargs,
        )


workers = (
    [
        # add 40 kube workers
        MyKubeWorker(f"kube{i:02d}", max_builds=1, build_wait_timeout=0)
        for i in range(40)
    ]
    + [
        # add 4 local workers
        MyLocalWorker('local{:01d}'.format(i), max_builds=1)
        for i in range(5)
    ]
    + [MyWorker(f"p12-pd-{i}", max_builds=1) for i in range(40)]
    + [MyWorker(f"p12-ep2-{i}", max_builds=1) for i in range(80)]
)
