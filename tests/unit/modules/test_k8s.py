"""
Unit Tests for the k8s execution module.
"""

import base64
import hashlib
import time
from subprocess import PIPE, Popen

import pytest

import salt.modules.k8s as k8s
import salt.utils.files
import salt.utils.json
from tests.support.unit import TestCase


@pytest.mark.skip_if_binaries_missing("kubectl")
class TestK8SNamespace(TestCase):

    maxDiff = None

    def test_get_namespaces(self):
        res = k8s.get_namespaces(apiserver_url="http://127.0.0.1:8080")
        a = len(res.get("items"))
        proc = Popen(["kubectl", "get", "namespaces", "-o", "json"], stdout=PIPE)
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = len(kubectl_out.get("items"))
        self.assertEqual(a, b)

    def test_get_one_namespace(self):
        res = k8s.get_namespaces("default", apiserver_url="http://127.0.0.1:8080")
        a = res.get("metadata", {}).get("name", "a")
        proc = Popen(
            ["kubectl", "get", "namespaces", "default", "-o", "json"], stdout=PIPE
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = kubectl_out.get("metadata", {}).get("name", "b")
        self.assertEqual(a, b)

    def test_create_namespace(self):
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        nsname = hash.hexdigest()[:16]
        res = k8s.create_namespace(nsname, apiserver_url="http://127.0.0.1:8080")
        proc = Popen(
            ["kubectl", "get", "namespaces", nsname, "-o", "json"], stdout=PIPE
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        # if creation is failed, kubernetes return non json error message
        self.assertTrue(isinstance(kubectl_out, dict))


@pytest.mark.skip_if_binaries_missing("kubectl")
class TestK8SSecrets(TestCase):

    maxDiff = None

    def setUp(self):
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.name = hash.hexdigest()[:16]
        data = {"testsecret": base64.encodestring("teststring")}
        self.request = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": self.name, "namespace": "default"},
            "data": data,
        }

    def test_get_secrets(self):
        res = k8s.get_secrets("default", apiserver_url="http://127.0.0.1:8080")
        a = len(res.get("items", []))
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "secrets", "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = len(kubectl_out.get("items", []))
        self.assertEqual(a, b)

    def test_get_one_secret(self):
        name = self.name
        filename = f"/tmp/{name}.json"
        with salt.utils.files.fopen(filename, "w") as f:
            salt.utils.json.dump(self.request, f)

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.1)
        res = k8s.get_secrets("default", name, apiserver_url="http://127.0.0.1:8080")
        a = res.get("metadata", {}).get("name", "a")
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "secrets", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = kubectl_out.get("metadata", {}).get("name", "b")
        self.assertEqual(a, b)

    def test_get_decoded_secret(self):
        name = self.name
        filename = f"/tmp/{name}.json"
        with salt.utils.files.fopen(filename, "w") as f:
            salt.utils.json.dump(self.request, f)

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give etcd to populate data on all nodes
        time.sleep(0.1)
        res = k8s.get_secrets(
            "default", name, apiserver_url="http://127.0.0.1:8080", decode=True
        )
        a = res.get("data", {}).get(
            "testsecret",
        )
        self.assertEqual(a, "teststring")

    def test_create_secret(self):
        name = self.name
        names = []
        expected_data = {}
        for i in range(2):
            names.append(f"/tmp/{name}-{i}")
            with salt.utils.files.fopen(f"/tmp/{name}-{i}", "w") as f:
                expected_data[f"{name}-{i}"] = base64.b64encode(f"{name}{i}")
                f.write(salt.utils.stringutils.to_str(f"{name}{i}"))
        res = k8s.create_secret(
            "default", name, names, apiserver_url="http://127.0.0.1:8080"
        )
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "secrets", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        # if creation is failed, kubernetes return non json error message
        b = kubectl_out.get("data", {})
        self.assertTrue(isinstance(kubectl_out, dict))
        self.assertEqual(expected_data, b)

    def test_update_secret(self):
        name = self.name
        filename = f"/tmp/{name}.json"
        with salt.utils.files.fopen(filename, "w") as f:
            salt.utils.json.dump(self.request, f)

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.1)
        expected_data = {}
        names = []
        for i in range(3):
            names.append(f"/tmp/{name}-{i}-updated")
            with salt.utils.files.fopen(f"/tmp/{name}-{i}-updated", "w") as f:
                expected_data[f"{name}-{i}-updated"] = base64.b64encode(
                    f"{name}{i}-updated"
                )
                f.write(f"{name}{i}-updated")

        res = k8s.update_secret(
            "default", name, names, apiserver_url="http://127.0.0.1:8080"
        )
        # if creation is failed, kubernetes return non json error message
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "secrets", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        # if creation is failed, kubernetes return non json error message
        b = kubectl_out.get("data", {})
        self.assertTrue(isinstance(kubectl_out, dict))
        self.assertEqual(expected_data, b)

    def test_delete_secret(self):
        name = self.name
        filename = f"/tmp/{name}.json"
        with salt.utils.files.fopen(filename, "w") as f:
            salt.utils.json.dump(self.request, f)

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.1)
        res = k8s.delete_secret("default", name, apiserver_url="http://127.0.0.1:8080")
        time.sleep(0.1)
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "secrets", name, "-o", "json"],
            stdout=PIPE,
            stderr=PIPE,
        )
        kubectl_out, err = proc.communicate()
        # stdout is empty, stderr is showing something like "not found"
        self.assertEqual("", kubectl_out)
        self.assertEqual(f'Error from server: secrets "{name}" not found\n', err)


