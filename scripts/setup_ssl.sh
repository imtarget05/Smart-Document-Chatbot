#!/bin/bash
# SSL Certificate Setup Script for Smart Document Chatbot
# Generates self-signed cert for dev or provides instructions for production

set -e

KEYSTORE_PATH="backend/src/main/resources/keystore.p12"
KEYSTORE_PASSWORD="${SSL_KEY_STORE_PASSWORD:-changeit}"
ALIAS="smartdoc"
DAYS_VALID=365

echo "🔐 SSL Certificate Setup"
echo "========================"

if [ "$1" == "--production" ]; then
    echo ""
    echo "For PRODUCTION, use a real certificate from:"
    echo "  - Let's Encrypt (free): https://letsencrypt.org"
    echo "  - Your corporate CA"
    echo "  - Cloud provider (AWS ACM, GCP SSL, Azure Key Vault)"
    echo ""
    echo "Steps:"
    echo "1. Obtain certificate (cert.pem + key.pem)"
    echo "2. Convert to PKCS12:"
    echo "   openssl pkcs12 -export -in cert.pem -inkey key.pem \\"
    echo "     -out backend/src/main/resources/keystore.p12 \\"
    echo "     -name smartdoc -passout pass:\$SSL_KEY_STORE_PASSWORD"
    echo "3. Set SSL_ENABLED=true in production env"
    echo ""
else
    echo "Generating self-signed certificate for development..."
    
    # Remove old keystore
    rm -f "$KEYSTORE_PATH"
    
    # Generate self-signed certificate
    keytool -genkeypair \
        -alias "$ALIAS" \
        -keyalg RSA \
        -keysize 2048 \
        -storetype PKCS12 \
        -keystore "$KEYSTORE_PATH" \
        -validity "$DAYS_VALID" \
        -storepass "$KEYSTORE_PASSWORD" \
        -keypass "$KEYSTORE_PASSWORD" \
        -dname "CN=localhost, OU=Dev, O=SmartDoc, L=Hanoi, ST=VN, C=VN" \
        -ext "SAN=dns:localhost,ip:127.0.0.1"
    
    echo ""
    echo "✅ Self-signed certificate created:"
    echo "   Path: $KEYSTORE_PATH"
    echo "   Password: $KEYSTORE_PASSWORD"
    echo "   Valid: $DAYS_VALID days"
    echo ""
    echo "To enable SSL locally:"
    echo "  export SSL_ENABLED=true"
    echo "  export SSL_KEY_STORE_PASSWORD=$KEYSTORE_PASSWORD"
    echo ""
    echo "⚠️  Browsers will warn about self-signed cert — this is normal for dev."
fi
