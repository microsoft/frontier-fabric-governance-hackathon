variable "environment_name" {
  type        = string
  description = "Environment name used for resource naming (e.g. fwg-dev)."
}

variable "location" {
  type        = string
  description = "Azure region for all resources."
}

variable "principal_id" {
  type        = string
  default     = ""
  description = "Object id of the user/group to grant Key Vault Administrator on the vault. Leave empty to skip."
}

variable "github_app_id" {
  type    = string
  default = ""
}

variable "github_installation_id" {
  type    = string
  default = ""
}

variable "github_owner" {
  type    = string
  default = ""
}

variable "github_repo" {
  type    = string
  default = "frontier-fabric-governance-hackathon"
}

variable "github_base_branch" {
  type    = string
  default = "main"
}

variable "resource_token" {
  type        = string
  default     = ""
  description = <<-EOT
    Optional. Pin the deterministic name suffix used for every resource (matches the
    `uniqueString(...)` token previously emitted by the Bicep template). Required when
    importing resources from the existing Bicep deployment. Leave empty to derive a new
    token for a fresh environment.
  EOT
}

variable "tags" {
  type    = map(string)
  default = {}
}
