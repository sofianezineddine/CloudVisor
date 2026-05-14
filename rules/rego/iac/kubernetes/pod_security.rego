# METADATA
# title: Kubernetes Pod Security Violations
# description: Detects insecure pod configurations including privileged containers, root execution, and missing security contexts.
# severity: HIGH
# category: iac
# resource_type: Pod, Deployment, StatefulSet, DaemonSet
# version: 1.0.0

package cloudvisor.iac.kubernetes.pod_security

import future.keywords.if
import future.keywords.in
import future.keywords.contains

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    container := spec.containers[_]
    container.securityContext.privileged == true
    finding := {
        "rule_id": "iac.kubernetes.privileged-container",
        "severity": "CRITICAL",
        "title": "Container Runs in Privileged Mode",
        "description": sprintf("Container '%v' in %v '%v' runs in privileged mode. Privileged containers have full access to the host and can escape container isolation.", [container.name, input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set securityContext.privileged to false. If elevated privileges are needed, use specific Linux capabilities instead of full privileged mode.",
    }
}

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    container := spec.containers[_]
    container.securityContext.runAsUser == 0
    finding := {
        "rule_id": "iac.kubernetes.run-as-root",
        "severity": "HIGH",
        "title": "Container Runs as Root User",
        "description": sprintf("Container '%v' in %v '%v' runs as root (UID 0). Running as root increases the impact of container escape vulnerabilities.", [container.name, input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set securityContext.runAsNonRoot to true and securityContext.runAsUser to a non-zero UID (e.g., 1000).",
    }
}

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    not spec.securityContext.runAsNonRoot
    container := spec.containers[_]
    not container.securityContext.runAsNonRoot
    not container.securityContext.runAsUser
    finding := {
        "rule_id": "iac.kubernetes.no-run-as-non-root",
        "severity": "MEDIUM",
        "title": "Container Does Not Enforce Non-Root Execution",
        "description": sprintf("Container '%v' in %v '%v' does not set runAsNonRoot. The container may run as root by default.", [container.name, input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set securityContext.runAsNonRoot to true at the pod or container level to prevent root execution.",
    }
}

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    container := spec.containers[_]
    not container.securityContext.readOnlyRootFilesystem
    finding := {
        "rule_id": "iac.kubernetes.writable-root-filesystem",
        "severity": "MEDIUM",
        "title": "Container Has Writable Root Filesystem",
        "description": sprintf("Container '%v' in %v '%v' does not set readOnlyRootFilesystem. A writable filesystem allows attackers to modify binaries or plant malware.", [container.name, input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set securityContext.readOnlyRootFilesystem to true. Use emptyDir volumes for directories that need write access.",
    }
}

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    container := spec.containers[_]
    container.securityContext.allowPrivilegeEscalation == true
    finding := {
        "rule_id": "iac.kubernetes.allow-privilege-escalation",
        "severity": "HIGH",
        "title": "Container Allows Privilege Escalation",
        "description": sprintf("Container '%v' in %v '%v' allows privilege escalation. A process could gain more privileges than its parent.", [container.name, input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set securityContext.allowPrivilegeEscalation to false to prevent child processes from gaining additional privileges.",
    }
}

violation contains finding if {
    _is_workload_resource
    spec := _pod_spec
    spec.hostNetwork == true
    finding := {
        "rule_id": "iac.kubernetes.host-network",
        "severity": "HIGH",
        "title": "Pod Uses Host Network Namespace",
        "description": sprintf("%v '%v' uses the host network namespace. This allows the pod to access all network interfaces on the host.", [input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Set spec.hostNetwork to false unless absolutely required. Use NetworkPolicies to control pod-to-pod communication instead.",
    }
}

# Helper rules

_is_workload_resource if {
    input.resource.properties.kind in {"Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob"}
}

_pod_spec := input.resource.properties.spec if {
    input.resource.properties.kind == "Pod"
}

_pod_spec := input.resource.properties.spec.template.spec if {
    input.resource.properties.kind in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"}
}

_pod_spec := input.resource.properties.spec.jobTemplate.spec.template.spec if {
    input.resource.properties.kind == "CronJob"
}
