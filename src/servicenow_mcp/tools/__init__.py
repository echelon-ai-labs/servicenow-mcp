"""
Tools module for the ServiceNow MCP server.
"""

# Import tools as they are implemented
from servicenow_mcp.tools.catalog_optimization import (
    get_optimization_recommendations,
    update_catalog_item,
)
from servicenow_mcp.tools.catalog_tools import (
    create_catalog_category,
    get_catalog_item,
    list_catalog_categories,
    list_catalog_items,
    move_catalog_items,
    update_catalog_category,
)
from servicenow_mcp.tools.catalog_variables import (
    create_catalog_item_variable,
    list_catalog_item_variables,
    update_catalog_item_variable,
)
from servicenow_mcp.tools.change_tools import (
    add_change_task,
    approve_change,
    create_change_request,
    get_change_request_details,
    list_change_requests,
    reject_change,
    submit_change_for_approval,
    update_change_request,
)
from servicenow_mcp.tools.changeset_tools import (
    add_file_to_changeset,
    commit_changeset,
    create_changeset,
    get_changeset_details,
    list_changesets,
    publish_changeset,
    update_changeset,
)
from servicenow_mcp.tools.incident_tools import (
    add_comment,
    create_incident,
    list_incidents,
    resolve_incident,
    update_incident,
)
from servicenow_mcp.tools.knowledge_base import (
    create_article,
    create_category,
    create_knowledge_base,
    get_article,
    list_articles,
    list_knowledge_bases,
    publish_article,
    update_article,
    list_categories,
)
from servicenow_mcp.tools.script_include_tools import (
    create_script_include,
    delete_script_include,
    get_script_include,
    list_script_includes,
    update_script_include,
)
from servicenow_mcp.tools.user_tools import (
    create_user,
    update_user,
    get_user,
    list_users,
    create_group,
    update_group,
    add_group_members,
    remove_group_members,
    list_groups,
)
from servicenow_mcp.tools.workflow_tools import (
    activate_workflow,
    add_workflow_activity,
    create_workflow,
    deactivate_workflow,
    delete_workflow_activity,
    get_workflow_activities,
    get_workflow_details,
    list_workflow_versions,
    list_workflows,
    reorder_workflow_activities,
    update_workflow,
    update_workflow_activity,
)
from servicenow_mcp.tools.story_tools import (
    create_story,
    update_story,
    list_stories,
    list_story_dependencies,
    create_story_dependency,
    delete_story_dependency,
)
from servicenow_mcp.tools.epic_tools import (
    create_epic,
    update_epic,
    list_epics,
)
from servicenow_mcp.tools.scrum_task_tools import (
    create_scrum_task,
    update_scrum_task,
    list_scrum_tasks,
)
from servicenow_mcp.tools.project_tools import (
    create_project,
    update_project,
    list_projects,
)
# from servicenow_mcp.tools.problem_tools import create_problem, update_problem
# from servicenow_mcp.tools.request_tools import create_request, update_request

__all__ = [
    # Incident tools
    "create_incident",
    "update_incident",
    "add_comment",
    "resolve_incident",
    "list_incidents",
    
    # Catalog tools
    "list_catalog_items",
    "get_catalog_item",
    "list_catalog_categories",
    "create_catalog_category",
    "update_catalog_category",
    "move_catalog_items",
    "get_optimization_recommendations",
    "update_catalog_item",
    "create_catalog_item_variable",
    "list_catalog_item_variables",
    "update_catalog_item_variable",
    
    # Change management tools
    "create_change_request",
    "update_change_request",
    "list_change_requests",
    "get_change_request_details",
    "add_change_task",
    "submit_change_for_approval",
    "approve_change",
    "reject_change",
    
    # Workflow management tools
    "list_workflows",
    "get_workflow_details",
    "list_workflow_versions",
    "get_workflow_activities",
    "create_workflow",
    "update_workflow",
    "activate_workflow",
    "deactivate_workflow",
    "add_workflow_activity",
    "update_workflow_activity",
    "delete_workflow_activity",
    "reorder_workflow_activities",
    
    # Changeset tools
    "list_changesets",
    "get_changeset_details",
    "create_changeset",
    "update_changeset",
    "commit_changeset",
    "publish_changeset",
    "add_file_to_changeset",
    
    # Script Include tools
    "list_script_includes",
    "get_script_include",
    "create_script_include",
    "update_script_include",
    "delete_script_include",
    
    # Knowledge Base tools
    "create_knowledge_base",
    "list_knowledge_bases",
    "create_category",
    "list_categories",
    "create_article",
    "update_article",
    "publish_article",
    "list_articles",
    "get_article",
    
    # User management tools
    "create_user",
    "update_user",
    "get_user",
    "list_users",
    "create_group",
    "update_group",
    "add_group_members",
    "remove_group_members",
    "list_groups",

    # Story tools
    "create_story",
    "update_story",
    "list_stories",
    "list_story_dependencies",
    "create_story_dependency",
    "delete_story_dependency",
    
    # Epic tools
    "create_epic",
    "update_epic",
    "list_epics",

    # Scrum Task tools
    "create_scrum_task",
    "update_scrum_task",
    "list_scrum_tasks",

    # Project tools
    "create_project",
    "update_project",
    "list_projects",

    
    # Future tools
    # "create_problem",
    # "update_problem",
    # "create_request",
    # "update_request",
] 