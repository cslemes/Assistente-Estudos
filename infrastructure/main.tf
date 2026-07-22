terraform {
  required_version = ">= 1.5"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.47"
    }
  }
}

provider "digitalocean" {
  token             = var.do_token
  spaces_access_id  = var.spaces_access_key
  spaces_secret_key = var.spaces_secret_key
}

# ── Spaces bucket ─────────────────────────────────────────────────────────────

resource "digitalocean_spaces_bucket" "storage" {
  name   = var.spaces_bucket_name
  region = var.region
  acl    = "private"

  versioning {
    enabled = false
  }
}

# Allow public GET on all objects (mirrors MinIO's `mc anonymous set download`)
resource "digitalocean_spaces_bucket_policy" "public_read" {
  region = digitalocean_spaces_bucket.storage.region
  bucket = digitalocean_spaces_bucket.storage.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject"]
      Resource  = ["arn:aws:s3:::${digitalocean_spaces_bucket.storage.name}/*"]
    }]
  })
}

resource "digitalocean_spaces_bucket_cors_configuration" "storage" {
  region = digitalocean_spaces_bucket.storage.region
  bucket = digitalocean_spaces_bucket.storage.name

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

# ── SSH key ───────────────────────────────────────────────────────────────────

resource "digitalocean_ssh_key" "deploy" {
  name       = "${var.droplet_name}-deploy"
  public_key = var.ssh_public_key
}

# ── Droplet ───────────────────────────────────────────────────────────────────

resource "digitalocean_droplet" "app" {
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-24-04-x64"
  ssh_keys = [digitalocean_ssh_key.deploy.fingerprint]
  tags     = ["assistente-estudos", "production"]

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    github_user         = var.github_user
    github_token        = var.github_token
    env_contents        = file("${path.module}/../.env")
    compose_contents    = file("${path.module}/../docker-compose.prod.yml")
    spaces_endpoint     = "https://${var.region}.digitaloceanspaces.com"
    spaces_access_key   = var.spaces_access_key
    spaces_secret_key   = var.spaces_secret_key
    spaces_bucket_name  = digitalocean_spaces_bucket.storage.name
    spaces_public_url   = "https://${digitalocean_spaces_bucket.storage.name}.${var.region}.digitaloceanspaces.com"
    spaces_region       = var.region
  })

  depends_on = [digitalocean_spaces_bucket_policy.public_read]
}

# ── Firewall ──────────────────────────────────────────────────────────────────

resource "digitalocean_firewall" "app" {
  name        = "${var.droplet_name}-fw"
  droplet_ids = [digitalocean_droplet.app.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# ── Optional: domain A record ─────────────────────────────────────────────────

resource "digitalocean_domain" "app" {
  count      = var.domain != "" ? 1 : 0
  name       = var.domain
  ip_address = digitalocean_droplet.app.ipv4_address
}

resource "digitalocean_record" "www" {
  count  = var.domain != "" ? 1 : 0
  domain = digitalocean_domain.app[0].name
  type   = "A"
  name   = "www"
  value  = digitalocean_droplet.app.ipv4_address
  ttl    = 300
}
