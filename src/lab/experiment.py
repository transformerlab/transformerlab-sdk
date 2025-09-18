from . import dirs
from .labresource import BaseLabResource


class Experiment(BaseLabResource):
    """
    Base object for managing all config associated with an experiment
    """

    def __init__(self, experiment_id):
        self.id = experiment_id

    def _get_dir(self):
        """Abstract method on BaseLabResource"""
        return dirs.experiment_dir_by_name(self.id)
