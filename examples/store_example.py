"""
Example demonstrating MutableMapping (store) to MCP conversion.

This shows how to automatically expose CRUD operations for any
dict-like object using py2mcp.

To run:
    python examples/store_example.py
"""

from py2mcp import mk_mcp_from_store


# Example 1: Simple project store
projects = {
    'proj1': {
        'name': 'Website Redesign',
        'status': 'active',
        'team_size': 5
    },
    'proj2': {
        'name': 'Mobile App',
        'status': 'planning',
        'team_size': 3
    },
    'proj3': {
        'name': 'API Integration',
        'status': 'completed',
        'team_size': 2
    }
}

# Create MCP server from the store
# This automatically generates:
#   - list_projects() -> list all project keys
#   - get_project(key) -> get a project by key
#   - set_project(key, value) -> create or update a project
#   - delete_project(key) -> remove a project
mcp = mk_mcp_from_store(projects, name='project')


if __name__ == '__main__':
    print("Starting MCP server with project store...")
    print("\nAvailable tools:")
    print("  - list_projects: List all project IDs")
    print("  - get_project: Get a project by ID")
    print("  - set_project: Create or update a project")
    print("  - delete_project: Delete a project")
    print("\nExample usage:")
    print("  list_projects()")
    print("  get_project('proj1')")
    print("  set_project('proj4', {'name': 'New Project', 'status': 'planning'})")
    print("  delete_project('proj3')")
    mcp.run()
