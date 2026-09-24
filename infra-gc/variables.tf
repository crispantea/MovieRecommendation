# ID of the project, find it in the GCP console when clicking 
# on the project name (on the top dropdown)
variable "GCP_PROJECT_ID" {
  default = "agi-project-509613"
}

# A list of machine types is found at: https://cloud.google.com/compute/docs/machine-types
# NOTE: Prices are defined per region. Before choosing an instance, check the cost at:
# https://cloud.google.com/compute/pricing#machinetype
# Minimum required is N1 type = "n1-standard-1, 1 vCPU, 3.75 GB RAM"
variable "GCP_MACHINE_TYPE" {
  default = "n1-standard-1"
}

# Regions list is found at:
# https://cloud.google.com/compute/docs/regions-zones/regions-zones?hl=en_US
# NOTE: For prices of your deployment check: Compute Engine dashboard -> VM instances -> Zone
variable "GCP_ZONE" {
  default = "europe-west3-c"
}
