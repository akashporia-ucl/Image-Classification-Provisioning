output "management_vm_ips" {
  description = "IP addresses of the management node"
  value       = harvester_virtualmachine.mgmtvm[*].network_interface[0].ip_address
}

output "worker_vm_ips" {
  description = "IP addresses of the worker nodes"
  value       = harvester_virtualmachine.worker[*].network_interface[0].ip_address
}

output "username" {
  value = var.username
}
