import logging
import kopf
import kr8s

Hellos = kr8s.objects.new_class("hellos.testdevops.com", "v1", namespaced=True)

@kopf.on.create("hellos")  # type: ignore
def create_chain(body, **kwargs):
    hello = Hellos(body)
    name = hello.metadata["name"]
    namespace = hello.metadata.get("namespace", "default")
    text = hello.spec["text"]
    container_port = int(hello.spec["container_port"])
    service_type = hello.spec["service_type"]
    service_port = int(hello.spec["service_port"])

    # --- Pod (add ownerRef BEFORE create) ---
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"{name}-pod",
            "namespace": namespace,
            "labels": {"app": f"{name}-pod"},
        },
        "spec": {
            "containers": [
                {
                    "name": "http-echo",
                    "image": "hashicorp/http-echo",
                    "args": [f"-text={text}", f"-listen=:{container_port}"],
                    "ports": [{"containerPort": container_port}],
                }
            ],
        },
    }
    kopf.adopt(pod_manifest)  # <-- ensure GC works
    pod = kr8s.objects.Pod(pod_manifest)
    pod.create()
    logging.info(f"*** Hello pod {name}-pod created on :{container_port}")

    # --- Service (add ownerRef BEFORE create) ---
    svc_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"{name}-svc",
            "namespace": namespace,
        },
        "spec": {
            "type": service_type,
            "selector": {"app": f"{name}-pod"},
            "ports": [{
                "name": "http",
                "port": service_port,
                "targetPort": container_port,
            }],
        },
    }
    kopf.adopt(svc_manifest)  # <-- ensure GC works
    svc = kr8s.objects.Service(svc_manifest)
    svc.create()
    logging.info(f"*** Service {name}-svc created on :{service_port} -> targetPort {container_port}")
