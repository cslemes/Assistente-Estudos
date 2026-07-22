output "droplet_ip" {
  description = "Public IPv4 address of the droplet"
  value       = digitalocean_droplet.app.ipv4_address
}

output "app_url" {
  description = "URL to access the application"
  value       = var.domain != "" ? "http://${var.domain}" : "http://${digitalocean_droplet.app.ipv4_address}"
}

output "ssh_command" {
  description = "SSH command to connect to the droplet"
  value       = "ssh root@${digitalocean_droplet.app.ipv4_address}"
}

output "logs_command" {
  description = "Command to tail app logs from the droplet"
  value       = "ssh root@${digitalocean_droplet.app.ipv4_address} 'cd /opt/assistente && docker compose logs -f'"
}

output "spaces_bucket" {
  description = "DigitalOcean Spaces bucket name"
  value       = digitalocean_spaces_bucket.storage.name
}

output "spaces_endpoint" {
  description = "Spaces S3-compatible endpoint URL (for boto3 / aws CLI)"
  value       = "https://${var.region}.digitaloceanspaces.com"
}

output "spaces_public_url" {
  description = "Base public URL for stored files"
  value       = "https://${digitalocean_spaces_bucket.storage.name}.${var.region}.digitaloceanspaces.com"
}
