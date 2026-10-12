# ================================================================================================ #
# ========== Workers ============================================================================= #
# ================================================================================================ #
resource "google_compute_instance" "worker" {
  count = 3
  name = "worker${count.index+1}"
  machine_type = var.GCP_MACHINE_TYPE
  zone = var.GCP_ZONE

  boot_disk {
    initialize_params {
      size = 20
      image = "ubuntu-os-cloud/ubuntu-2204-lts" # TODO: Check if we want to change this
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.public_key_path)}"
  }
  tags = ["cluster", "worker"]
}


# ================================================================================================ #
# ========== Control Plane ======================================================================= #
# ================================================================================================ #
resource "google_compute_instance" "master" {
  name = "control-plane"
  machine_type = var.GCP_MACHINE_TYPE
  zone = var.GCP_ZONE

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.public_key_path)}"
  }

  tags = ["cluster", "master"]
}

