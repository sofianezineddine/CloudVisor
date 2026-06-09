# METADATA
# title: Secrets detected in CI/CD environment variables
# description: CI/CD pipeline configuration contains environment variables that appear to be secrets.
# severity: CRITICAL
# category: cicd
# resource_type: cicd::pipeline
# remediation: Move secrets to a secrets manager (AWS Secrets Manager, HashiCorp Vault). Never hardcode secrets.
# version: 1.0.0

package cloudvisor.cicd.secrets_in_env

# Common secret patterns in env var names
secret_patterns := {
    "password", "passwd", "secret", "api_key", "apikey",
    "token", "private_key", "access_key", "secret_key",
    "credentials", "auth_token", "bearer_token",
}

deny[msg] if {
    input.resource.resource_type == "cicd::pipeline"
    env_var := input.resource.raw.env[_]
    lower_name := lower(env_var.name)
    pattern := secret_patterns[_]
    contains(lower_name, pattern)
    not startswith(env_var.value, "${{")  # Not a reference to a secret store
    not startswith(env_var.value, "$(")   # Not a variable reference
    msg := sprintf("CI/CD pipeline '%v' has potential secret in env var: %v",
        [input.resource.name, env_var.name])
}
