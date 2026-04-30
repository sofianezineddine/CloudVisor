# METADATA
# title: Kubernetes container has no resource limits
# description: Container does not have CPU or memory limits set, risking resource exhaustion (DoS).
# severity: MEDIUM
# category: kspm
# resource_type: kubernetes::pod
# remediation: Set resources.limits.cpu and resources.limits.memory on all containers.
# version: 1.0.0

package cloudvisor.kspm.no_resource_limits

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "kubernetes::pod"
    container := input.resource.raw.spec.containers[_]
    not container.resources.limits
    msg := sprintf("Pod '%v' container '%v' has no resource limits set",
        [input.resource.name, container.name])
}
