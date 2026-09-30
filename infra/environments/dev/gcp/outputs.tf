output "master" {
    value = module.compute.master
}

output "master_ssh" {
 value = module.compute.master_ssh
}

output "worker_IPs"  {
  value = module.compute.worker_IPs
}
