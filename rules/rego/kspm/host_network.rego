# METADATA
# title: Kubernetes Pod uses host network
# description: Pod is configured with hostNetwork=true, sharing the host's network namespace.
# severity: HIGH
# category: kspm
# resource_type: kubernetes::pod
# remediation: Set hostNetwork to false unless absolutely required. Use Kubernetes network policies instead.
# version: 1.0.0

package cloudvisor.kspm.host_network

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    input.resource.raw.spec.hostNetwork == true
    msg := sprintf("Pod '%v' uses host network namespace", [input.resource.name])
}
