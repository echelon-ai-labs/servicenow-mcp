#!/bin/bash

# ServiceNow MCP - Google Cloud Run Deployment Script with Secret Manager
# This script deploys the ServiceNow MCP server to Google Cloud Run using Google Secret Manager for sensitive data

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="servicenow-mcp"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
}

# Function to get current project
get_current_project() {
    local current_project=$(gcloud config get-value project 2>/dev/null)
    if [ -n "$current_project" ]; then
        PROJECT_ID=$current_project
    fi
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it with your ServiceNow credentials."
        exit 1
    fi
}

# Function to read environment variables from .env file
load_env_vars() {
    print_info "Loading environment variables from .env file..."
    
    # Read .env file and export variables
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^#.*$ ]] && [[ -n "$key" ]]; then
            # Remove quotes from value
            value="${value%\"}"
            value="${value#\"}"
            export "$key=$value"
        fi
    done < .env
}

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
        print_info "Updating existing secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=- --project=$PROJECT_ID
    else
        print_info "Creating new secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=- --project=$PROJECT_ID
    fi
}

# Function to grant Cloud Run access to secrets
grant_secret_access() {
    local secret_name=$1
    local service_account=$2
    
    print_info "Granting access to secret: $secret_name"
    gcloud secrets add-iam-policy-binding $secret_name \
        --member="serviceAccount:$service_account" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID
}

# Main deployment function
deploy_to_cloud_run() {
    print_info "Starting deployment to Google Cloud Run with Secret Manager..."
    
    # Check prerequisites
    check_gcloud
    check_env_file
    load_env_vars
    
    # Get current project if not set
    if [ -z "$PROJECT_ID" ]; then
        get_current_project
        if [ -z "$PROJECT_ID" ]; then
            print_error "No Google Cloud project set. Please run: gcloud config set project YOUR_PROJECT_ID"
            exit 1
        fi
    fi
    
    print_info "Using project: $PROJECT_ID"
    print_info "Deploying to region: $REGION"
    print_info "Service name: $SERVICE_NAME"
    
    # Enable required APIs
    print_info "Enabling required Google Cloud APIs..."
    gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
    gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
    gcloud services enable run.googleapis.com --project=$PROJECT_ID
    
    # Get the Cloud Run service account
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    # Create secrets
    print_info "Creating/updating secrets in Secret Manager..."
    create_or_update_secret "servicenow-password" "$SERVICENOW_PASSWORD"
    
    # Grant access to secrets
    grant_secret_access "servicenow-password" "$SERVICE_ACCOUNT"
    
    # Confirm deployment
    echo ""
    print_warning "This will deploy the ServiceNow MCP server with the following configuration:"
    echo "  - Instance URL: $SERVICENOW_INSTANCE_URL"
    echo "  - Username: $SERVICENOW_USERNAME"
    echo "  - Password: [STORED IN SECRET MANAGER]"
    echo ""
    read -p "Do you want to continue? (y/N) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled."
        exit 0
    fi
    
    # Deploy to Cloud Run
    print_info "Deploying to Cloud Run (this may take a few minutes)..."
    
    gcloud run deploy $SERVICE_NAME \
        --source . \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port 8080 \
        --set-env-vars SERVICENOW_INSTANCE_URL="$SERVICENOW_INSTANCE_URL" \
        --set-env-vars SERVICENOW_USERNAME="$SERVICENOW_USERNAME" \
        --set-env-vars SERVICENOW_AUTH_TYPE="basic" \
        --set-env-vars MCP_TOOL_PACKAGE="full" \
        --update-secrets SERVICENOW_PASSWORD=servicenow-password:latest \
        --timeout 300 \
        --max-instances 10 \
        --project=$PROJECT_ID
    
    if [ $? -eq 0 ]; then
        print_info "Deployment successful!"
        
        # Get the service URL
        SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)
        
        echo ""
        print_info "Your ServiceNow MCP server is now running at:"
        echo "  $SERVICE_URL"
        echo ""
        print_info "SSE endpoint: $SERVICE_URL/sse"
        print_info "Messages endpoint: $SERVICE_URL/messages/"
        echo ""
        print_info "Secrets are stored in Google Secret Manager for enhanced security."
    else
        print_error "Deployment failed. Please check the error messages above."
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --service-name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID      Google Cloud project ID"
            echo "  --region REGION          Deployment region (default: us-central1)"
            echo "  --service-name NAME      Cloud Run service name (default: servicenow-mcp)"
            echo "  --help                   Show this help message"
            echo ""
            echo "This script uses Google Secret Manager to securely store sensitive credentials."
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the deployment
deploy_to_cloud_run
