import os

from . import dirs
from .labresource import BaseLabResource
from .job import Job


class Experiment(BaseLabResource):
    """
    Base object for managing all config associated with an experiment
    """

    def __init__(self, experiment_id):
        self.id = experiment_id

    def _get_dir(self):
        """Abstract method on BaseLabResource"""
        return dirs.experiment_dir_by_name(self.id)

    def _get_jobs_dir(self):
        return os.path.join(self._get_dir(), "jobs")

    def create_new_job(self):
        jobs_dir = self._get_jobs_dir()

        # Scan the jobs directory for subdirectories with numberic names
        # Find the largest number and increment to get the new job ID
        largest_numeric_subdir = 0
        if os.path.isdir(jobs_dir):
            for entry in os.listdir(jobs_dir):
                if entry.isdigit():
                    full_path = os.path.join(jobs_dir, entry)
                    if os.path.isdir(full_path):
                        job_id = int(entry)
                        if job_id > largest_numeric_subdir:
                            largest_numeric_subdir = job_id

        new_job_id = largest_numeric_subdir + 1
        new_job = Job(self.id, new_job_id)
        return new_job
