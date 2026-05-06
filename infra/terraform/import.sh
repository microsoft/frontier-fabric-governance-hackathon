#!/usr/bin/env bash
# Import the existing Bicep-deployed resources into Terraform state so that
# the first `terraform apply` (or `azd up` after switching providers) produces
# zero changes. Run this once, from inside infra/terraform/, after `terraform init`.
#
# Required env (defaults match the live fwg-dev environment):
#   SUBSCRIPTION_ID  (default: 4673f58d-c87c-40ea-a2cc-aae692d16d6f)
#   RESOURCE_GROUP   (default: rg-fwg-dev)
#   RESOURCE_TOKEN   (default: rynra7bb2ogjk)
#   PRINCIPAL_ID     (the Object ID granted Key Vault Administrator;
#                    leave empty if you didn't deploy that role assignment)
#
# Re-running is safe: terraform import is a no-op if the address is already in
# state.

set -euo pipefail

SUB="${SUBSCRIPTION_ID:-4673f58d-c87c-40ea-a2cc-aae692d16d6f}"
RG="${RESOURCE_GROUP:-rg-fwg-dev}"
TOKEN="${RESOURCE_TOKEN:-rynra7bb2ogjk}"
PRINCIPAL="${PRINCIPAL_ID:-}"

PFX="fwg"
UAMI_NAME="${PFX}-id-${TOKEN}"
STG_NAME="${PFX}st${TOKEN}"
LAWS_NAME="${PFX}-log-${TOKEN}"
APPI_NAME="${PFX}-appi-${TOKEN}"
KV_NAME="${PFX}-kv-${TOKEN}"
PLAN_NAME="${PFX}-plan-${TOKEN}"
FUNC_NAME="${PFX}-func-${TOKEN}"

UAMI_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/${UAMI_NAME}"
STG_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Storage/storageAccounts/${STG_NAME}"
LAWS_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.OperationalInsights/workspaces/${LAWS_NAME}"
APPI_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Insights/components/${APPI_NAME}"
KV_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.KeyVault/vaults/${KV_NAME}"
PLAN_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Web/serverfarms/${PLAN_NAME}"
FUNC_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Web/sites/${FUNC_NAME}"
CONTAINER_ID="https://${STG_NAME}.blob.core.windows.net/app-package"

# Built-in role IDs
ROLE_KV_SECRETS_USER="4633458b-17de-408a-b874-0445c86b69e6"
ROLE_KV_ADMINISTRATOR="00482a5a-887f-4fb3-b363-3b7fe8e74483"
ROLE_STG_BLOB_OWNER="b7e6dc6d-f1e8-4753-8033-0f276bb0955b"

# Look up role assignment ids (Terraform imports them by full id, not by GUID name).
ra_id() {
  local scope="$1" role="$2" principal="$3"
  az role assignment list \
    --scope "${scope}" \
    --role "${role}" \
    --assignee "${principal}" \
    --query "[0].id" -o tsv 2>/dev/null
}

UAMI_PRINCIPAL_ID="$(az identity show --ids "${UAMI_ID}" --query principalId -o tsv 2>/dev/null || true)"
if [[ -z "${UAMI_PRINCIPAL_ID}" ]]; then
  echo "ERROR: could not resolve principalId for ${UAMI_NAME}. Is it deployed?" >&2
  exit 1
fi

KV_SECRETS_USER_RA="$(ra_id "${KV_ID}" "${ROLE_KV_SECRETS_USER}" "${UAMI_PRINCIPAL_ID}")"
STG_BLOB_OWNER_RA="$(ra_id "${STG_ID}" "${ROLE_STG_BLOB_OWNER}" "${UAMI_PRINCIPAL_ID}")"

echo "==> Importing core resources"
terraform import azurerm_user_assigned_identity.uami        "${UAMI_ID}"
terraform import azurerm_storage_account.storage            "${STG_ID}"
terraform import azurerm_storage_container.deployment       "${CONTAINER_ID}"
terraform import azurerm_log_analytics_workspace.laws       "${LAWS_ID}"
terraform import azurerm_application_insights.appi          "${APPI_ID}"
terraform import azurerm_key_vault.kv                       "${KV_ID}"
terraform import azurerm_service_plan.plan                  "${PLAN_ID}"
terraform import azurerm_function_app_flex_consumption.func "${FUNC_ID}"

echo "==> Importing role assignments"
if [[ -n "${KV_SECRETS_USER_RA}" ]]; then
  terraform import azurerm_role_assignment.kv_secrets_user  "${KV_SECRETS_USER_RA}"
else
  echo "WARN: Key Vault Secrets User role assignment for UAMI not found - skipping."
fi

if [[ -n "${STG_BLOB_OWNER_RA}" ]]; then
  terraform import azurerm_role_assignment.storage_blob_owner "${STG_BLOB_OWNER_RA}"
else
  echo "WARN: Storage Blob Data Owner role assignment for UAMI not found - skipping."
fi

if [[ -n "${PRINCIPAL}" ]]; then
  KV_ADMIN_RA="$(ra_id "${KV_ID}" "${ROLE_KV_ADMINISTRATOR}" "${PRINCIPAL}")"
  if [[ -n "${KV_ADMIN_RA}" ]]; then
    terraform import 'azurerm_role_assignment.kv_admin[0]'  "${KV_ADMIN_RA}"
  else
    echo "WARN: Key Vault Administrator assignment for ${PRINCIPAL} not found - skipping."
  fi
fi

echo
echo "All applicable resources imported."
echo "Now run: terraform plan -var-file=main.tfvars.json"
echo "It should report 'No changes' (or only cosmetic tag/setting drift)."
