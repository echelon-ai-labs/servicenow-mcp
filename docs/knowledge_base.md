# Knowledge Base Management

The ServiceNow MCP server provides tools for managing knowledge bases, categories, and articles in ServiceNow.

## Overview

Knowledge bases in ServiceNow allow organizations to store and share information in a structured format. This can include documentation, FAQs, troubleshooting guides, and other knowledge resources.

The ServiceNow MCP Knowledge Base tools provide a way to create and manage knowledge bases, categories, and articles through the ServiceNow API.

## Available Tools

### Knowledge Base Management

1. **create_knowledge_base** - Create a new knowledge base in ServiceNow
   - Parameters:
     - `title` - Title of the knowledge base
     - `description` (optional) - Description of the knowledge base
     - `owner` (optional) - The specified admin user or group
     - `managers` (optional) - Users who can manage this knowledge base
     - `publish_workflow` (optional) - Publication workflow
     - `retire_workflow` (optional) - Retirement workflow

2. **list_knowledge_bases** - List knowledge bases from ServiceNow
   - Parameters:
     - `limit` (optional, default: 10) - Maximum number of knowledge bases to return
     - `offset` (optional, default: 0) - Offset for pagination
     - `active` (optional) - Filter by active status
     - `query` (optional) - Search query for knowledge bases

### Category Management

1. **create_category** - Create a new category in a knowledge base
   - Parameters:
     - `title` - Title of the category
     - `description` (optional) - Description of the category
     - `knowledge_base` - The knowledge base to create the category in
     - `parent_category` (optional) - Parent category (if creating a subcategory)
     - `active` (optional, default: true) - Whether the category is active

2. **list_categories** - List categories in a knowledge base
   - Parameters:
     - `knowledge_base` (optional) - Filter by knowledge base ID
     - `parent_category` (optional) - Filter by parent category ID
     - `limit` (optional, default: 10) - Maximum number of categories to return
     - `offset` (optional, default: 0) - Offset for pagination
     - `active` (optional) - Filter by active status
     - `query` (optional) - Search query for categories

### Article Management

1. **create_article** - Create a new knowledge article
   - Parameters:
     - `title` - Title of the article
     - `text` - The main body text for the article
     - `short_description` - Short description of the article
     - `knowledge_base` - The knowledge base to create the article in
     - `category` - Category for the article
     - `keywords` (optional) - Keywords for search
     - `article_type` (optional, default: "text") - The type of article

2. **update_article** - Update an existing knowledge article
   - Parameters:
     - `article_id` - ID of the article to update
     - `title` (optional) - Updated title of the article
     - `text` (optional) - Updated main body text for the article
     - `short_description` (optional) - Updated short description
     - `category` (optional) - Updated category for the article
     - `keywords` (optional) - Updated keywords for search

3. **publish_article** - Publish a knowledge article
   - Parameters:
     - `article_id` - ID of the article to publish
     - `workflow_state` (optional, default: "published") - The workflow state to set
     - `workflow_version` (optional) - The workflow version to use

4. **list_articles** - List knowledge articles with filtering options
   - Parameters:
     - `limit` (optional, default: 10) - Maximum number of articles to return
     - `offset` (optional, default: 0) - Offset for pagination
     - `knowledge_base` (optional) - Filter by knowledge base
     - `category` (optional) - Filter by category
     - `query` (optional) - Search query for articles
     - `workflow_state` (optional) - Filter by workflow state

5. **get_article** - Get a specific knowledge article by ID
   - Parameters:
     - `article_id` - ID of the article to get

## Example Usage

### Creating a Knowledge Base

```python
response = create_knowledge_base({
    "title": "Healthcare IT Knowledge Base",
    "description": "Knowledge base for healthcare IT resources and documentation",
    "owner": "healthcare_admins"
})
print(f"Knowledge base created with ID: {response['kb_id']}")
```

### Listing Knowledge Bases

```python
response = list_knowledge_bases({
    "active": True,
    "query": "IT",
    "limit": 20
})
print(f"Found {response['count']} knowledge bases")
for kb in response['knowledge_bases']:
    print(f"- {kb['title']}")
```

### Creating a Category

```python
response = create_category({
    "title": "Network Configuration",
    "description": "Articles related to network configuration in healthcare environments",
    "knowledge_base": "healthcare_kb"
})
print(f"Category created with ID: {response['category_id']}")
```

### Creating an Article

```python
response = create_article({
    "title": "VPN Setup for Remote Clinicians",
    "short_description": "Step-by-step guide for setting up VPN access for remote clinicians",
    "text": "# VPN Setup Guide\n\n1. Install the VPN client...",
    "knowledge_base": "healthcare_kb",
    "category": "network_config",
    "keywords": "vpn, remote access, clinicians, setup"
})
print(f"Article created with ID: {response['article_id']}")
```

### Updating an Article

```python
response = update_article({
    "article_id": "kb0010001",
    "text": "# Updated VPN Setup Guide\n\n1. Download the latest VPN client...",
    "keywords": "vpn, remote access, clinicians, setup, configuration"
})
print(f"Article updated: {response['success']}")
```

### Publishing an Article

```python
response = publish_article({
    "article_id": "kb0010001"
})
print(f"Article published: {response['success']}")
```

### Listing Articles

```python
response = list_articles({
    "knowledge_base": "healthcare_kb",
    "category": "network_config",
    "limit": 20
})
print(f"Found {response['count']} articles")
for article in response['articles']:
    print(f"- {article['title']}")
```

### Getting Article Details

```python
response = get_article({
    "article_id": "kb0010001"
})
article = response['article']
print(f"Title: {article['title']}")
print(f"Category: {article['category']}")
print(f"Views: {article['views']}")
```

### Listing Categories

```python
response = list_categories({
    "knowledge_base": "healthcare_kb",
    "active": True,
    "limit": 20
})
print(f"Found {response['count']} categories")
for category in response['categories']:
    print(f"- {category['title']}")
```

## ServiceNow API Endpoints

The Knowledge Base tools use the following ServiceNow API endpoints:

- `/table/kb_knowledge_base` - Knowledge base table API
- `/table/kb_category` - Category table API
- `/table/kb_knowledge` - Knowledge article table API

## Error Handling

All knowledge base tools handle errors gracefully and return responses with `success` and `message` fields. If an operation fails, the `success` field will be `false` and the `message` field will contain information about the error.

## Additional Information

For more information about knowledge management in ServiceNow, see the [ServiceNow Knowledge Management documentation](https://docs.servicenow.com/bundle/tokyo-servicenow-platform/page/product/knowledge-management/concept/c_KnowledgeManagement.html).