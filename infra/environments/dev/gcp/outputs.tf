output "master" {
    value = module.compute.master
}

output "master_ssh" {
 value = module.compute.master_ssh
}

output "workers"  {
  value = module.compute.workers
}

output "disks" {
  value = module.storage.disks
}
