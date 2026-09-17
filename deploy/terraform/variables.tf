variable "resource_group_name" {
  type    = string
  default = "rg-portfolio-prod"
}

variable "location" {
  type    = string
  default = "southeastasia"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "acr_name" {
  type    = string
  default = ""
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "neon_database_url" {
  type      = string
  default   = ""
  sensitive = true
}

variable "qdrant_host" {
  type    = string
  default = ""
}

variable "qdrant_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "spring_datasource_username" {
  type      = string
  default   = ""
  sensitive = true
}

variable "spring_datasource_password" {
  type      = string
  default   = ""
  sensitive = true
}

variable "jwt_secret" {
  type      = string
  default   = ""
  sensitive = true
}
