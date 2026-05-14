# METADATA
# title: Kubernetes Network Policy Violations
# description: Detects missing or overly permissive network policies that could allow unrestricted pod communication.
# severity: MEDIUM
# category: iac
# resource_type: NetworkPolicy
# version: 1.0.0

package cloudvisor.iac.kubernetes.network_policy

import future.keywords.if
import future.keywords.in
import future.keywords.contains

violation contains finding if {
    input.resource.properties.kind == "NetworkPolicy"
    spec := input.resource.properties.spec
    ingress := spec.ingress[_]
    from_rule := ingress.from[_]
    from_rule.ipBlock.cidr == "0.0.0.0/0"
    not from_rule.ipBlock.except
    finding := {
        "rule_id": "iac.kubernetes.netpol-allow-all-ingress",
        "severity": "HIGH",
        "title": "Network Policy Allows All Ingress Traffic",
        "description": sprintf("NetworkPolicy '%v' allows ingress from 0.0.0.0/0 without exceptions. This effectively allows all external traffic to reach the selected pods.", [input.resource.identifier]),
        "remediation": "Restrict the ipBlock.cidr to specific CIDR ranges or use podSelector/namespaceSelector to limit ingress sources. Add ipBlock.except to exclude untrusted ranges.",
    }
}

violation contains finding if {
    input.resource.properties.kind == "NetworkPolicy"
    spec := input.resource.properties.spec
    egress := spec.egress[_]
    to_rule := egress.to[_]
    to_rule.ipBlock.cidr == "0.0.0.0/0"
    not to_rule.ipBlock.except
    finding := {
        "rule_id": "iac.kubernetes.netpol-allow-all-egress",
        "severity": "MEDIUM",
        "title": "Network Policy Allows All Egress Traffic",
        "description": sprintf("NetworkPolicy '%v' allows egress to 0.0.0.0/0 without exceptions. Pods can communicate with any external endpoint.", [input.resource.identifier]),
        "remediation": "Restrict egress to specific CIDR ranges, namespaces, or pods. Use DNS policies to limit which external services pods can reach.",
    }
}

violation contains finding if {
    input.resource.properties.kind == "NetworkPolicy"
    spec := input.resource.properties.spec
    ingress := spec.ingress[_]
    count(ingress) == 0
    finding := {
        "rule_id": "iac.kubernetes.netpol-empty-ingress-rule",
        "severity": "HIGH",
        "title": "Network Policy Has Empty Ingress Rule (Allows All)",
        "description": sprintf("NetworkPolicy '%v' has an empty ingress rule which allows all ingress traffic. An empty 'from' field means all sources are allowed.", [input.resource.identifier]),
        "remediation": "Add specific 'from' selectors (podSelector, namespaceSelector, or ipBlock) to restrict which sources can send traffic to the selected pods.",
    }
}

violation contains finding if {
    input.resource.properties.kind in {"Deployment", "StatefulSet", "DaemonSet", "Pod"}
    spec := input.resource.properties.spec
    metadata := input.resource.properties.metadata
    not metadata.labels
    finding := {
        "rule_id": "iac.kubernetes.workload-no-labels",
        "severity": "LOW",
        "title": "Workload Missing Labels for Network Policy Selection",
        "description": sprintf("%v '%v' has no labels defined. Network policies use label selectors to target pods; without labels, policies cannot be applied.", [input.resource.properties.kind, input.resource.identifier]),
        "remediation": "Add meaningful labels to the pod metadata (e.g., app, tier, environment) so that NetworkPolicies can select and protect these pods.",
    }
}
