# There is no default for this which means that this will fail
# if its not set. Set this in a terraform.tfvars file in this
# directory
variable "GCP_PROJECT_ID" {}

# A list of machine types is found at: https://cloud.google.com/compute/docs/machine-types
variable "GCP_MACHINE_TYPE" {
  default = "e2-standard-2"
}

# Regions list is found at:
# https://cloud.google.com/compute/docs/regions-zones/regions-zones?hl=en_US
variable "GCP_ZONE" {
  default = "europe-west3-c"
}

variable "public_key_path" {
  type        = string
  description = "File path to the SSH public key for authenticating as the 'ubuntu' user."
  default     = "/root/.ssh/id_rsa.pub"
}
