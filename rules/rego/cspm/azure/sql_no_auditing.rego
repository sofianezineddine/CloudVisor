# METADATA
# title: Azure SQL Server has no auditing enabled
# description: Azure SQL Server does not have auditing enabled, making it difficult to detect suspicious activity.
# severity: MEDIUM
# category: cspm
# provider: azure
# resource_type: azure::sql::server
# remediation: Enable auditing on the SQL Server in the Azure portal under Security > Auditing.
# compliance:
#   - framework: SOC2
#     control: CC7.2
#   - framework: PCI-DSS
#     control: 10.2
# version: 1.0.0

package cloudvisor.cspm.azure_sql_no_auditing

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::sql::server"
    not input.resource.raw.auditing_enabled
    msg := sprintf("Azure SQL Server '%v' does not have auditing enabled", [input.resource.name])
}
