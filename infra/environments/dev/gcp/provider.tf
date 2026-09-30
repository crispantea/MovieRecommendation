# GCP provider is not specified here so the hashicorp default is used

provider "google" {
  credentials = file("credentials.json")
  project = var.GCP_PROJECT_ID
  zone = var.GCP_ZONE
}