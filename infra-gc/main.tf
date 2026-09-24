module "network" {
  source = "./modules/network"
  
  network_name = "lab3-network"
}

module "test_server" {
  source = "./modules/gc-instance"

  network_id = module.network.network_id
  GCP_MACHINE_TYPE = var.GCP_MACHINE_TYPE
  GCP_ZONE = var.GCP_ZONE
}