@pytest.mark.skip_if_binaries_missing("kubectl")
class TestK8SResourceQuotas(TestCase):

    maxDiff = None

    def setUp(self):
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.name = hash.hexdigest()[:16]

    def test_get_resource_quotas(self):
        name = self.name
        namespace = self.name
        create_namespace = Popen(
            ["kubectl", "create", "namespace", namespace], stdout=PIPE
        )
        create_namespace = Popen(
            ["kubectl", "create", "namespace", namespace], stdout=PIPE
        )
        request = """
apiVersion: v1
kind: ResourceQuota
metadata:
  name: {}
spec:
  hard:
    cpu: "20"
    memory: 1Gi
    persistentvolumeclaims: "10"
    pods: "10"
    replicationcontrollers: "20"
    resourcequotas: "1"
    secrets: "10"
    services: "5"
""".format(
            name
        )
        filename = f"/tmp/{name}.yaml"
        with salt.utils.files.fopen(filename, "w") as f:
            f.write(salt.utils.stringutils.to_str(request))

        create = Popen(
            ["kubectl", f"--namespace={namespace}", "create", "-f", filename],
            stdout=PIPE,
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.2)
        res = k8s.get_resource_quotas(namespace, apiserver_url="http://127.0.0.1:8080")
        a = len(res.get("items", []))
        proc = Popen(
            [
                "kubectl",
                f"--namespace={namespace}",
                "get",
                "quota",
                "-o",
                "json",
            ],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = len(kubectl_out.get("items", []))
        self.assertEqual(a, b)

    def test_get_one_resource_quota(self):
        name = self.name
        namespace = self.name
        create_namespace = Popen(
            ["kubectl", "create", "namespace", namespace], stdout=PIPE
        )
        request = """
apiVersion: v1
kind: ResourceQuota
metadata:
  name: {}
spec:
  hard:
    cpu: "20"
    memory: 1Gi
    persistentvolumeclaims: "10"
    pods: "10"
    replicationcontrollers: "20"
    resourcequotas: "1"
    secrets: "10"
    services: "5"
""".format(
            name
        )
        filename = f"/tmp/{name}.yaml"
        with salt.utils.files.fopen(filename, "w") as f:
            f.write(salt.utils.stringutils.to_str(request))

        create = Popen(
            ["kubectl", f"--namespace={namespace}", "create", "-f", filename],
            stdout=PIPE,
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.2)
        res = k8s.get_resource_quotas(
            namespace, name, apiserver_url="http://127.0.0.1:8080"
        )
        a = res.get("metadata", {}).get("name", "a")
        proc = Popen(
            [
                "kubectl",
                f"--namespace={namespace}",
                "get",
                "quota",
                name,
                "-o",
                "json",
            ],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = kubectl_out.get("metadata", {}).get("name", "b")
        self.assertEqual(a, b)

    def test_create_resource_quota(self):
        name = self.name
        namespace = self.name
        create_namespace = Popen(
            ["kubectl", "create", "namespace", namespace], stdout=PIPE
        )
        quota = {"cpu": "20", "memory": "1Gi"}
        res = k8s.create_resource_quota(
            namespace, quota, name=name, apiserver_url="http://127.0.0.1:8080"
        )
        proc = Popen(
            [
                "kubectl",
                f"--namespace={namespace}",
                "get",
                "quota",
                name,
                "-o",
                "json",
            ],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        self.assertTrue(isinstance(kubectl_out, dict))

    def test_update_resource_quota(self):
        name = self.name
        namespace = self.name
        create_namespace = Popen(
            ["kubectl", "create", "namespace", namespace], stdout=PIPE
        )
        request = """
apiVersion: v1
kind: ResourceQuota
metadata:
  name: {}
spec:
  hard:
    cpu: "20"
    memory: 1Gi
    persistentvolumeclaims: "10"
    pods: "10"
    replicationcontrollers: "20"
    resourcequotas: "1"
    secrets: "10"
    services: "5"
""".format(
            name
        )
        filename = f"/tmp/{name}.yaml"
        with salt.utils.files.fopen(filename, "w") as f:
            f.write(salt.utils.stringutils.to_str(request))

        create = Popen(
            ["kubectl", f"--namespace={namespace}", "create", "-f", filename],
            stdout=PIPE,
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.2)
        quota = {"cpu": "10", "memory": "2Gi"}
        res = k8s.create_resource_quota(
            namespace,
            quota,
            name=name,
            apiserver_url="http://127.0.0.1:8080",
            update=True,
        )
        proc = Popen(
            [
                "kubectl",
                f"--namespace={namespace}",
                "get",
                "quota",
                name,
                "-o",
                "json",
            ],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        limit = kubectl_out.get("spec").get("hard").get("memory")
        self.assertEqual("2Gi", limit)


@pytest.mark.skip_if_binaries_missing("kubectl")
class TestK8SLimitRange(TestCase):

    maxDiff = None

    def setUp(self):
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.name = hash.hexdigest()[:16]

    def test_create_limit_range(self):
        name = self.name
        limits = {"Container": {"defaultRequest": {"cpu": "100m"}}}
        res = k8s.create_limit_range(
            "default", limits, name=name, apiserver_url="http://127.0.0.1:8080"
        )
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "limits", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        self.assertTrue(isinstance(kubectl_out, dict))

    def test_update_limit_range(self):
        name = self.name
        request = """
apiVersion: v1
kind: LimitRange
metadata:
  name: {}
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
""".format(
            name
        )
        limits = {"Container": {"defaultRequest": {"cpu": "100m"}}}
        filename = f"/tmp/{name}.yaml"
        with salt.utils.files.fopen(filename, "w") as f:
            f.write(salt.utils.stringutils.to_str(request))

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.1)
        res = k8s.create_limit_range(
            "default",
            limits,
            name=name,
            apiserver_url="http://127.0.0.1:8080",
            update=True,
        )
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "limits", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        limit = (
            kubectl_out.get("spec").get("limits")[0].get("defaultRequest").get("cpu")
        )
        self.assertEqual("100m", limit)

    def test_get_limit_ranges(self):
        res = k8s.get_limit_ranges("default", apiserver_url="http://127.0.0.1:8080")
        a = len(res.get("items", []))
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "limits", "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = len(kubectl_out.get("items", []))
        self.assertEqual(a, b)

    def test_get_one_limit_range(self):
        name = self.name
        request = """
apiVersion: v1
kind: LimitRange
metadata:
  name: {}
spec:
  limits:
  - default:
      cpu: 200m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
""".format(
            name
        )
        filename = f"/tmp/{name}.yaml"
        with salt.utils.files.fopen(filename, "w") as f:
            f.write(salt.utils.stringutils.to_str(request))

        create = Popen(
            ["kubectl", "--namespace=default", "create", "-f", filename], stdout=PIPE
        )
        # wee need to give kubernetes time save data in etcd
        time.sleep(0.1)
        res = k8s.get_limit_ranges(
            "default", name, apiserver_url="http://127.0.0.1:8080"
        )
        a = res.get("metadata", {}).get("name", "a")
        proc = Popen(
            ["kubectl", "--namespace=default", "get", "limits", name, "-o", "json"],
            stdout=PIPE,
        )
        kubectl_out = salt.utils.json.loads(proc.communicate()[0])
        b = kubectl_out.get("metadata", {}).get("name", "b")
        self.assertEqual(a, b)
