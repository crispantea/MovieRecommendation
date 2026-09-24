provider "google" {
  credentials = file("credentials.json")
  project = var.GCP_PROJECT_ID
  zone = var.GCP_ZONE
}