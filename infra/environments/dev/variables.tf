variable "keycloak_client_id" {
  type        = string
  description = "The Keycloak Client ID"
  default = null
}

variable "keycloak_client_secret" {
  type        = string
  description = "The Keycloak Client Secret"
  sensitive   = true
  default = null
}

variable "keycloak_realm" {
  type = string
}

variable "keycloak_url" {
  type        = string
  description = "The Keycloak base URL"
  default = null
}

variable "frontend_url" {
  type    = string
  default = "http://localhost:5173"
}

variable "admin_email" {
  type = string
}

variable "admin_initial_password" {
  type      = string
  sensitive = true
}