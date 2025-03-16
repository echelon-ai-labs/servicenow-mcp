"""
Task resources for the ServiceNow MCP server.

This module provides resources for accessing task data from ServiceNow.
"""

import logging
from typing import Dict, List, Optional

from mcp.server.fastmcp.resources import Resource
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig


logger = logging.getLogger(__name__)


class TaskModel(BaseModel):
    """Model representing a ServiceNow task."""
    
    sys_id: str = Field(..., description="Unique identifier for the task")
    number: str = Field(..., description="Task number (e.g., TASK0010001)")
    short_description: str = Field(..., description="Short description of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    state: str = Field(..., description="Current state of the task")
    priority: Optional[str] = Field(None, description="Priority of the task")
    assigned_to: Optional[str] = Field(None, description="User assigned to the task")
    category: Optional[str] = Field(None, description="Category of the task")
    due_date: Optional[str] = Field(None, description="Due date for the task")
    created_on: str = Field(..., description="Date and time when the task was created")
    updated_on: str = Field(..., description="Date and time when the task was last updated")
    completed_on: Optional[str] = Field(None, description="Date and time when the task was completed")


class TaskListParams(BaseModel):
    """Parameters for listing tasks."""
    
    limit: int = Field(10, description="Maximum number of tasks to return")
    offset: int = Field(0, description="Offset for pagination")
    state: Optional[str] = Field(None, description="Filter by task state")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    category: Optional[str] = Field(None, description="Filter by category")
    query: Optional[str] = Field(None, description="Search query for tasks")


class TaskResource(Resource):
    """Resource for accessing ServiceNow tasks."""
    
    def __init__(self, config: ServerConfig, auth_manager: AuthManager):
        """
        Initialize the task resource.
        
        Args:
            config: Server configuration.
            auth_manager: Authentication manager.
        """
        # Use the instance URL from the configuration for the uri
        uri = f"{config.instance_url}/api/now/tasks"
        super().__init__(name="tasks", uri=uri)
        # Store config and auth_manager as private attributes
        self._config = config
        self._auth_manager = auth_manager
        self._api_url = f"{config.api_url}/table/task"
    
    async def read(self, params: dict = None) -> dict:
        """
        Read tasks from ServiceNow.
        
        This is the required method for the Resource abstract class.
        
        Args:
            params: Parameters for reading tasks.
            
        Returns:
            Dictionary with tasks data.
        """
        list_params = TaskListParams(**(params or {}))
        tasks = await self.list_tasks(list_params)
        return {"tasks": [task.dict() for task in tasks]}
    
    async def list_tasks(self, params: TaskListParams) -> List[TaskModel]:
        """
        List tasks from ServiceNow.
        
        Args:
            params: Parameters for listing tasks.
            
        Returns:
            List of tasks.
        """
        import requests
        
        # Build query parameters
        query_params = {
            "sysparm_limit": params.limit,
            "sysparm_offset": params.offset,
            "sysparm_display_value": "true",
            "sysparm_exclude_reference_link": "true",
        }
        
        # Add filters
        filters = []
        if params.state:
            filters.append(f"state={params.state}")
        if params.assigned_to:
            filters.append(f"assigned_to={params.assigned_to}")
        if params.category:
            filters.append(f"category={params.category}")
        if params.query:
            filters.append(f"short_descriptionLIKE{params.query}^ORdescriptionLIKE{params.query}")
        
        if filters:
            query_params["sysparm_query"] = "^".join(filters)
        
        # Make request
        try:
            response = requests.get(
                self._api_url,
                params=query_params,
                headers=self._auth_manager.get_headers(),
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            tasks = []
            
            for task_data in data.get("result", []):
                # Handle assigned_to field which could be a string or a dictionary
                assigned_to = task_data.get("assigned_to")
                if isinstance(assigned_to, dict):
                    assigned_to = assigned_to.get("display_value")
                
                task = TaskModel(
                    sys_id=task_data.get("sys_id"),
                    number=task_data.get("number"),
                    short_description=task_data.get("short_description"),
                    description=task_data.get("description"),
                    state=task_data.get("state"),
                    priority=task_data.get("priority"),
                    assigned_to=assigned_to,
                    category=task_data.get("category"),
                    due_date=task_data.get("due_date"),
                    created_on=task_data.get("sys_created_on"),
                    updated_on=task_data.get("sys_updated_on"),
                    completed_on=task_data.get("closed_at"),
                )
                tasks.append(task)
            
            return tasks
            
        except requests.RequestException as e:
            logger.error(f"Failed to list tasks: {e}")
            raise ValueError(f"Failed to list tasks: {e}")
    
    async def get_task(self, task_id: str) -> TaskModel:
        """
        Get a specific task from ServiceNow.
        
        Args:
            task_id: Task ID or sys_id.
            
        Returns:
            Task details.
        """
        import requests
        
        # Determine if task_id is a number or sys_id
        query_param = "sysparm_query=number=" + task_id
        if len(task_id) == 32 and all(c in "0123456789abcdef" for c in task_id):
            # This is likely a sys_id
            url = f"{self._api_url}/{task_id}"
            query_param = None
        else:
            # This is likely a task number
            url = self._api_url
        
        # Make request
        try:
            params = {
                "sysparm_display_value": "true",
                "sysparm_exclude_reference_link": "true",
            }
            
            if query_param:
                params["sysparm_query"] = query_param
            
            response = requests.get(
                url,
                params=params,
                headers=self._auth_manager.get_headers(),
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            
            if query_param:
                result = data.get("result", [])
                if not result:
                    raise ValueError(f"Task not found: {task_id}")
                task_data = result[0]
            else:
                task_data = data.get("result", {})
                if not task_data:
                    raise ValueError(f"Task not found: {task_id}")
            
            # Handle assigned_to field which could be a string or a dictionary
            assigned_to = task_data.get("assigned_to")
            if isinstance(assigned_to, dict):
                assigned_to = assigned_to.get("display_value")
            
            task = TaskModel(
                sys_id=task_data.get("sys_id"),
                number=task_data.get("number"),
                short_description=task_data.get("short_description"),
                description=task_data.get("description"),
                state=task_data.get("state"),
                priority=task_data.get("priority"),
                assigned_to=assigned_to,
                category=task_data.get("category"),
                due_date=task_data.get("due_date"),
                created_on=task_data.get("sys_created_on"),
                updated_on=task_data.get("sys_updated_on"),
                completed_on=task_data.get("closed_at"),
            )
            
            return task
            
        except requests.RequestException as e:
            logger.error(f"Failed to get task: {e}")
            raise ValueError(f"Failed to get task: {e}")
