module "auth" {
    providers = {
        keycloak = keycloak
    }
    source = "./../../modules/keycloak/auth"

    frontend_url = var.frontend_url
    admin_email = var.admin_email 
    admin_initial_password = var.admin_initial_password
    keycloak_url = var.keycloak_url
}