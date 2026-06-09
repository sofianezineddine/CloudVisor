# METADATA
# title: Kubernetes Pod runs as root
# description: Pod or container is configured to run as root user (UID 0), violating least privilege.
# severity: HIGH
# category: kspm
# resource_type: kubernetes::pod
# remediation: Set securityContext.runAsNonRoot=true and securityContext.runAsUser to a non-zero UID.
# version: 1.0.0

package cloudvisor.kspm.pod_security

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    container := input.resource.raw.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := sprintf("Pod '%v' container '%v' runs as root (UID 0)", [input.resource.name, container.name])
}

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    container := input.resource.raw.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("Pod '%v' container '%v' runs in privileged mode", [input.resource.name, container.name])
}
