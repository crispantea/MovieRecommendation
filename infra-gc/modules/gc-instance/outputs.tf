output "external_ip" {
  value = google_compute_instance.this.hostname
}