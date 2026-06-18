// Fabric Workspace Governance — backend for the M365 declarative agent.
// Provisions:
//   - Storage (required by Functions runtime)
//   - Log Analytics + Application Insights
//   - User-assigned Managed Identity (UAMI)
//   - Key Vault (RBAC mode) holding the GitHub App private key
//   - Linux Flex Consumption Function App (Python) with the UAMI attached
//   - RBAC: UAMI → Key Vault Secrets User on the vault
//
// Naming follows azd conventions; the resource token is generated once.

targetScope = 'resourceGroup'

@description('Environment name used for resource naming (e.g. dev, prd).')
param environmentName string

@description('Location for all resources.')
param location string = resourceGroup().location

@description('Tags applied to every resource.')
param tags object = {
  'azd-env-name': environmentName
  workload: 'frontier-fabric-governance-hackathon'
}

@description('GitHub App ID (stored as plain App Setting).')
param githubAppId string = ''

@description('GitHub App installation ID for this repo.')
param githubInstallationId string = ''

@description('GitHub repo owner (org or user).')
param githubOwner string = ''

@description('GitHub repo name.')
param githubRepo string = 'frontier-fabric-governance-hackathon'

@description('Default branch the agent opens PRs against.')
param githubBaseBranch string = 'main'

@description('Email of the person who should be a Key Vault Administrator (puts the GitHub App private key in the vault). Leave empty to skip.')
param keyVaultAdminPrincipalId string = ''

var resourceToken = uniqueString(subscription().id, resourceGroup().id, environmentName)
var prefix = 'fwg' // frontier-fabric-governance-hackathon

// ---- Identity ----------------------------------------------------------
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-${resourceToken}'
  location: location
  tags: tags
}

// ---- Storage (Functions runtime) ---------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${prefix}st${resourceToken}')
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

// ---- Log Analytics + App Insights --------------------------------------
resource laws 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appi-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: laws.id
  }
}

// ---- Key Vault ---------------------------------------------------------
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

// Built-in role IDs
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var keyVaultAdministratorRoleId = '00482a5a-887f-4fb3-b363-3b7fe8e74483'

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, uami.id, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource kvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(keyVaultAdminPrincipalId)) {
  scope: kv
  name: guid(kv.id, keyVaultAdminPrincipalId, keyVaultAdministratorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultAdministratorRoleId)
    principalId: keyVaultAdminPrincipalId
    principalType: 'User'
  }
}

// ---- Function App (Flex Consumption, Python 3.11) ----------------------
resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${prefix}-plan-${resourceToken}'
  location: location
  tags: tags
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  kind: 'functionapp'
  properties: {
    reserved: true
  }
}

var deploymentContainerName = 'app-package'

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/${deploymentContainerName}'
  properties: {
    publicAccess: 'None'
  }
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: '${prefix}-func-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uami.id}': {}
    }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    keyVaultReferenceIdentity: uami.id
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentContainerName}'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: uami.id
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 40
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storage.name
        }
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
        }
        {
          name: 'AzureWebJobsStorage__clientId'
          value: uami.properties.clientId
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appi.properties.ConnectionString
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: uami.properties.clientId
        }
        {
          name: 'KEY_VAULT_URL'
          value: kv.properties.vaultUri
        }
        {
          name: 'GITHUB_PRIVATE_KEY_SECRET'
          value: 'github-app-private-key'
        }
        {
          name: 'GITHUB_APP_ID'
          value: githubAppId
        }
        {
          name: 'GITHUB_INSTALLATION_ID'
          value: githubInstallationId
        }
        {
          name: 'GITHUB_OWNER'
          value: githubOwner
        }
        {
          name: 'GITHUB_REPO'
          value: githubRepo
        }
        {
          name: 'GITHUB_BASE_BRANCH'
          value: githubBaseBranch
        }
        {
          // Default 'true' so the Function comes up healthy without GitHub
          // App credentials. Flip to 'false' once the PEM is in Key Vault
          // and GITHUB_APP_ID / GITHUB_INSTALLATION_ID are set.
          name: 'DRY_RUN'
          value: 'true'
        }
      ]
      cors: {
        allowedOrigins: [
          'https://teams.microsoft.com'
          'https://m365.cloud.microsoft'
          'https://copilot.microsoft.com'
        ]
      }
    }
  }
}

// Storage Blob Data Owner so the Function can read/write its deployment package
var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
resource storageBlobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, uami.id, storageBlobDataOwnerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---- Outputs -----------------------------------------------------------
output AZURE_FUNCTION_APP_NAME string = func.name
output AZURE_FUNCTION_APP_HOSTNAME string = func.properties.defaultHostName
output AZURE_KEY_VAULT_NAME string = kv.name
output AZURE_KEY_VAULT_URL string = kv.properties.vaultUri
output AZURE_USER_ASSIGNED_IDENTITY_ID string = uami.id
output AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID string = uami.properties.clientId
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appi.properties.ConnectionString
