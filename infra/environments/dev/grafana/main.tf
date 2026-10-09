module "grafana" {
    providers = {
        grafana = grafana
    }
    source = "./../../../modules/grafana"
}