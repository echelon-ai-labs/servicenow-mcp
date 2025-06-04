"""
Knowledge base tools for the ServiceNow MCP server.

This module provides tools for managing knowledge bases, categories, and articles in ServiceNow.
"""

import logging
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class CreateKnowledgeBaseParams(BaseModel):
    """Parameters for creating a knowledge base."""

    title: str = Field(..., description="Title of the knowledge base")
    description: Optional[str] = Field(None, description="Description of the knowledge base")
    owner: Optional[str] = Field(None, description="The specified admin user or group")
    managers: Optional[str] = Field(None, description="Users who can manage this knowledge base")
    publish_workflow: Optional[str] = Field("Knowledge - Instant Publish", description="Publication workflow")
    retire_workflow: Optional[str] = Field("Knowledge - Instant Retire", description="Retirement workflow")


class ListKnowledgeBasesParams(BaseModel):
    """Parameters for listing knowledge bases."""
    
    limit: int = Field(10, description="Maximum number of knowledge bases to return")
    offset: int = Field(0, description="Offset for pagination")
    active: Optional[bool] = Field(None, description="Filter by active status")
    query: Optional[str] = Field(None, description="Search query for knowledge bases")


class CreateCategoryParams(BaseModel):
    """Parameters for creating a category in a knowledge base."""

    title: str = Field(..., description="Title of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    knowledge_base: str = Field(..., description="The knowledge base to create the category in")
    parent_category: Optional[str] = Field(None, description="Parent category (if creating a subcategory). Sys_id refering to the parent category or sys_id of the parent table.")
    parent_table: Optional[str] = Field(None, description="Parent table (if creating a subcategory). Sys_id refering to the table where the parent category is defined.")
    active: bool = Field(True, description="Whether the category is active")


class CreateArticleParams(BaseModel):
    """Parameters for creating a knowledge article."""

    title: str = Field(..., description="Title of the article")
    text: str = Field(..., description="The main body text for the article. Field supports html formatting and wiki markup based on the article_type. HTML is the default.")
    short_description: str = Field(..., description="Short description of the article")
    knowledge_base: str = Field(..., description="The knowledge base to create the article in")
    category: str = Field(..., description="Category for the article")
    keywords: Optional[str] = Field(None, description="Keywords for search")
    article_type: Optional[str] = Field("html", description="The type of article. Options are 'text' or 'wiki'. text lets the text field support html formatting. wiki lets the text field support wiki markup.")


class UpdateArticleParams(BaseModel):
    """Parameters for updating a knowledge article."""

    article_id: str = Field(..., description="ID of the article to update")
    title: Optional[str] = Field(None, description="Updated title of the article")
    text: Optional[str] = Field(None, description="Updated main body text for the article. Field supports html formatting and wiki markup based on the article_type. HTML is the default.")
    short_description: Optional[str] = Field(None, description="Updated short description")
    category: Optional[str] = Field(None, description="Updated category for the article")
    keywords: Optional[str] = Field(None, description="Updated keywords for search")


class PublishArticleParams(BaseModel):
    """Parameters for publishing a knowledge article."""

    article_id: str = Field(..., description="ID of the article to publish")
    workflow_state: Optional[str] = Field("published", description="The workflow state to set")
    workflow_version: Optional[str] = Field(None, description="The workflow version to use")


class ListArticlesParams(BaseModel):
    """Parameters for listing knowledge articles."""
    
    limit: int = Field(10, description="Maximum number of articles to return")
    offset: int = Field(0, description="Offset for pagination")
    knowledge_base: Optional[str] = Field(None, description="Filter by knowledge base")
    category: Optional[str] = Field(None, description="Filter by category")
    query: Optional[str] = Field(None, description="Search query for articles")
    workflow_state: Optional[str] = Field(None, description="Filter by workflow state")


class GetArticleParams(BaseModel):
    """Parameters for getting a knowledge article."""

    article_id: str = Field(..., description="ID of the article to get")


class KnowledgeBaseResponse(BaseModel):
    """Response from knowledge base operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    kb_id: Optional[str] = Field(None, description="ID of the affected knowledge base")
    kb_name: Optional[str] = Field(None, description="Name of the affected knowledge base")


class CategoryResponse(BaseModel):
    """Response from category operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    category_id: Optional[str] = Field(None, description="ID of the affected category")
    category_name: Optional[str] = Field(None, description="Name of the affected category")


class ArticleResponse(BaseModel):
    """Response from article operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    article_id: Optional[str] = Field(None, description="ID of the affected article")
    article_title: Optional[str] = Field(None, description="Title of the affected article")
    workflow_state: Optional[str] = Field(None, description="Current workflow state of the article")


class ListCategoriesParams(BaseModel):
    """Parameters for listing categories in a knowledge base."""
    
    knowledge_base: Optional[str] = Field(None, description="Filter by knowledge base ID")
    parent_category: Optional[str] = Field(None, description="Filter by parent category ID")
    limit: int = Field(10, description="Maximum number of categories to return")
    offset: int = Field(0, description="Offset for pagination")
    active: Optional[bool] = Field(None, description="Filter by active status")
    query: Optional[str] = Field(None, description="Search query for categories")


def create_knowledge_base(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateKnowledgeBaseParams,
) -> KnowledgeBaseResponse:
    """
    Create a new knowledge base in ServiceNow.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the knowledge base.

    Returns:
        Response with the created knowledge base details.
    """
    api_url = f"{config.api_url}/table/kb_knowledge_base"

    # Build request data
    data = {
        "title": params.title,
    }

    if params.description:
        data["description"] = params.description
    if params.owner:
        data["owner"] = params.owner
    if params.managers:
        data["kb_managers"] = params.managers
    if params.publish_workflow:
        data["workflow_publish"] = params.publish_workflow
    if params.retire_workflow:
        data["workflow_retire"] = params.retire_workflow

    # Make request
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return KnowledgeBaseResponse(
            success=True,
            message="Knowledge base created successfully",
            kb_id=result.get("sys_id"),
            kb_name=result.get("title"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create knowledge base: {e}")
        return KnowledgeBaseResponse(
            success=False,
            message=f"Failed to create knowledge base: {str(e)}",
        )


def list_knowledge_bases(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListKnowledgeBasesParams,
) -> Dict[str, Any]:
    """
    List knowledge bases with filtering options.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing knowledge bases.

    Returns:
        Dictionary with list of knowledge bases and metadata.
    """
    api_url = f"{config.api_url}/table/kb_knowledge_base"

    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
    }

    # Build query string
    query_parts = []
    if params.active is not None:
        query_parts.append(f"active={str(params.active).lower()}")
    if params.query:
        query_parts.append(f"titleLIKE{params.query}^ORdescriptionLIKE{params.query}")

    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        # Get the JSON response 
        json_response = response.json()
        
        # Safely extract the result
        if isinstance(json_response, dict) and "result" in json_response:
            result = json_response.get("result", [])
        else:
            logger.error("Unexpected response format: %s", json_response)
            return {
                "success": False,
                "message": "Unexpected response format",
                "knowledge_bases": [],
                "count": 0,
                "limit": params.limit,
                "offset": params.offset,
            }

        # Transform the results - create a simpler structure
        knowledge_bases = []
        
        # Handle either string or list
        if isinstance(result, list):
            for kb_item in result:
                if not isinstance(kb_item, dict):
                    logger.warning("Skipping non-dictionary KB item: %s", kb_item)
                    continue
                    
                # Safely extract values
                kb_id = kb_item.get("sys_id", "")
                title = kb_item.get("title", "")
                description = kb_item.get("description", "")
                
                # Extract nested values safely
                owner = ""
                if isinstance(kb_item.get("owner"), dict):
                    owner = kb_item["owner"].get("display_value", "")
                
                managers = ""
                if isinstance(kb_item.get("kb_managers"), dict):
                    managers = kb_item["kb_managers"].get("display_value", "")
                
                active = False
                if kb_item.get("active") == "true":
                    active = True
                
                created = kb_item.get("sys_created_on", "")
                updated = kb_item.get("sys_updated_on", "")
                
                knowledge_bases.append({
                    "id": kb_id,
                    "title": title,
                    "description": description,
                    "owner": owner,
                    "managers": managers,
                    "active": active,
                    "created": created,
                    "updated": updated,
                })
        else:
            logger.warning("Result is not a list: %s", result)

        return {
            "success": True,
            "message": f"Found {len(knowledge_bases)} knowledge bases",
            "knowledge_bases": knowledge_bases,
            "count": len(knowledge_bases),
            "limit": params.limit,
            "offset": params.offset,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list knowledge bases: {e}")
        return {
            "success": False,
            "message": f"Failed to list knowledge bases: {str(e)}",
            "knowledge_bases": [],
            "count": 0,
            "limit": params.limit,
            "offset": params.offset,
        }


def create_category(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCategoryParams,
) -> CategoryResponse:
    """
    Create a new category in a knowledge base.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the category.

    Returns:
        Response with the created category details.
    """
    api_url = f"{config.api_url}/table/kb_category"

    # Build request data
    data = {
        "label": params.title,
        "kb_knowledge_base": params.knowledge_base,
        # Convert boolean to string "true"/"false" as ServiceNow expects
        "active": str(params.active).lower(),
    }

    if params.description:
        data["description"] = params.description
    if params.parent_category:
        data["parent"] = params.parent_category
    if params.parent_table:
        data["parent_table"] = params.parent_table
    
    # Log the request data for debugging
    logger.debug(f"Creating category with data: {data}")

    # Make request
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})
        logger.debug(f"Category creation response: {result}")

        # Log the specific fields to check the knowledge base assignment
        if "kb_knowledge_base" in result:
            logger.debug(f"Knowledge base in response: {result['kb_knowledge_base']}")
        
        # Log the active status
        if "active" in result:
            logger.debug(f"Active status in response: {result['active']}")
        
        return CategoryResponse(
            success=True,
            message="Category created successfully",
            category_id=result.get("sys_id"),
            category_name=result.get("label"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create category: {e}")
        return CategoryResponse(
            success=False,
            message=f"Failed to create category: {str(e)}",
        )


def create_article(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateArticleParams,
) -> ArticleResponse:
    """
    Create a new knowledge article.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for creating the article.

    Returns:
        Response with the created article details.
    """
    api_url = f"{config.api_url}/table/kb_knowledge"

    # Build request data
    data = {
        "short_description": params.short_description,
        "text": params.text,
        "kb_knowledge_base": params.knowledge_base,
        "kb_category": params.category,
        "article_type": params.article_type,
    }

    if params.title:
        data["short_description"] = params.title
    if params.keywords:
        data["keywords"] = params.keywords

    # Make request
    try:
        response = requests.post(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return ArticleResponse(
            success=True,
            message="Article created successfully",
            article_id=result.get("sys_id"),
            article_title=result.get("short_description"),
            workflow_state=result.get("workflow_state"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to create article: {e}")
        return ArticleResponse(
            success=False,
            message=f"Failed to create article: {str(e)}",
        )


def update_article(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateArticleParams,
) -> ArticleResponse:
    """
    Update an existing knowledge article.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for updating the article.

    Returns:
        Response with the updated article details.
    """
    api_url = f"{config.api_url}/table/kb_knowledge/{params.article_id}"

    # Build request data
    data = {}

    if params.title:
        data["short_description"] = params.title
    if params.text:
        data["text"] = params.text
    if params.short_description:
        data["short_description"] = params.short_description
    if params.category:
        data["kb_category"] = params.category
    if params.keywords:
        data["keywords"] = params.keywords

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return ArticleResponse(
            success=True,
            message="Article updated successfully",
            article_id=params.article_id,
            article_title=result.get("short_description"),
            workflow_state=result.get("workflow_state"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to update article: {e}")
        return ArticleResponse(
            success=False,
            message=f"Failed to update article: {str(e)}",
        )


def publish_article(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: PublishArticleParams,
) -> ArticleResponse:
    """
    Publish a knowledge article.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for publishing the article.

    Returns:
        Response with the published article details.
    """
    api_url = f"{config.api_url}/table/kb_knowledge/{params.article_id}"

    # Build request data
    data = {
        "workflow_state": params.workflow_state,
    }

    if params.workflow_version:
        data["workflow_version"] = params.workflow_version

    # Make request
    try:
        response = requests.patch(
            api_url,
            json=data,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        result = response.json().get("result", {})

        return ArticleResponse(
            success=True,
            message="Article published successfully",
            article_id=params.article_id,
            article_title=result.get("short_description"),
            workflow_state=result.get("workflow_state"),
        )

    except requests.RequestException as e:
        logger.error(f"Failed to publish article: {e}")
        return ArticleResponse(
            success=False,
            message=f"Failed to publish article: {str(e)}",
        )


def list_articles(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListArticlesParams,
) -> Dict[str, Any]:
    """
    List knowledge articles with filtering options.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing articles.

    Returns:
        Dictionary with list of articles and metadata.
    """
    api_url = f"{config.api_url}/table/kb_knowledge"

    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "all",
    }

    # Build query string
    query_parts = []
    if params.knowledge_base:
        query_parts.append(f"kb_knowledge_base.sys_id={params.knowledge_base}")
    if params.category:
        query_parts.append(f"kb_category.sys_id={params.category}")
    if params.workflow_state:
        query_parts.append(f"workflow_state={params.workflow_state}")
    if params.query:
        query_parts.append(f"short_descriptionLIKE{params.query}^ORtextLIKE{params.query}")

    if query_parts:
        query_string = "^".join(query_parts)
        logger.debug(f"Constructed article query string: {query_string}")
        query_params["sysparm_query"] = query_string
    
    # Log the query parameters for debugging
    logger.debug(f"Listing articles with query params: {query_params}")

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        # Get the JSON response
        json_response = response.json()
        logger.debug(f"Article listing raw response: {json_response}")
        
        # Safely extract the result
        if isinstance(json_response, dict) and "result" in json_response:
            result = json_response.get("result", [])
        else:
            logger.error("Unexpected response format: %s", json_response)
            return {
                "success": False,
                "message": f"Unexpected response format",
                "articles": [],
                "count": 0,
                "limit": params.limit,
                "offset": params.offset,
            }

        # Transform the results
        articles = []
        
        # Handle either string or list
        if isinstance(result, list):
            for article_item in result:
                if not isinstance(article_item, dict):
                    logger.warning("Skipping non-dictionary article item: %s", article_item)
                    continue
                    
                # Safely extract values
                article_id = article_item.get("sys_id", "")
                title = article_item.get("short_description", "")
                
                # Extract nested values safely
                knowledge_base = ""
                if isinstance(article_item.get("kb_knowledge_base"), dict):
                    knowledge_base = article_item["kb_knowledge_base"].get("display_value", "")
                
                category = ""
                if isinstance(article_item.get("kb_category"), dict):
                    category = article_item["kb_category"].get("display_value", "")
                
                workflow_state = ""
                if isinstance(article_item.get("workflow_state"), dict):
                    workflow_state = article_item["workflow_state"].get("display_value", "")
                
                created = article_item.get("sys_created_on", "")
                updated = article_item.get("sys_updated_on", "")
                
                articles.append({
                    "id": article_id,
                    "title": title,
                    "knowledge_base": knowledge_base,
                    "category": category,
                    "workflow_state": workflow_state,
                    "created": created,
                    "updated": updated,
                })
        else:
            logger.warning("Result is not a list: %s", result)

        return {
            "success": True,
            "message": f"Found {len(articles)} articles",
            "articles": articles,
            "count": len(articles),
            "limit": params.limit,
            "offset": params.offset,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list articles: {e}")
        return {
            "success": False,
            "message": f"Failed to list articles: {str(e)}",
            "articles": [],
            "count": 0,
            "limit": params.limit,
            "offset": params.offset,
        }


def get_article(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetArticleParams,
) -> Dict[str, Any]:
    """
    Get a specific knowledge article by ID.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for getting the article.

    Returns:
        Dictionary with article details.
    """
    api_url = f"{config.api_url}/table/kb_knowledge/{params.article_id}"

    # Build query parameters
    query_params = {
        "sysparm_display_value": "true",
    }

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        # Get the JSON response
        json_response = response.json()
        
        # Safely extract the result
        if isinstance(json_response, dict) and "result" in json_response:
            result = json_response.get("result", {})
        else:
            logger.error("Unexpected response format: %s", json_response)
            return {
                "success": False,
                "message": "Unexpected response format",
            }

        if not result or not isinstance(result, dict):
            return {
                "success": False,
                "message": f"Article with ID {params.article_id} not found",
            }

        # Extract values safely
        article_id = result.get("sys_id", "")
        title = result.get("short_description", "")
        text = result.get("text", "")
        
        # Extract nested values safely
        knowledge_base = ""
        if isinstance(result.get("kb_knowledge_base"), dict):
            knowledge_base = result["kb_knowledge_base"].get("display_value", "")
        
        category = ""
        if isinstance(result.get("kb_category"), dict):
            category = result["kb_category"].get("display_value", "")
        
        workflow_state = ""
        if isinstance(result.get("workflow_state"), dict):
            workflow_state = result["workflow_state"].get("display_value", "")
        
        author = ""
        if isinstance(result.get("author"), dict):
            author = result["author"].get("display_value", "")
        
        keywords = result.get("keywords", "")
        article_type = result.get("article_type", "")
        views = result.get("view_count", "0")
        created = result.get("sys_created_on", "")
        updated = result.get("sys_updated_on", "")

        article = {
            "id": article_id,
            "title": title,
            "text": text,
            "knowledge_base": knowledge_base,
            "category": category,
            "workflow_state": workflow_state,
            "created": created,
            "updated": updated,
            "author": author,
            "keywords": keywords,
            "article_type": article_type,
            "views": views,
        }

        return {
            "success": True,
            "message": "Article retrieved successfully",
            "article": article,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to get article: {e}")
        return {
            "success": False,
            "message": f"Failed to get article: {str(e)}",
        }


def list_categories(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCategoriesParams,
) -> Dict[str, Any]:
    """
    List categories in a knowledge base.

    Args:
        config: Server configuration.
        auth_manager: Authentication manager.
        params: Parameters for listing categories.

    Returns:
        Dictionary with list of categories and metadata.
    """
    api_url = f"{config.api_url}/table/kb_category"

    # Build query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "all",
    }

    # Build query string
    query_parts = []
    if params.knowledge_base:
        # Try different query format to ensure we match by sys_id value
        query_parts.append(f"kb_knowledge_base.sys_id={params.knowledge_base}")
    if params.parent_category:
        query_parts.append(f"parent.sys_id={params.parent_category}")
    if params.active is not None:
        query_parts.append(f"active={str(params.active).lower()}")
    if params.query:
        query_parts.append(f"labelLIKE{params.query}^ORdescriptionLIKE{params.query}")

    if query_parts:
        query_string = "^".join(query_parts)
        logger.debug(f"Constructed query string: {query_string}")
        query_params["sysparm_query"] = query_string
    
    # Log the query parameters for debugging
    logger.debug(f"Listing categories with query params: {query_params}")

    # Make request
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()

        # Get the JSON response
        json_response = response.json()
        
        # Safely extract the result
        if isinstance(json_response, dict) and "result" in json_response:
            result = json_response.get("result", [])
        else:
            logger.error("Unexpected response format: %s", json_response)
            return {
                "success": False,
                "message": "Unexpected response format",
                "categories": [],
                "count": 0,
                "limit": params.limit,
                "offset": params.offset,
            }

        # Transform the results
        categories = []
        
        # Handle either string or list
        if isinstance(result, list):
            for category_item in result:
                if not isinstance(category_item, dict):
                    logger.warning("Skipping non-dictionary category item: %s", category_item)
                    continue
                    
                # Safely extract values
                category_id = category_item.get("sys_id", "")
                title = category_item.get("label", "")
                description = category_item.get("description", "")
                
                # Extract knowledge base - handle both dictionary and string cases
                knowledge_base = ""
                kb_field = category_item.get("kb_knowledge_base")
                if isinstance(kb_field, dict):
                    knowledge_base = kb_field.get("display_value", "")
                elif isinstance(kb_field, str):
                    knowledge_base = kb_field
                # Also check if kb_knowledge_base is missing but there's a separate value field
                elif "kb_knowledge_base_value" in category_item:
                    knowledge_base = category_item.get("kb_knowledge_base_value", "")
                elif "kb_knowledge_base.display_value" in category_item:
                    knowledge_base = category_item.get("kb_knowledge_base.display_value", "")
                
                # Extract parent category - handle both dictionary and string cases
                parent = ""
                parent_field = category_item.get("parent")
                if isinstance(parent_field, dict):
                    parent = parent_field.get("display_value", "")
                elif isinstance(parent_field, str):
                    parent = parent_field
                # Also check alternative field names
                elif "parent_value" in category_item:
                    parent = category_item.get("parent_value", "")
                elif "parent.display_value" in category_item:
                    parent = category_item.get("parent.display_value", "")
                
                # Convert active to boolean - handle string or boolean types
                active_field = category_item.get("active")
                if isinstance(active_field, str):
                    active = active_field.lower() == "true"
                elif isinstance(active_field, bool):
                    active = active_field
                else:
                    active = False
                
                created = category_item.get("sys_created_on", "")
                updated = category_item.get("sys_updated_on", "")
                
                categories.append({
                    "id": category_id,
                    "title": title,
                    "description": description,
                    "knowledge_base": knowledge_base,
                    "parent_category": parent,
                    "active": active,
                    "created": created,
                    "updated": updated,
                })
                
                # Log for debugging purposes
                logger.debug(f"Processed category: {title}, KB: {knowledge_base}, Parent: {parent}")
        else:
            logger.warning("Result is not a list: %s", result)

        return {
            "success": True,
            "message": f"Found {len(categories)} categories",
            "categories": categories,
            "count": len(categories),
            "limit": params.limit,
            "offset": params.offset,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to list categories: {e}")
        return {
            "success": False,
            "message": f"Failed to list categories: {str(e)}",
            "categories": [],
            "count": 0,
            "limit": params.limit,
            "offset": params.offset,
        } 