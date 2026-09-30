module "network" {
    source = "./../../../modules/gcp/network"
}

module "compute" {
    source = "./../../../modules/gcp/compute"

    public_key_path = var.public_key_path
    GCP_MACHINE_TYPE = var.GCP_MACHINE_TYPE
    GCP_ZONE = var.GCP_ZONE
}