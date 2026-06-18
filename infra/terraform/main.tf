# Fabric Workspace Governance - backend for the M365 declarative agent.
# Provisions:
#   - Storage account + deployment container (required by Functions runtime)
#   - Log Analytics workspace + Application Insights (workspace-based)
#   - User-assigned Managed Identity (UAMI)
#   - Key Vault (RBAC mode) holding the GitHub App private key
#   - Linux Flex Consumption Function App (Python 3.11) with the UAMI attached
#   - RBAC: UAMI -> Key Vault Secrets User on the vault
#   - RBAC: UAMI -> Storage Blob Data Owner on the storage account
#
# This file is the Terraform port of infra/bicep/main.bicep. See
# infra/terraform/README.md for migration / import instructions.

data "azurerm_subscription" "current" {}

data "azurerm_resource_group" "rg" {
  name = "rg-${var.environment_name}"
}

locals {
  prefix = "fwg"

  # Bicep's `uniqueString(subscription().id, resourceGroup().id, environmentName)`
  # produces a 13-char base32-ish hash. We can't reproduce that algorithm exactly
  # in Terraform, so we either accept a pinned override (required for importing
  # an existing Bicep-deployed environment) or derive a stable sha256-based token
  # for fresh deployments.
  derived_token = lower(substr(
    replace(sha256("${data.azurerm_subscription.current.id}-${data.azurerm_resource_group.rg.id}-${var.environment_name}"), "/[^a-z0-9]/", ""),
    0, 13
  ))
  resource_token = var.resource_token != "" ? var.resource_token : local.derived_token

  base_tags = {
    "azd-env-name" = var.environment_name
    workload       = "frontier-fabric-governance-hackathon"
  }
  tags = merge(local.base_tags, var.tags)

  deployment_container_name = "app-package"

  # Built-in Azure RBAC role definition IDs (subscription-scoped).
  role_kv_secrets_user         = "4633458b-17de-408a-b874-0445c86b69e6"
  role_kv_administrator        = "00482a5a-887f-4fb3-b363-3b7fe8e74483"
  role_storage_blob_data_owner = "b7e6dc6d-f1e8-4753-8033-0f276bb0955b"

  # Resource names - kept deterministic so imports from the prior Bicep
  # deployment line up exactly with the live resources.
  uami_name    = "${local.prefix}-id-${local.resource_token}"
  storage_name = lower("${local.prefix}st${local.resource_token}")
  laws_name    = "${local.prefix}-log-${local.resource_token}"
  appi_name    = "${local.prefix}-appi-${local.resource_token}"
  kv_name      = "${local.prefix}-kv-${local.resource_token}"
  plan_name    = "${local.prefix}-plan-${local.resource_token}"
  func_name    = "${local.prefix}-func-${local.resource_token}"
}

# ---- Identity --------------------------------------------------------------
resource "azurerm_user_assigned_identity" "uami" {
  name                = local.uami_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  tags                = local.tags
}

# ---- Storage (Functions runtime + deployment package) ----------------------
resource "azurerm_storage_account" "storage" {
  name                            = local.storage_name
  resource_group_name             = data.azurerm_resource_group.rg.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true
  tags                            = local.tags
}

resource "azurerm_storage_container" "deployment" {
  name                  = local.deployment_container_name
  storage_account_id    = azurerm_storage_account.storage.id
  container_access_type = "private"
}

# ---- Log Analytics + Application Insights ---------------------------------
resource "azurerm_log_analytics_workspace" "laws" {
  name                = local.laws_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "appi" {
  name                = local.appi_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.laws.id
  tags                = local.tags
}

# ---- Key Vault -------------------------------------------------------------
resource "azurerm_key_vault" "kv" {
  name                          = local.kv_name
  resource_group_name           = data.azurerm_resource_group.rg.name
  location                      = var.location
  tenant_id                     = data.azurerm_subscription.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  soft_delete_retention_days    = 7
  purge_protection_enabled      = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_role_assignment" "kv_secrets_user" {
  scope              = azurerm_key_vault.kv.id
  role_definition_id = "${data.azurerm_subscription.current.id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_kv_secrets_user}"
  principal_id       = azurerm_user_assigned_identity.uami.principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_role_assignment" "kv_admin" {
  count              = var.principal_id != "" ? 1 : 0
  scope              = azurerm_key_vault.kv.id
  role_definition_id = "${data.azurerm_subscription.current.id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_kv_administrator}"
  principal_id       = var.principal_id
  principal_type     = "User"
}

# ---- RBAC: UAMI on storage (so Functions can read its package zip) --------
resource "azurerm_role_assignment" "storage_blob_owner" {
  scope              = azurerm_storage_account.storage.id
  role_definition_id = "${data.azurerm_subscription.current.id}/providers/Microsoft.Authorization/roleDefinitions/${local.role_storage_blob_data_owner}"
  principal_id       = azurerm_user_assigned_identity.uami.principal_id
  principal_type     = "ServicePrincipal"
}

# ---- Function App (Flex Consumption FC1, Python 3.11) ---------------------
resource "azurerm_service_plan" "plan" {
  name                = local.plan_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = local.tags
}

resource "azurerm_function_app_flex_consumption" "func" {
  name                = local.func_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  service_plan_id     = azurerm_service_plan.plan.id

  # Deployment package storage - using UAMI auth, no connection string needed.
  storage_container_type            = "blobContainer"
  storage_container_endpoint        = "${azurerm_storage_account.storage.primary_blob_endpoint}${azurerm_storage_container.deployment.name}"
  storage_authentication_type       = "UserAssignedIdentity"
  storage_user_assigned_identity_id = azurerm_user_assigned_identity.uami.id

  # Runtime
  runtime_name    = "python"
  runtime_version = "3.11"

  # Scale
  maximum_instance_count = 40
  instance_memory_in_mb  = 2048

  https_only = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.uami.id]
  }

  site_config {
    cors {
      allowed_origins = [
        "https://teams.microsoft.com",
        "https://m365.cloud.microsoft",
        "https://copilot.microsoft.com",
      ]
    }
  }

  app_settings = {
    AzureWebJobsStorage__accountName      = azurerm_storage_account.storage.name
    AzureWebJobsStorage__credential       = "managedidentity"
    AzureWebJobsStorage__clientId         = azurerm_user_assigned_identity.uami.client_id
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.appi.connection_string
    AZURE_CLIENT_ID                       = azurerm_user_assigned_identity.uami.client_id
    KEY_VAULT_URL                         = azurerm_key_vault.kv.vault_uri
    GITHUB_PRIVATE_KEY_SECRET             = "github-app-private-key"
    GITHUB_APP_ID                         = var.github_app_id
    GITHUB_INSTALLATION_ID                = var.github_installation_id
    GITHUB_OWNER                          = var.github_owner
    GITHUB_REPO                           = var.github_repo
    GITHUB_BASE_BRANCH                    = var.github_base_branch
    # Default 'true' so the Function comes up healthy without GitHub App
    # credentials. Flip to 'false' once the PEM is in Key Vault and
    # GITHUB_APP_ID / GITHUB_INSTALLATION_ID are set.
    DRY_RUN = "true"
  }

  tags = merge(local.tags, { "azd-service-name" = "api" })

  depends_on = [
    azurerm_role_assignment.storage_blob_owner,
  ]
}
