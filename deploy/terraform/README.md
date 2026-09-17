# 🏗️ Terraform Infrastructure as Code (IaC) — Smart-Document-Chatbot

Quản lý hạ tầng Azure Container Apps cho Spring Boot Backend API bằng Terraform:

```bash
cd deploy/terraform
terraform init

# Credentials truyền qua tfvars (KHÔNG commit file này):
#   neon_database_url          — jdbc:postgresql://<host>/<db>?sslmode=require
#   spring_datasource_username / spring_datasource_password — từ cùng connection string Neon
#   jwt_secret                 — openssl rand -base64 48
#   qdrant_host / qdrant_api_key — cloud.qdrant.tech
cat > terraform.tfvars <<'EOF'
neon_database_url          = "jdbc:postgresql://...neon.tech/...?sslmode=require"
spring_datasource_username = "..."
spring_datasource_password = "..."
jwt_secret                 = "..."
qdrant_host                = "..."
qdrant_api_key             = "..."
EOF

terraform plan
terraform apply -auto-approve
```

Lưu ý: `terraform.tfvars` chứa secret — đã được gitignore, không bao giờ commit.
Ảnh container được push riêng bằng `az acr build` (xem `scripts/deploy-azure.sh`).

