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
  filename        = "${path.module}/../../../../ansible/inventory/hosts.yml"
  file_permission = "0644"

  content = yamlencode({
    all = {
      children = {
        master = {
          hosts = {
            (module.compute.master.name) = {
              ansible_host = module.compute.master.ip
              api_external_ip = module.compute.master.ip
            }
          }
        }
        workers = {
          hosts = {
            for w in module.compute.workers : w.name => {
              ansible_host = w.ip
            }
          }
        }
      }
    }
  })
}