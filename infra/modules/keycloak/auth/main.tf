resource "keycloak_realm" "agi_project" {
  realm   = "agi-project"
  enabled = true

  # Sign-up and login
  registration_allowed           = true
  registration_email_as_username = true
  login_with_email_allowed       = true
  reset_password_allowed         = true
  verify_email                   = false # set to true once an smtp_server is configured
  ssl_required                   = "external" # TODO: Check this

  password_policy = "notUsername"

  # Token lifetimes
  access_token_lifespan    = "5m"
  sso_session_idle_timeout = "30m"
  sso_session_max_lifespan = "10h"

  security_defenses {
    brute_force_detection {
      permanent_lockout  = false
      max_login_failures = 5
    }
  }
}

resource "keycloak_role" "user" {
  realm_id    = keycloak_realm.agi_project.id
  name        = "user"
  description = "Standard user"
}

resource "keycloak_role" "admin" {
  realm_id        = keycloak_realm.agi_project.id
  name            = "admin"
  description     = "Application admin"
  composite_roles = [keycloak_role.user.id] # Includes everything a user can do
}


# Every newly registered user gets "user" automatically.
resource "keycloak_default_roles" "this" {
  realm_id = keycloak_realm.agi_project.id
  default_roles = [
    keycloak_role.user.name,
    "account/manage-account", # lets users change their own password/profile (client/role syntax)
  ]
}

resource "keycloak_openid_client" "agi_web" {
  realm_id  = keycloak_realm.agi_project.id
  client_id = "agi-web"
  name      = "AGI web app"
  enabled   = true

  access_type                  = "PUBLIC"
  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = false
  service_accounts_enabled     = false
  pkce_code_challenge_method   = "S256"

  root_url                        = var.frontend_url
  valid_redirect_uris             = ["${var.frontend_url}/*"] # path wildcard on our own origin only
  valid_post_logout_redirect_uris = ["${var.frontend_url}/*"]
  web_origins                     = [var.frontend_url]

  # Only roles explicitly mapped below will appear in this client's tokens
  full_scope_allowed = false
}

# Allow the client to expose these realm roles in its tokens.
# Without this, full_scope_allowed = false means no roles in the token.
resource "keycloak_generic_role_mapper" "web_roles" {
  for_each = {
    user  = keycloak_role.user.id
    admin = keycloak_role.admin.id
  }

  realm_id  = keycloak_realm.agi_project.id
  client_id = keycloak_openid_client.agi_web.id
  role_id   = each.value
}

# Audience: each service checks that its own name is in `aud`
resource "keycloak_openid_audience_protocol_mapper" "audiences" {
  # TODO: If more services will read the users token, add it here!
  for_each = toset(["profiles-api", "inference-api"])

  realm_id  = keycloak_realm.agi_project.id
  client_id = keycloak_openid_client.agi_web.id
  name      = "${each.key}-audience"

  included_custom_audience = each.key
  add_to_id_token          = false
  add_to_access_token      = true
}

# First admin user
resource "keycloak_user" "admin" {
  realm_id       = keycloak_realm.agi_project.id
  username       = var.admin_email
  email          = var.admin_email
  email_verified = true
  enabled        = true

  initial_password {
    value     = var.admin_initial_password
    temporary = true # forced to change at first login
  }
}

resource "keycloak_user_roles" "admin" {
  realm_id   = keycloak_realm.agi_project.id
  user_id    = keycloak_user.admin.id
  role_ids   = [keycloak_role.admin.id]
  exhaustive = true
}