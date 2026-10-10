variable "GCP_PROJECT_ID" {}

variable "GCP_ZONE" {
  type        = string
  description = "Google Cloud zone to deploy the instance"
}

variable "services" {
  description = "Persistent disk configuration keyed by service name."

  type = map(object({
    size = number
    type = string # ssd or hdd
  }))

  validation {
    condition = alltrue([
      for service in values(var.services) :
      contains(["ssd", "hdd"], service.type) && service.size > 0
    ])
    error_message = "Disk type must be ssd or hdd, and size must be positive."
  }
}
