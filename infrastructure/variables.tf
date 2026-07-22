variable "do_token" {
  description = "DigitalOcean personal access token (https://cloud.digitalocean.com/account/api/tokens)"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key content to install on the droplet (e.g. content of ~/.ssh/id_ed25519.pub)"
  type        = string
}

variable "github_user" {
  description = "GitHub username used to pull images from GHCR (ghcr.io/<github_user>/...)"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token with read:packages scope for GHCR image pulls"
  type        = string
  sensitive   = true
}

variable "spaces_access_key" {
  description = "DigitalOcean Spaces access key (API → Spaces Keys — separate from the DO API token)"
  type        = string
  sensitive   = true
}

variable "spaces_secret_key" {
  description = "DigitalOcean Spaces secret key"
  type        = string
  sensitive   = true
}

variable "spaces_bucket_name" {
  description = "Name for the Spaces bucket — must be globally unique across all DO Spaces"
  type        = string
  default     = "assistente-estudos"
}

variable "droplet_name" {
  description = "Name for the DigitalOcean droplet"
  type        = string
  default     = "assistente-estudos"
}

variable "region" {
  description = "DigitalOcean region slug — must be a Spaces-enabled region: nyc3, ams3, sgp1, fra1, sfo3, syd1, tor1"
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = "Droplet size slug — s-2vcpu-4gb ($24/mo) is the recommended minimum"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "domain" {
  description = "Optional domain name to create an A record pointing to the droplet (e.g. assistente.example.com). Leave empty to skip DNS."
  type        = string
  default     = ""
}
