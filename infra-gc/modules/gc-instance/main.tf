resource "google_compute_instance" "this" {
  name          = "test-instance"
  machine_type  = var.GCP_MACHINE_TYPE
  zone          = var.GCP_ZONE

  boot_disk {
    initialize_params {
      # NOTE: Image list can be found at: https://console.cloud.google.com/compute/images
      image = "debian-13-trixie-v20260921"
    }
  }

  network_interface {
    # A default network is created for all GCP projects
    network = var.network_id
    access_config {
    }
  }

  metadata = {
    ssh-keys = "debian:${file("/root/.ssh/id_rsa.pub")}"
  }
}
