###########  Web Servers   #############
resource "google_compute_instance" "worker" {
    count = 3
    name = "worker${count.index+1}"
    machine_type = var.GCP_MACHINE_TYPE
    zone = var.GCP_ZONE

    boot_disk {
        initialize_params {
          image = "ubuntu-os-cloud/ubuntu-2204-lts" # TODO: Check if we want to change this
        }
    }

    network_interface {
        network = "default"
        access_config {
        }
    }

    metadata = {
      ssh-keys = "ubuntu:${file(var.public_key_path)}"
    }
  tags = ["cluster", "worker"]
}


###########  Master   #############
resource "google_compute_instance" "master" {
    name = "master"
    machine_type = var.GCP_MACHINE_TYPE
    zone = var.GCP_ZONE

    boot_disk {
        initialize_params {
          image = "ubuntu-os-cloud/ubuntu-2204-lts"
        }
    }

    network_interface {
        network = "default"
        access_config {
        }
    }

    metadata = {
      ssh-keys = "ubuntu:${file(var.public_key_path)}"
    }

  tags = ["cluster", "master"]
}

