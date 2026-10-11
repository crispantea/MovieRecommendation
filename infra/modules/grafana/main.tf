resource "grafana_folder" "app_monitoring" {
  title = "Application Monitoring"
}

resource "grafana_dashboard" "keycloak" {
  folder      = grafana_folder.app_monitoring.uid
  config_json = file("${path.module}/dashboards/keycloak.json")
  overwrite   = true
}

resource "grafana_dashboard" "inference_service" {
  folder      = grafana_folder.app_monitoring.uid
  config_json = file("${path.module}/dashboards/inference_service.json")
  overwrite   = true
}