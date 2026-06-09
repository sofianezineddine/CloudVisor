# METADATA
# title: Kubernetes container runs in privileged mode
# description: Container has privileged=true in its security context, granting it full host access.
# severity: CRITICAL
# category: kspm
# resource_type: kubernetes::pod
# remediation: Remove privileged:true from the container securityContext. Use specific capabilities instead.
# version: 1.0.0

package cloudvisor.kspm.privileged_container

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    container := input.resource.raw.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("Pod '%v' container '%v' runs in privileged mode",
        [input.resource.name, container.name])
}

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    container := input.resource.raw.spec.initContainers[_]
    container.securityContext.privileged == true
    msg := sprintf("Pod '%v' init container '%v' runs in privileged mode",
        [input.resource.name, container.name])
}
