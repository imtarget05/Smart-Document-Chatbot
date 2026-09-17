terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Smart-Document-Chatbot"
  }
}

resource "azurerm_container_registry" "acr" {
  name                = coalesce(var.acr_name, "crportfolio${random_string.suffix.result}")
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = azurerm_resource_group.rg.tags
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "smartdoc-law"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = azurerm_resource_group.rg.tags
}

resource "azurerm_container_app_environment" "env" {
  name                       = "smartdoc-cae-env"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  tags                       = azurerm_resource_group.rg.tags
}

resource "azurerm_container_app" "backend" {
  name                         = "smart-document-api"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = azurerm_resource_group.rg.tags

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "smart-document-backend"
      image  = "${azurerm_container_registry.acr.login_server}/smart-document-api:${var.image_tag}"
      cpu    = 0.75
      memory = "1.5Gi"

      env {
        name  = "SPRING_PROFILES_ACTIVE"
        value = "prod"
      }
      env {
        name  = "NEON_DATABASE_URL"
        value = var.neon_database_url
      }
      env {
        name  = "SPRING_DATASOURCE_USERNAME"
        value = var.spring_datasource_username
      }
      env {
        name  = "SPRING_DATASOURCE_PASSWORD"
        value = var.spring_datasource_password
      }
      env {
        name  = "JWT_SECRET"
        value = var.jwt_secret
      }
      env {
        name  = "QDRANT_HOST"
        value = var.qdrant_host
      }
      env {
        name  = "QDRANT_API_KEY"
        value = var.qdrant_api_key
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
