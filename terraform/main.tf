# Data sources for image and SSH key
data "harvester_image" "img" {
  display_name = var.img_display_name
  namespace    = "harvester-public"
}

data "harvester_ssh_key" "mysshkey" {
  name      = var.keyname
  namespace = var.namespace
}

# Random ID for unique resource naming
resource "random_id" "secret" {
  byte_length = 5
}

# Cloud-init secret
resource "harvester_cloudinit_secret" "cloud-config" {
  name      = "cloud-config-${random_id.secret.hex}"
  namespace = var.namespace

  user_data = templatefile("cloud-init.tmpl.yml", {
    public_key_openssh = data.harvester_ssh_key.mysshkey.public_key,
    lecturer_key       = file("${path.module}/lecturer_key.pub")
  })
}

# Host Machine
resource "harvester_virtualmachine" "mgmtvm" {
  count                = 1
  name                 = "${var.username}-mgmt-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  namespace            = var.namespace
  restart_after_update = true
  description          = "Host Node"
  cpu                  = 2
  memory               = "4Gi"
  efi                  = true
  secure_boot          = false
  run_strategy         = "RerunOnFailure"
  hostname             = "${var.username}-mgmt-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  reserved_memory      = "100Mi"
  machine_type         = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = "10Gi"
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud-config.name
  }

  tags = {
    role                           = "management"
    description                    = "Management_node_for_coordinating_the_environment"
    storage_access_hostname        = "${var.username}-s3"
    storage_access_port            = 9000
    storage_access_protocol        = "https"
    storage_console_hostname       = "${var.username}-cons"
    storage_console_port           = 9001
    storage_console_protocol       = "https"
    condenser_ingress_prometheus_hostname = "prometheus-${var.username}"
    condenser_ingress_prometheus_port     = 9090
    condenser_ingress_nodeexporter_hostname = "nodeexporter-${var.username}"
    condenser_ingress_nodeexporter_port   = 9100
    condenser_ingress_grafana_hostname    = "grafana-${var.username}"
    condenser_ingress_grafana_port        = 3000
    condenser_ingress_spark_hostname = "spark-${var.username}"
    condenser_ingress_spark_port   = 8080
    condenser_ingress_react_hostname = "react-${var.username}"
    condenser_ingress_react_port = 3501
    condenser_ingress_flask_hostname = "flask-${var.username}"
    condenser_ingress_flask_port = 3500
    condenser_ingress_isEnabled           = true
    condenser_ingress_isAllowed           = true
  }
}


# Worker Machines
resource "harvester_virtualmachine" "worker" {
  count                = var.vm_count
  name                 = "${var.username}-worker-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  namespace            = var.namespace
  restart_after_update = true
  description          = "Worker Node"
  cpu                  = 4
  memory               = "32Gi"
  efi                  = true
  secure_boot          = true
  run_strategy         = "RerunOnFailure"
  hostname             = "${var.username}-worker-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  reserved_memory      = "100Mi"
  machine_type         = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name        = "rootdisk"
    type        = "disk"
    size        = "50Gi"
    bus         = "virtio"
    boot_order  = 1
    image       = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name        = "datadisk"
    type        = "disk"
    size        = "200Gi"
    bus         = "virtio"
    auto_delete = true
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud-config.name
  }

  tags = {
    role                        = "worker"
    description                 = "Worker_node_for_compute_tasks_connected_to_storage"
    storage_access_hostname     = "${var.username}-s3"
    storage_access_port         = 9000
    storage_access_protocol     = "https"
    storage_console_hostname    = "${var.username}-cons"
    storage_console_port        = 9001
    storage_console_protocol    = "https"
    condenser_ingress_isEnabled = true
    condenser_ingress_isAllowed = true
    condenser_ingress_nodeexporter_hostname = "nodeexporter-worker-${count.index + 1}-${var.username}"
    condenser_ingress_nodeexporter_port   = 9100
    condenser_ingress_spark_hostname = "spark-worker-${count.index + 1}-${var.username}"
    condenser_ingress_spark_port   = 8081
  }
}

