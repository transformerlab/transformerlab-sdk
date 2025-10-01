from .dirs import WORKSPACE_DIR, HOME_DIR
from .workspace import get_workspace_dir
from .auth import set_cookies, set_sealed_session
from .job import Job
from .experiment import Experiment
from .model import Model
from .dataset import Dataset

from .lab_facade import Lab

# Provide a convenient singleton facade for simple usage
lab = Lab()

__all__ = [
    "WORKSPACE_DIR",
    "HOME_DIR",
    "get_workspace_dir",
    "set_cookies",
    "set_sealed_session",
    Job,
    Experiment,
    Model,
    Dataset,
    "lab",
    "Lab",
]
