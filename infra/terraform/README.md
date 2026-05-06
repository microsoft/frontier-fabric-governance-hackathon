# Terraform IaC for Fabric Workspace Governance

This directory contains the Terraform port of the original Bicep template
(`infra/bicep/main.bicep`). It is wired into `azd` via `azure.yaml`:

```yaml
infra:
  provider: terraform
  path: infra/terraform
  module: main
```

## Files

| File | Purpose |
| --- | --- |
| `provider.tf` | `terraform { required_providers { azurerm ~> 4.14 } }` and provider features |
| `variables.tf` | All inputs (env name, location, GitHub App settings, principal id, optional `resource_token`) |
| `main.tf` | UAMI, Storage + container, Log Analytics, App Insights, Key Vault, Service Plan (FC1), Function App (Flex Consumption / Python 3.11), and three role assignments |
| `outputs.tf` | Outputs that azd writes back into `.azure/<env>/.env` (names match the original Bicep outputs) |
| `main.tfvars.json` | azd-managed parameter file. Uses `${VAR}` substitution from `.azure/<env>/.env` |
| `import.sh` | Helper that runs `terraform import` for every live resource so a switchover from the Bicep deployment is non-destructive |
| `.gitignore` | Keeps `.terraform/`, `*.tfstate`, and `*.auto.tfvars.json` out of the repo |

## Prerequisites

1. **Terraform CLI**
   ```bash
   brew install hashicorp/tap/terraform
   ```
2. **Enable azd's Terraform support** (still in alpha):
   ```bash
   azd config set alpha.terraform on
   ```
3. **azd >= 1.10** and **Azure CLI** logged in (`az login`).

## Migrating the existing `fwg-dev` deployment from Bicep to Terraform

The live environment was provisioned by Bicep and is healthy. To adopt it into
Terraform state without destroying anything:

```bash
cd infra/terraform

# 1. Initialise (downloads the azurerm provider, no remote backend yet)
terraform init

# 2. Pin the existing resource-name token so generated names match what's live.
#    This is already set in .azure/fwg-dev/.env via the AZURE_RESOURCE_TOKEN
#    azd env var; the import.sh defaults to it. Verify:
echo "Live token: rynra7bb2ogjk"

# 3. Import every live resource into local state
bash import.sh

# 4. Confirm zero/cosmetic drift
terraform plan -var-file=main.tfvars.json
```

Expected outcome: `terraform plan` should report **No changes** (or only
benign tag/setting drift such as deprecated `min_tls_version`). If it wants to
recreate anything, *do not apply* — open the plan, identify the drifted
attribute, and adjust `main.tf` so it matches reality before flipping over.

After a clean plan, set the resource token in the azd env so it survives
across `azd up` runs:

```bash
azd env set AZURE_RESOURCE_TOKEN rynra7bb2ogjk
```

Then you can deploy normally:

```bash
azd provision   # runs `terraform apply`
azd deploy api  # zips api/ and pushes to the same Function App
```

## Fresh deployment (new environment)

For a brand new environment, simply:

```bash
azd config set alpha.terraform on
azd env new <new-env-name>
azd up
```

The Terraform module will derive a fresh `resource_token` from a SHA-256 hash
of subscription id, resource group id, and environment name. Names will be
stable across runs once the env is provisioned (azd captures the output
`AZURE_RESOURCE_TOKEN` into `.azure/<env>/.env`).

## State

This module currently uses **local state** (`terraform.tfstate` next to the
files). For team use you should configure a remote backend, e.g.:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "<your tfstate account>"
    container_name       = "tfstate"
    key                  = "fwg-dev.tfstate"
  }
}
```

azd doesn't manage the backend for you - create the storage container yourself
and run `terraform init -migrate-state` after adding the block.

## Bicep is preserved

The original Bicep template lives untouched at `infra/bicep/`. To switch
back, change `azure.yaml`:

```yaml
infra:
  provider: bicep
  path: infra/bicep
  module: main
```

…and re-run `azd provision`. (Switching back is non-destructive: ARM is the
source of truth, and the resource names are stable across both providers as
long as the same `AZURE_RESOURCE_TOKEN` is used.)

## Why Terraform here? — short evaluation

| Aspect | Bicep | Terraform |
| --- | --- | --- |
| azd integration | GA | Alpha (`azd config set alpha.terraform on`) |
| Flex Consumption FC1 Function App | First-class via ARM | First-class via `azurerm_function_app_flex_consumption` (azurerm 4.x) |
| State | Stateless — ARM is the truth | Requires a state file or remote backend |
| Drift handling | `az deployment what-if` | `terraform plan` |
| Adopt existing live resources | n/a (already deployed by it) | Requires `terraform import` per resource (see `import.sh`) |
| Multi-cloud portability | Azure only | Azure / AWS / GCP — not relevant for this app |
| Verbosity | More compact for Azure | More boilerplate, more explicit |

For an Azure-only governance backend, Bicep was perfectly sufficient. We
maintain the Terraform port because the user requested it; it gives the team
the option of adopting Terraform tooling (Sentinel, OPA, drift detection
pipelines, etc.) without rewriting the IaC under pressure.
