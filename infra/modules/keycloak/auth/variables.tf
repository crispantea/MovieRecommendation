variable "keycloak_url" {
  type = string
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