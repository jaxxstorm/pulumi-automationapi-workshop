"""A Python Pulumi program"""

import pulumi
import pulumi_digitalocean as do
import pulumi_kubernetes as k8s

import clusterissuers.pulumi_crds as clusterissuers
import certificates.pulumi_crds as certs

do_config = pulumi.Config("digitalocean")
token = do_config.get_secret("token")

# Get the workshop project
workshop = do.get_project(name="Workshops")

workshop_domain = "pulumi-workshop.net"

# Create a DNS domain
dns_domain = do.Domain("workshop-domain", name=workshop_domain)


# grab the latest version available from DigitalOcean
ver = do.get_kubernetes_versions()

# provision a Kubernetes cluster
cluster = do.KubernetesCluster(
    "workshop-cluster",
    region="nyc3",
    version=ver.latest_version,
    node_pool=do.KubernetesClusterNodePoolArgs(
        name="default", size="s-1vcpu-2gb", node_count=3
    ),
)

# Set up a Kubernetes provider
k8s_provider = k8s.Provider(
    "do-k8s",
    kubeconfig=cluster.kube_configs.apply(lambda c: c[0].raw_config),
    opts=pulumi.ResourceOptions(parent=cluster),
)

ns = k8s.core.v1.Namespace(
    "platform",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="platform"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, parent=k8s_provider),
)

external_dns = k8s.helm.v3.Chart(
    "external-dns",
    k8s.helm.v3.ChartOpts(
        chart="external-dns",
        namespace=ns.metadata.name,
        fetch_opts=k8s.helm.v3.FetchOpts(repo="https://charts.bitnami.com/bitnami"),
        values={
            "provider": "digitalocean",
            "domainFilters": [workshop_domain],
            "digitalocean": {"apiToken": token},
        },
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, parent=ns),
)

nginx_ingress = k8s.helm.v3.Chart(
    "nginx-ingress",
    k8s.helm.v3.ChartOpts(
        namespace=ns.metadata.name,
        chart="ingress-nginx",
        version="3.26.0",
        fetch_opts=k8s.helm.v3.FetchOpts(
            repo="https://kubernetes.github.io/ingress-nginx"
        ),
        values={
            "controller": {
                "publishService": {
                    "enabled": "true"
                }
            }
        }
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, parent=ns),
)

pulumi.export("kubeconfig", cluster.kube_configs[0].raw_config)
