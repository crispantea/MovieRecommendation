output "issuer" {
  description = "Use as the expected `iss` in your backend token verification"
  value       = "${var.keycloak_url}/realms/${keycloak_realm.agi_project.realm}"
}