# Root dir is the parent of the parent of this current directory:

import os
from . import dirs_workspace

from werkzeug.utils import secure_filename

WORKSPACE_DIR = dirs_workspace.WORKSPACE_DIR
HOME_DIR = dirs_workspace.HOME_DIR

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
os.environ["TLAB_LOG"] = "transformerlab.log"

# EXPERIMENTS_DIR
EXPERIMENTS_DIR: str = os.path.join(WORKSPACE_DIR, "experiments")
os.makedirs(name=EXPERIMENTS_DIR, exist_ok=True)

# JOBS DIR
JOBS_DIR = os.path.join(WORKSPACE_DIR, "jobs")
os.makedirs(name=JOBS_DIR, exist_ok=True)

# GLOBAL_LOG_PATH
# MTMIGRATE: This doesn't work in multi-tenant world
GLOBAL_LOG_PATH = os.path.join(HOME_DIR, "transformerlab.log")

# OTHER LOGS DIR:
LOGS_DIR = os.path.join(HOME_DIR, "logs")
os.makedirs(name=LOGS_DIR, exist_ok=True)


# TODO: Move this to Experiment
def experiment_dir_by_name(experiment_name: str) -> str:
    return os.path.join(EXPERIMENTS_DIR, experiment_name)


# PLUGIN_DIR
PLUGIN_DIR = os.path.join(WORKSPACE_DIR, "plugins")


def plugin_dir_by_name(plugin_name: str) -> str:
    plugin_name = secure_filename(plugin_name)
    return os.path.join(PLUGIN_DIR, plugin_name)


# MODELS_DIR
MODELS_DIR = os.path.join(WORKSPACE_DIR, "models")
os.makedirs(name=MODELS_DIR, exist_ok=True)

# DATASETS_DIR
DATASETS_DIR = os.path.join(WORKSPACE_DIR, "datasets")
os.makedirs(name=DATASETS_DIR, exist_ok=True)


def dataset_dir_by_id(dataset_id: str) -> str:
    return os.path.join(DATASETS_DIR, dataset_id)


TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp")
os.makedirs(name=TEMP_DIR, exist_ok=True)


# Prompt Templates Dir:
PROMPT_TEMPLATES_DIR = os.path.join(WORKSPACE_DIR, "prompt_templates")
os.makedirs(name=PROMPT_TEMPLATES_DIR, exist_ok=True)

# Tools Dir:
TOOLS_DIR = os.path.join(WORKSPACE_DIR, "tools")
os.makedirs(name=TOOLS_DIR, exist_ok=True)

# Batched Prompts Dir:
BATCHED_PROMPTS_DIR = os.path.join(WORKSPACE_DIR, "batched_prompts")
os.makedirs(name=BATCHED_PROMPTS_DIR, exist_ok=True)

GALLERIES_CACHE_DIR = os.path.join(WORKSPACE_DIR, "galleries")
os.makedirs(name=GALLERIES_CACHE_DIR, exist_ok=True)

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


# TEMPORARY: These functions are duplicates of things you can do elsewhere
# But we need to leave them here in order to not break the API for now


def job_dir_by_experiment_and_id(experiment_name: str, job_id: str) -> str:
    """
    Get the job directory path for a given experiment and job ID.
    Uses new structure: WORKSPACE_DIR/experiments/experiment_name/jobs/job_id/
    Args:
        experiment_name: Name of the experiment
        job_id: Job ID (will be sanitized with secure_filename)
    Returns:
        Path to the job directory
    """
    job_id_safe = secure_filename(str(job_id))
    experiment_dir = experiment_dir_by_name(experiment_name)
    job_dir = os.path.join(experiment_dir, "jobs", job_id_safe)
    os.makedirs(job_dir, exist_ok=True)
    return job_dir


def get_job_output_dir(experiment_name: str, job_id: str) -> str:
    """
    Get the job output directory, with backward compatibility.
    First tries new structure, then falls back to old structure if needed.
    Args:
        experiment_name: Name of the experiment
        job_id: Job ID
    Returns:
        Path to the job output directory
    """
    # Try new structure first
    new_job_dir = job_dir_by_experiment_and_id(experiment_name, job_id)
    if os.path.exists(new_job_dir):
        return new_job_dir

    # Fall back to old structure for backward compatibility
    job_id_safe = secure_filename(str(job_id))
    old_job_dir = os.path.join(WORKSPACE_DIR, "jobs", job_id_safe)
    if os.path.exists(old_job_dir):
        return old_job_dir

    # If neither exists, return new structure (will be created when needed)
    return new_job_dir
