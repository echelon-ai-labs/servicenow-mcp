# ServiceNow MCP - Google Cloud Run Deployment Guide

Deploy the ServiceNow MCP server to Google Cloud Run without Docker installed locally.

## Prerequisites

1. **Google Cloud SDK (gcloud)** installed and authenticated
2. **Google Cloud Project** with billing enabled
3. **ServiceNow credentials** in your `.env` file

## Quick Start

```bash
./deploy-with-secrets.sh
```

This script:
- Loads credentials from `.env`
- Stores passwords in Google Secret Manager
- Builds container using Cloud Build
- Deploys to Cloud Run with enhanced security
- Displays the service URL

## Manual Deployment

### Direct from source:
```bash
gcloud run deploy servicenow-mcp \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars-file .env
```

### Using Cloud Build:
```bash
# Build image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/servicenow-mcp

# Deploy image
gcloud run deploy servicenow-mcp \
  --image gcr.io/YOUR_PROJECT_ID/servicenow-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars-file .env
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SERVICENOW_INSTANCE_URL` | ServiceNow instance URL | Yes |
| `SERVICENOW_USERNAME` | ServiceNow username | Yes |
| `SERVICENOW_PASSWORD` | ServiceNow password | Yes |
| `SERVICENOW_AUTH_TYPE` | Auth type (basic/oauth/api_key) | No |
| `MCP_TOOL_PACKAGE` | Tool package (full/minimal/none) | No |

## Service Endpoints

- **SSE Endpoint**: `https://[service-url]/sse` - For MCP clients
- **Health Check**: `https://[service-url]/health` - Service status
- **Messages**: `https://[service-url]/messages/` - MCP messages

## Connecting with MCP Inspector

1. Deploy the service using one of the methods above
2. Copy the service URL from the deployment output
3. Open MCP Inspector
4. Enter: `https://[service-url]/sse`
5. Click Connect

## Troubleshooting

### View logs:
```bash
gcloud run services logs read servicenow-mcp --region us-central1
```

### Stream logs:
```bash
gcloud run services logs tail servicenow-mcp --region us-central1
```

### Common issues:
- **"gcloud not found"**: Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **"Project not set"**: Run `gcloud config set project YOUR_PROJECT_ID`
- **Build failures**: Check logs with `gcloud builds list --limit=5`

## Updating the Service

```bash
# Using deployment script
./deploy-with-secrets.sh

# Or manually
gcloud run deploy servicenow-mcp --source . --region us-central1
```

## Cleanup

```bash
# Delete service
gcloud run services delete servicenow-mcp --region us-central1

# Delete secrets (if using secure deployment)
gcloud secrets delete servicenow-password
```

## Cost Optimization

Cloud Run charges only when handling requests and scales to zero when idle. First 2 million requests per month are free.
