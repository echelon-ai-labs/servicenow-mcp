# Access Control & Security Management

This document describes the Access Control List (ACL) and Security management tools available in the ServiceNow MCP server.

## Overview

The Access Control & Security toolchain provides comprehensive management of:
- **Access Control Lists (ACLs)** - Control record and field-level access
- **Roles** - Define and manage user roles
- **Security Attributes** - Configure security attribute settings

## Available Tools

### Access Control Lists (ACLs)

#### 1. List ACLs
```python
list_acls(
    limit=10,
    offset=0,
    table_name="incident",  # Optional: Filter by table
    operation="read",  # Optional: read, write, create, delete
    active=True,  # Optional: Filter by active status
    query="admin"  # Optional: Search query
)
```

**Returns**: List of ACLs with sys_id, name, type, operation, description, active status, admin_overrides, script, created_on, and updated_on.

#### 2. Get ACL
```python
get_acl(
    acl_id="<sys_id>"  # ACL sys_id
)
```

**Returns**: Detailed information about a specific ACL.

#### 3. Create ACL
```python
create_acl(
    name="incident.read",
    type="record",  # record, field, etc.
    operation="read",  # read, write, create, delete
    description="Control read access to incidents",
    script="gs.hasRole('itil')",  # Optional: evaluation script
    active=True,
    admin_overrides=False  # Whether admin role overrides this ACL
)
```

**Returns**: Created ACL details with sys_id.

#### 4. Update ACL
```python
update_acl(
    acl_id="<sys_id>",
    name="incident.read",  # Optional
    description="Updated description",  # Optional
    script="gs.hasRole('itil') || gs.hasRole('admin')",  # Optional
    active=True,  # Optional
    admin_overrides=True  # Optional
)
```

**Returns**: Updated ACL details.

#### 5. Delete ACL
```python
delete_acl(
    acl_id="<sys_id>"
)
```

**Returns**: Confirmation of deletion.

### Roles Management

#### 1. List Roles
```python
list_roles_security(
    limit=10,
    offset=0,
    query="admin",  # Optional: Search query
    active=True  # Optional: Filter by active status
)
```

**Returns**: List of roles with sys_id, name, description, elevated_privilege, requires_subscription, and created_on.

#### 2. Get Role
```python
get_role(
    role_id="admin"  # Role sys_id or name
)
```

**Returns**: Detailed information about a specific role.

#### 3. Create Role
```python
create_role(
    name="custom_role",
    description="Custom role for specific access",
    requires_subscription="",  # Optional: Subscription requirement
    elevated_privilege=False  # Whether this is an elevated privilege role
)
```

**Returns**: Created role details with sys_id.

#### 4. Update Role
```python
update_role(
    role_id="<sys_id>",
    name="custom_role_updated",  # Optional
    description="Updated description",  # Optional
    requires_subscription="",  # Optional
    elevated_privilege=False  # Optional
)
```

**Returns**: Updated role details.

### Security Attributes

#### 1. List Security Attributes
```python
list_security_attributes(
    limit=10,
    offset=0,
    query="data"  # Optional: Search query
)
```

**Returns**: List of security attributes with sys_id, name, description, type, and created_on.

#### 2. Create Security Attribute
```python
create_security_attribute(
    name="data_classification",
    description="Data classification attribute",
    type="string"  # Type of the attribute
)
```

**Returns**: Created security attribute details with sys_id.

## Use Cases

### 1. Audit ACLs for a Specific Table
```python
# List all ACLs for the incident table
acls = list_acls(
    table_name="incident",
    limit=50
)

# Review each ACL
for acl in acls['acls']:
    print(f"ACL: {acl['name']}")
    print(f"  Operation: {acl['operation']}")
    print(f"  Active: {acl['active']}")
    print(f"  Script: {acl['script']}")
```

### 2. Create Custom Role with Specific Access
```python
# Create a custom role
role = create_role(
    name="custom_incident_manager",
    description="Custom role for incident management",
    elevated_privilege=False
)

# Create ACL that uses this role
acl = create_acl(
    name="incident.write.custom",
    type="record",
    operation="write",
    script=f"gs.hasRole('{role['data']['name']}')",
    description="Allow custom incident managers to write incidents"
)
```

### 3. Review Role Permissions
```python
# List all roles
roles = list_roles_security(limit=100)

# Get details for specific role
admin_role = get_role(role_id="admin")

# List ACLs that reference this role
acls = list_acls(query=admin_role['data']['name'], limit=50)
```

### 4. Temporarily Disable ACLs
```python
# Get ACL to disable
acl = get_acl(acl_id="<sys_id>")

# Disable the ACL
update_acl(
    acl_id=acl['data']['sys_id'],
    active=False
)

# Re-enable later
update_acl(
    acl_id=acl['data']['sys_id'],
    active=True
)
```

