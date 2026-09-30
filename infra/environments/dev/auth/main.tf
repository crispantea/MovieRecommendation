module "auth" {
    providers = {
        keycloak = keycloak
    }
    source = "./../../../modules/keycloak/auth"

    frontend_url = var.frontend_url
    keycloak_url = var.keycloak_url
}