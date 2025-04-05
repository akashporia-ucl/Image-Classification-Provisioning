locals {
  rendered_config = templatefile("${path.module}/../ansible/templates/grafana_datasource.yml.j2", {
    username = var.username
  })
}
