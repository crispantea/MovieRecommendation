output "disks" {
  value = {
    for name, disk in google_compute_disk.this : name => {
      name          = disk.name
      self_link     = disk.self_link
      volume_handle = "projects/${var.GCP_PROJECT_ID}/zones/${var.GCP_ZONE}/disks/${disk.name}"
      size          = disk.size
      type          = disk.type
      zone          = var.GCP_ZONE
    }
  }
}
