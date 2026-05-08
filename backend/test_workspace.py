from workspace.manager import create_workspace, list_workspaces


ws = create_workspace("Test Workspace")
print(ws)

print(list_workspaces())
