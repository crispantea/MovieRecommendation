output "master" {
    value = module.compute.master
}

output "master_ssh" {
 value = module.compute.master_ssh
}

output "workers"  {
  value = module.compute.workers
}
