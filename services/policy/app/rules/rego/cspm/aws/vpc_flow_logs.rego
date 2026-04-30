# METADATA
# title: "VPC Flow Logs Not Enabled"
# description: "VPC does not have flow logs enabled for network monitoring"
# severity: MEDIUM
# category: cspm
# provider: aws
# resource_type: aws::ec2::vpc
# compliance:
#   - framework: CIS-AWS
#     control: "3.9"
#   - framework: SOC2
#     control: "CC6.1"
#   - framework: NIST-800-53
#     control: "AU-2"
# remediation: "Enable VPC Flow Logs: AWS Console > VPC > Your VPCs > VPC > Flow logs > Create flow log"

package cloudvisor.cspm.aws.vpc_flow_logs

import future.keywords

deny[finding] {
    input.resource_type == "aws::ec2::vpc"
    
    # Check if VPC has flow logs enabled
    # This assumes the connector includes flow log information in the VPC resource
    flow_logs := input.raw.FlowLogs
    
    # No flow logs configured
    not flow_logs
    
    finding := {
        "rule_id": "aws-vpc-flow-logs-disabled",
        "title": "VPC flow logs are not enabled",
        "description": sprintf("VPC '%s' does not have flow logs enabled for network traffic monitoring", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Enable VPC flow logs to monitor network traffic and detect suspicious activity",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "3.9"},
            {"framework": "SOC2", "control": "CC6.1"},
            {"framework": "NIST-800-53", "control": "AU-2"}
        ]
    }
}

deny[finding] {
    input.resource_type == "aws::ec2::vpc"
    
    # Check if flow logs exist but are not active
    flow_logs := input.raw.FlowLogs
    flow_logs
    count(flow_logs) > 0
    
    # Check if any flow log is active
    active_logs := [log | log := flow_logs[_]; log.FlowLogStatus == "ACTIVE"]
    count(active_logs) == 0
    
    finding := {
        "rule_id": "aws-vpc-flow-logs-inactive",
        "title": "VPC flow logs are not active",
        "description": sprintf("VPC '%s' has flow logs configured but none are active", [input.name]),
        "severity": "MEDIUM",
        "remediation": "Ensure VPC flow logs are active and properly configured",
        "compliance_mapping": [
            {"framework": "CIS-AWS", "control": "3.9"},
            {"framework": "SOC2", "control": "CC6.1"}
        ]
    }
}