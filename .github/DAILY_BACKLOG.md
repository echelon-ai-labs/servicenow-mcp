# Daily Improvement Backlog

## Queue (pick top item each day)
2. Implement list_syslog_entries tool (commented out in tool_packages.yaml as TODO)
3. Implement get_syslog_entry tool
4. Implement delete_catalog_item_variable tool
5. Implement create_catalog_variable_choice tool
6. Implement create_ui_policy tool
7. Implement create_ui_policy_action tool
8. Implement create_user_criteria tool
9. Implement create_user_criteria_condition tool
10. Implement execute_script_include tool
11. Add tests for changeset_tools.py (currently 73% coverage)
12. Add tests for auth_manager.py (currently 70% coverage)
13. Add tests for catalog_optimization.py (currently 78% coverage)
14. Improve error messages across all tools
15. Add input validation for date fields across tools
16. Add pagination helpers for list operations
17. Add bulk operations support
18. Add retry logic with exponential backoff for API calls
19. Add rate limiting awareness for ServiceNow API
20. Add request/response logging in debug mode

## Completed
- 2026-04-08: Extract duplicated helpers (_get_instance_url, _get_headers, _unwrap_and_validate_params) from 8 tool files into src/servicenow_mcp/utils/helpers.py
