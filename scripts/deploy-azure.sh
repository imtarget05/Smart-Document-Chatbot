#!/usr/bin/env bash
# ==============================================================================
# Smart-Document-Chatbot — Automated Deployment Script for Azure Container Apps
# Deploys Spring Boot Backend API with scale-to-zero (minReplicas=0) for cost efficiency
# ==============================================================================

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-portfolio-prod}"
LOCATION="${LOCATION:-southeastasia}"
ACR_NAME="${ACR_NAME:-}"
CONTAINERAPPS_ENVIRONMENT="${CONTAINERAPPS_ENVIRONMENT:-cae-portfolio-env}"
APP_NAME="smart-document-api"
TARGET_PORT=8080
IMAGE_TAG="latest"

echo "=========================================================="
echo "🚀 Deploying Smart-Document-Chatbot Backend to Azure"
echo "Resource Group: $RESOURCE_GROUP | Location: $LOCATION"
echo "=========================================================="

if ! command -v az &> /dev/null; then
    echo "❌ Error: Azure CLI (az) is not installed."
    echo "💡 Install via Homebrew: brew install azure-cli"
    exit 1
fi

echo "🔍 Verifying Azure login status..."
az account show --output none || {
    echo "⚠️ Not logged in. Prompting for Azure login..."
    az login
}

echo "📦 Ensuring Resource Group [$RESOURCE_GROUP] exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

if [ -z "$ACR_NAME" ]; then
    SUBSCRIPTION_ID=$(az account show --query id -o tsv | tr -d '-' | cut -c1-6)
    ACR_NAME="crportfolio${SUBSCRIPTION_ID}"
fi

echo "🏭 Ensuring Azure Container Registry [$ACR_NAME] exists..."
if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    az acr create \
        --name "$ACR_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --sku Basic \
        --admin-enabled true \
        --location "$LOCATION" \
        --output table
fi

echo "🔨 Building and pushing image [$APP_NAME:$IMAGE_TAG] using ACR cloud build..."
az acr build \
    --registry "$ACR_NAME" \
    --image "${APP_NAME}:${IMAGE_TAG}" \
    --file docker/Dockerfile.backend \
    . \
    --output table

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_ADMIN_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
ACR_ADMIN_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)

echo "🌐 Ensuring Container Apps Environment [$CONTAINERAPPS_ENVIRONMENT] exists..."
if ! az containerapp env show --name "$CONTAINERAPPS_ENVIRONMENT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    az containerapp env create \
        --name "$CONTAINERAPPS_ENVIRONMENT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output table
fi

echo "🚀 Deploying Container App [$APP_NAME] with Scale-to-Zero (min-replicas=0)..."

az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINERAPPS_ENVIRONMENT" \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:${IMAGE_TAG}" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_ADMIN_USERNAME" \
    --registry-password "$ACR_ADMIN_PASSWORD" \
    --target-port "$TARGET_PORT" \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 1 \
    --cpu 0.75 \
    --memory 1.5Gi \
    --env-vars \
        "SPRING_PROFILES_ACTIVE=prod" \
        "NEON_DATABASE_URL=${NEON_DATABASE_URL:-}" \
        "SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL:-}" \
        "SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME:-}" \
        "SPRING_DATASOURCE_PASSWORD=${SPRING_DATASOURCE_PASSWORD:-}" \
        "JWT_SECRET=${JWT_SECRET:-}" \
        "QDRANT_HOST=${QDRANT_HOST:-}" \
        "QDRANT_API_KEY=${QDRANT_API_KEY:-}" \
    --output table || {
    echo "⚠️ Updating existing container app..."
    az containerapp update \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "${ACR_LOGIN_SERVER}/${APP_NAME}:${IMAGE_TAG}" \
        --output table
}

APP_URL=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "=========================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "🔗 Public Live API: https://${APP_URL}/swagger-ui/index.html"
echo "=========================================================="
echo "⚠️  Lưu ý: script này chỉ deploy BACKEND. LLM-Router (llm-router/) chưa có"
echo "   bản deploy Azure — backend sẽ báo 'LLM router unavailable' cho tới khi"
echo "   router được deploy (Render free tier: smart-doc-llm-router) và"
echo "   LLM_BASE_URL được trỏ tới URL đó trên Container App."
