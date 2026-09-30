module "network" {
    source = "./../../../modules/gcp/network"
}

module "compute" {
    source = "./../../../modules/gcp/compute"

    public_key_path = var.public_key_path
    GCP_MACHINE_TYPE = var.GCP_MACHINE_TYPE
    GCP_ZONE = var.GCP_ZONE
}

resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../../../../ansible/gcphosts"

  content = templatefile("${path.module}/../../../../ansible/gcphosts.template", {
    master_name = module.compute.master.name
    master_ip   = module.compute.master.ip
    public_key_path = var.public_key_path

    workers = module.compute.workers
  })
}