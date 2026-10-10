resource "google_compute_disk" "this" {
  for_each = var.services

  name    = "k8s-${each.key}-data"
  zone    = var.GCP_ZONE
  size    = each.value.size
  type    = each.value.type == "ssd" ? "pd-ssd" : "pd-standard"
}