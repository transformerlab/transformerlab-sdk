# Root dir is the parent of the parent of this current directory:

import os
import contextvars
from werkzeug.utils import secure_filename

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
_current_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_org_id", default=None
)


def set_organization_id(organization_id: str | None) -> None:
    _current_org_id.set(organization_id)


def get_workspace_dir() -> str:
    # Remote SkyPilot workspace override (highest precedence)
    # Only return container workspace path when value is exactly "true"
    if os.getenv("_TFL_REMOTE_SKYPILOT_WORKSPACE") == "true":
        return "/workspace"

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

"""
TFL_HOME_DIR is the directory that is the parent of the src and workspace directories.
By default, it is set to ~/.transformerlab

TFL_WORKSPACE_DIR is the directory where all the experiments, plugins, and models are stored.
By default, it is set to TFL_HOME_DIR/workspace

TFL_SOURCE_CODE_DIR is the directory where the source code is stored.
By default, it is set to TFL_HOME_DIR/src
This directory stores code but shouldn't store any data because it is erased and replaced
on updates.

You can set any of the above using environment parameters and it will override the defaults.

ROOT_DIR is a legacy variable that we should replace with the above, eventually.
"""

# FASTCHAT LOGDIR
os.environ["LOGDIR"] = os.getenv(
    "TFL_HOME_DIR", os.path.join(str(os.path.expanduser("~")), ".transformerlab")
)


def get_experiments_dir() -> str:
    path = os.path.join(get_workspace_dir(), "experiments")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_jobs_dir() -> str:
    workspace_dir = get_workspace_dir()
    path = os.path.join(workspace_dir, "jobs")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_global_log_path() -> str:
    return os.path.join(get_workspace_dir(), "transformerlab.log")


def get_logs_dir() -> str:
    path = os.path.join(HOME_DIR, "logs")
    os.makedirs(name=path, exist_ok=True)
    return path


# TODO: Move this to Experiment
def experiment_dir_by_name(experiment_name: str) -> str:
    experiments_dir = get_experiments_dir()
    return os.path.join(experiments_dir, experiment_name)


def get_plugin_dir() -> str:
    return os.path.join(get_workspace_dir(), "plugins")


def plugin_dir_by_name(plugin_name: str) -> str:
    plugin_name = secure_filename(plugin_name)
    return os.path.join(get_plugin_dir(), plugin_name)


def get_models_dir() -> str:
    path = os.path.join(get_workspace_dir(), "models")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_datasets_dir() -> str:
    path = os.path.join(get_workspace_dir(), "datasets")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_tasks_dir() -> str:
    path = os.path.join(get_workspace_dir(), "tasks")
    os.makedirs(name=path, exist_ok=True)
    return path


def dataset_dir_by_id(dataset_id: str) -> str:
    return os.path.join(get_datasets_dir(), dataset_id)


def get_temp_dir() -> str:
    path = os.path.join(get_workspace_dir(), "temp")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_prompt_templates_dir() -> str:
    path = os.path.join(get_workspace_dir(), "prompt_templates")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_tools_dir() -> str:
    path = os.path.join(get_workspace_dir(), "tools")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_batched_prompts_dir() -> str:
    path = os.path.join(get_workspace_dir(), "batched_prompts")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_galleries_cache_dir() -> str:
    path = os.path.join(get_workspace_dir(), "galleries")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_job_dir(job_id: str | int) -> str:
    """
    Return the filesystem directory for a specific job id under the jobs root.
    Mirrors `Job.get_dir()` but provided here for convenience where a `Job`
    instance is not readily available.
    """
    job_id_safe = secure_filename(str(job_id))
    return os.path.join(get_jobs_dir(), job_id_safe)


def get_job_artifacts_dir(job_id: str | int) -> str:
    """
    Return the artifacts directory for a specific job, creating it if needed.
    Example: ~/.transformerlab/workspace/jobs/<job_id>/artifacts
    """
    path = os.path.join(get_job_dir(job_id), "artifacts")
    os.makedirs(name=path, exist_ok=True)
    return path


def get_job_checkpoints_dir(job_id: str | int) -> str:
    """
    Return the checkpoints directory for a specific job, creating it if needed.
    Example: ~/.transformerlab/workspace/jobs/<job_id>/checkpoints
    """
    path = os.path.join(get_job_dir(job_id), "checkpoints")
    os.makedirs(name=path, exist_ok=True)
    return path


# Evals output file:
# TODO: These should probably be in the plugin subclasses


async def eval_output_file(experiment_name: str, eval_name: str) -> str:
    experiment_dir = experiment_dir_by_name(experiment_name)
    eval_name = secure_filename(eval_name)
    p = os.path.join(experiment_dir, "evals", eval_name)
    os.makedirs(p, exist_ok=True)
    return os.path.join(p, "output.txt")


async def generation_output_file(experiment_name: str, generation_name: str) -> str:
    experiment_dir = experiment_dir_by_name(experiment_name)
    generation_name = secure_filename(generation_name)
    p = os.path.join(experiment_dir, "generations", generation_name)
    os.makedirs(p, exist_ok=True)
    return os.path.join(p, "output.txt")
