environment = "nonprod"

# Replace with your own office / VPN egress ranges.
office_cidrs  = ["198.51.100.0/24"]
blocked_cidrs = ["203.0.113.0/24"]

oidc_redirect_uris = ["https://oidcdebugger.com/debug"]
