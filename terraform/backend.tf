# Partial config. CI passes bucket/prefix with -backend-config, so the same
# code can point at one state per org (nonprod, prod-readonly).
# Local checks use `terraform init -backend=false`.
terraform {
  backend "gcs" {}
}
