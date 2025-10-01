import os
import contextvars

# TFL_HOME_DIR
if "TFL_HOME_DIR" in os.environ:
    HOME_DIR = os.environ["TFL_HOME_DIR"]
    if not os.path.exists(HOME_DIR):
        print(f"Error: Home directory {HOME_DIR} does not exist")
        exit(1)
    print(f"Home directory is set to: {HOME_DIR}")
else:
    HOME_DIR = os.path.join(os.path.expanduser("~"), ".transformerlab")
    os.makedirs(name=HOME_DIR, exist_ok=True)
    print(f"Using default home directory: {HOME_DIR}")

# Context var for organization id (set by host app/session)
_current_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_org_id", default=None)


def set_organization_id(organization_id: str | None) -> None:
    _current_org_id.set(organization_id)


def get_workspace_dir() -> str:
    # Explicit override wins
    if "TFL_WORKSPACE_DIR" in os.environ:
        value = os.environ["TFL_WORKSPACE_DIR"]
        if not os.path.exists(value):
            print(f"Error: Workspace directory {value} does not exist")
            exit(1)
        return value

    org_id = _current_org_id.get()
    if org_id:
        path = os.path.join(HOME_DIR, "orgs", org_id, "workspace")
        os.makedirs(name=path, exist_ok=True)
        return path

    # Default single-tenant path
    path = os.path.join(HOME_DIR, "workspace")
    os.makedirs(name=path, exist_ok=True)
    return path


# Legacy constant for backward compatibility
WORKSPACE_DIR = get_workspace_dir()
