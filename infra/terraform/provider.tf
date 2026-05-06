terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      # Don't purge on destroy: lets us recover the vault if `terraform destroy`
      # is run by mistake. Soft-delete retention is 7 days.
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      # Allow `terraform destroy` to clean up child resources implicitly.
      prevent_deletion_if_contains_resources = false
    }
  }
}
