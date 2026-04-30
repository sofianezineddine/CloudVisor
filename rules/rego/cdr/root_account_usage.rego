# METADATA
# title: AWS root account API usage detected
# description: The AWS root account was used to make an API call. Root account usage should be avoided.
# severity: CRITICAL
# category: cdr
# provider: aws
# resource_type: aws::cloudtrail::event
# remediation: Disable root account access keys. Use IAM users/roles for all API access.
# version: 1.0.0

package cloudvisor.cdr.root_account_usage

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "aws::cloudtrail::event"
    input.resource.raw.userIdentity.type == "Root"
    input.resource.raw.eventName != "ConsoleLogin"
    msg := sprintf("Root account used for API call: %v from IP %v",
        [input.resource.raw.eventName, input.resource.raw.sourceIPAddress])
}
