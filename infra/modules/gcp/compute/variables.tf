variable "GCP_MACHINE_TYPE" {
  type        = string
  description = "Google Cloud instance type"
}

variable "GCP_ZONE" {
  type        = string
  description = "Google Cloud zone to deploy the instance"
}

variable "public_key_path" {
  type        = string
  description = "File path to the SSH public key for authenticating as the 'ubuntu' user."
}