### 5. Security Attribute Management
```python
# Create security attributes for data classification
attributes = [
    {"name": "public", "description": "Public data"},
    {"name": "internal", "description": "Internal use only"},
    {"name": "confidential", "description": "Confidential data"},
    {"name": "restricted", "description": "Restricted access"}
]

for attr in attributes:
    create_security_attribute(
        name=attr['name'],
        description=attr['description'],
        type="string"
    )

# List all security attributes
all_attributes = list_security_attributes(limit=50)
```

## Security Best Practices

### 1. ACL Design
- **Principle of Least Privilege**: Grant minimum required access
- **Clear Naming**: Use descriptive names like `table.operation.description`
- **Documentation**: Always add descriptions to ACLs
- **Test Scripts**: Thoroughly test ACL scripts before activation

### 2. Role Management
- **Role Hierarchy**: Use role inheritance where appropriate
- **Granular Roles**: Create specific roles rather than broad permissions
- **Regular Audits**: Periodically review role assignments
- **Elevated Privileges**: Mark admin roles with elevated_privilege flag

### 3. ACL Scripts
```javascript
// Good: Check for specific role
gs.hasRole('itil')

// Good: Check for multiple roles
gs.hasRole('itil') || gs.hasRole('admin')

// Good: Check for role and additional condition
gs.hasRole('itil') && current.assigned_to == gs.getUserID()

// Avoid: Complex logic that's hard to audit
// Keep scripts simple and readable
```

### 4. Security Attributes
- Use security attributes for data classification
- Apply attributes consistently across tables
- Document attribute meanings clearly
- Review attribute usage regularly

## Common ACL Patterns

### 1. Read Access Control
```python
create_acl(
    name="incident.read.restricted",
    type="record",
    operation="read",
    script="gs.hasRole('itil') || gs.hasRole('admin')"
)
```

### 2. Write Access Control
```python
create_acl(
    name="incident.write.assigned",
    type="record",
    operation="write",
    script="current.assigned_to == gs.getUserID() || gs.hasRole('incident_manager')"
)
```

### 3. Field-Level Security
```python
create_acl(
    name="incident.priority.write",
    type="field",
    operation="write",
    script="gs.hasRole('incident_manager') || gs.hasRole('admin')",
    description="Only managers can change incident priority"
)
```

### 4. Create Access Control
```python
create_acl(
    name="incident.create.all",
    type="record",
    operation="create",
    script="gs.hasRole('itil')",
    description="ITIL role required to create incidents"
)
```

### 5. Delete Access Control
```python
create_acl(
    name="incident.delete.admin",
    type="record",
    operation="delete",
    script="gs.hasRole('admin')",
    description="Only admins can delete incidents"
)
```

## ServiceNow Tables Referenced

- **sys_security_acl** - Access Control Lists
- **sys_user_role** - User Roles
- **sys_security_attribute** - Security Attributes

## Response Formats

### ACL Response
```json
{
  "success": true,
  "message": "ACL created successfully: incident.read",
  "data": {
    "sys_id": "abc123...",
    "name": "incident.read",
    "type": "record",
    "operation": "read"
  }
}
```

### ACL List Response
```json
{
  "success": true,
  "message": "Found 5 ACLs",
  "acls": [
    {
      "sys_id": "abc123...",
      "name": "incident.read",
      "type": "record",
      "operation": "read",
      "description": "Read access to incidents",
      "active": "true",
      "admin_overrides": "false",
      "script": "gs.hasRole('itil')",
      "created_on": "2024-01-15 10:30:00",
      "updated_on": "2024-01-15 10:30:00"
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

### Role Response
```json
{
  "success": true,
  "message": "Retrieved role: admin",
  "data": {
    "sys_id": "def456...",
    "name": "admin",
    "description": "Administrator role",
    "elevated_privilege": "true",
    "requires_subscription": ""
  }
}
```

## Error Handling

All tools return error information in the response:

```json
{
  "success": false,
  "message": "Failed to create ACL: Permission denied",
  "data": null
}
```

Common errors:
- **Permission denied**: User lacks required permissions
- **Invalid script**: ACL script contains syntax errors
- **Duplicate name**: ACL with same name already exists
- **Invalid operation**: Operation not supported for ACL type

## Notes

- **Admin Privileges**: Most ACL operations require admin or security_admin role
- **Testing**: Always test ACLs in a non-production environment first
- **Performance**: Complex ACL scripts can impact system performance
- **Inheritance**: ACLs can be inherited based on table hierarchy
- **Evaluation Order**: ACLs are evaluated in specific order (most restrictive first)
- **Debugging**: Use ACL debugging tools in ServiceNow to troubleshoot issues

## Related Documentation

- [User Management](user_management.md)
- [Workflow Management](workflow_management.md)
- [ServiceNow ACL Documentation](https://docs.servicenow.com/bundle/latest/page/administer/security/concept/access-control-rules.html)
