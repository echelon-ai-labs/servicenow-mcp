#!/usr/bin/env python3
"""
Workflow Management Demo

This script demonstrates how to use the ServiceNow MCP workflow management tools
to view, create, and modify workflows in ServiceNow.
"""

import os
import sys
import json
from datetime import datetime

from dotenv import load_dotenv

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig
from servicenow_mcp.tools.workflow_tools import (
    list_workflows,
    get_workflow_details,
    list_workflow_versions,
    get_workflow_activities,
    create_workflow,
    update_workflow,
    activate_workflow,
    deactivate_workflow,
    add_workflow_activity,
    update_workflow_activity,
    reorder_workflow_activities,
)


def print_json(data):
    """Print JSON data in a readable format."""
    print(json.dumps(data, indent=2))


def main():
    """Main function to demonstrate workflow management tools."""
    # Load environment variables from .env file
    load_dotenv()

    # Get ServiceNow credentials from environment variables
    instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")

    if not all([instance_url, username, password]):
        print("Error: Missing required environment variables.")
        print("Please set SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, and SERVICENOW_PASSWORD.")
        sys.exit(1)

    # Create authentication configuration
    auth_config = AuthConfig(
        type=AuthType.BASIC,
        basic=BasicAuthConfig(username=username, password=password),
    )

    # Create server configuration
    server_config = ServerConfig(
        instance_url=instance_url,
        auth=auth_config,
    )

    # Create authentication manager
    auth_manager = AuthManager(auth_config)

    print("ServiceNow Workflow Management Demo")
    print("===================================")
    print(f"Instance URL: {instance_url}")
    print(f"Username: {username}")
    print()

    # List active workflows
    print("Listing active workflows...")
    workflows_result = list_workflows(
        auth_manager,
        server_config,
        {
            "limit": 5,
            "active": True,
        },
    )
    print_json(workflows_result)
    print()

    # Check if we have any workflows
    if workflows_result.get("count", 0) == 0:
        print("No active workflows found. Creating a new workflow...")
        
        # Create a new workflow
        new_workflow_result = create_workflow(
            auth_manager,
            server_config,
            {
                "name": f"Demo Workflow {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "description": "A demo workflow created by the ServiceNow MCP workflow management demo",
                "table": "incident",
                "active": True,
            },
        )
        print_json(new_workflow_result)
        print()
        
        if "error" in new_workflow_result:
            print("Error creating workflow. Exiting.")
            sys.exit(1)
            
        workflow_id = new_workflow_result["workflow"]["sys_id"]
    else:
        # Use the first workflow from the list
        workflow_id = workflows_result["workflows"][0]["sys_id"]
        
    print(f"Using workflow with ID: {workflow_id}")
    print()
    
    # Get workflow details
    print("Getting workflow details...")
    workflow_details = get_workflow_details(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
        },
    )
    print_json(workflow_details)
    print()
    
    # List workflow versions
    print("Listing workflow versions...")
    versions_result = list_workflow_versions(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
            "limit": 5,
        },
    )
    print_json(versions_result)
    print()
    
    # Get workflow activities
    print("Getting workflow activities...")
    activities_result = get_workflow_activities(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
        },
    )
    print_json(activities_result)
    print()
    
    # Add a new activity to the workflow
    print("Adding a new approval activity to the workflow...")
    add_activity_result = add_workflow_activity(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
            "name": f"Demo Approval {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "description": "A demo approval activity",
            "activity_type": "approval",
        },
    )
    print_json(add_activity_result)
    print()
    
    if "error" in add_activity_result:
        print("Error adding activity. Skipping activity modification steps.")
    else:
        activity_id = add_activity_result["activity"]["sys_id"]
        
        # Update the activity
        print("Updating the activity...")
        update_activity_result = update_workflow_activity(
            auth_manager,
            server_config,
            {
                "activity_id": activity_id,
                "name": f"Updated Demo Approval {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "description": "An updated demo approval activity",
            },
        )
        print_json(update_activity_result)
        print()
        
        # Get the updated activities
        print("Getting updated workflow activities...")
        updated_activities_result = get_workflow_activities(
            auth_manager,
            server_config,
            {
                "workflow_id": workflow_id,
            },
        )
        print_json(updated_activities_result)
        print()
        
        # If there are multiple activities, reorder them
        if updated_activities_result.get("count", 0) > 1:
            print("Reordering workflow activities...")
            activity_ids = [activity["sys_id"] for activity in updated_activities_result["activities"]]
            # Reverse the order
            activity_ids.reverse()
            
            reorder_result = reorder_workflow_activities(
                auth_manager,
                server_config,
                {
                    "workflow_id": workflow_id,
                    "activity_ids": activity_ids,
                },
            )
            print_json(reorder_result)
            print()
            
            # Get the reordered activities
            print("Getting reordered workflow activities...")
            reordered_activities_result = get_workflow_activities(
                auth_manager,
                server_config,
                {
                    "workflow_id": workflow_id,
                },
            )
            print_json(reordered_activities_result)
            print()
    
    # Update the workflow
    print("Updating the workflow...")
    update_result = update_workflow(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
            "description": f"Updated description {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
    )
    print_json(update_result)
    print()
    
    # Deactivate the workflow
    print("Deactivating the workflow...")
    deactivate_result = deactivate_workflow(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
        },
    )
    print_json(deactivate_result)
    print()
    
    # Activate the workflow
    print("Activating the workflow...")
    activate_result = activate_workflow(
        auth_manager,
        server_config,
        {
            "workflow_id": workflow_id,
        },
    )
    print_json(activate_result)
    print()
    
    print("Workflow management demo completed successfully!")


if __name__ == "__main__":
    main() 