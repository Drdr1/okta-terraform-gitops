terraform {
  # 1.5+ for `import` blocks and `plan -generate-config-out`.
  required_version = ">= 1.5.0"

  required_providers {
    okta = {
      source = "okta/okta"
      # The provider's GitHub README (checked Oct 2026) warns against 6.14.0
      # and names 6.15.0 as the highest recommended release, although 7.0.0
      # exists. Bump deliberately, in its own PR, after reading the changelog.
      version = "~> 6.15.0"
    }
  }
}
