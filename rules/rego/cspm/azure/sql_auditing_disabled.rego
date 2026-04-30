# METADATA
# title: Azure SQL Server auditing not enabled
# description: Azure SQL Server does not have auditing enabled, making it impossible to track database activity.
# severity: HIGH
# category: cspm
# provider: azure
# resource_type: azure::sql::server
# remediation: Enable auditing on the Azure SQL Server in the Azure Portal under Security > Auditing. Configure audit logs to be sent to a storage account, Log Analytics, or Event Hub.
# version: 1.0.0

package cloudvisor.cspm.azure_sql_auditing_disabled

import future.keywords.if

deny[msg] if {
    input.resource.resource_type == "azure::sql::server"
    not input.resource.raw.auditingEnabled
    msg := sprintf("Azure SQL Server '%v' does not have auditing enabled", [input.resource.name])
}
