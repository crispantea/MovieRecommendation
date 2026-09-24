variable "GCP_MACHINE_TYPE" {
  description = "Google Cloud instance type"
  default     = "n1-standard-1"
  type        = string
}

variable "GCP_ZONE" {
  description = "Google Cloud zone to deploy the instance"
  default     = "europe-west3-c"
  type        = string
}

variable "network_id" {
  description = "ID of the network to attach the instance"
  type        = string
}
