output "master_ssh" {
  value = google_compute_instance.master.self_link
}

output "master" {
  value = {
    name = google_compute_instance.master.name
    ip   = google_compute_instance.master.network_interface[0].access_config[0].nat_ip
  }
}

output "workers" {
  value = [
    for instance in google_compute_instance.worker : {
      name = instance.name
      ip   = instance.network_interface[0].access_config[0].nat_ip
    }
  ]
}