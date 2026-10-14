resource "okta_network_zone" "office" {
  name     = "Office and VPN"
  type     = "IP"
  usage    = "POLICY"
  status   = "ACTIVE"
  gateways = var.office_cidrs
}

resource "okta_network_zone" "blocklist" {
  name     = "Blocked ranges"
  type     = "IP"
  usage    = "BLOCKLIST"
  status   = "ACTIVE"
  gateways = var.blocked_cidrs
}
