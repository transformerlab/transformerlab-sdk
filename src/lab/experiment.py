import os
from werkzeug.utils import secure_filename

from .dirs import EXPERIMENTS_DIR
from .labresource import BaseLabResource
from .job import Job


class Experiment(BaseLabResource):
    """
    Base object for managing all config associated with an experiment
    """

    def __init__(self, experiment_id):
        self.id = experiment_id

    def get_dir(self):
        """Abstract method on BaseLabResource"""
        experiment_id_safe = secure_filename(str(self.id))
        return os.path.join(EXPERIMENTS_DIR, experiment_id_safe)

    def _get_jobs_dir(self):
        return os.path.join(self.get_dir(), "jobs")

    def create_new_job(self):
        """
        Creates a new job with a blank template and returns a Job object.
        """
        jobs_dir = self._get_jobs_dir()

        # Choose an ID for the new job
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

    def get_jobs(self, type: str = "", status: str = ""):
        """
        Get a list of IDs for jobs stored in this experiment.
        type: If not blank, filter by jobs with this type.
        status: If not blank, filter by jobs with this status.
        """
        jobs_dir = self._get_jobs_dir()

        # Iterate through the jobs directory and add validate jobs to result
        # A subdirectory if a valid job if it contains a file called index.json
        # and that json file parses.
        results = []
        if os.path.isdir(jobs_dir):
            for entry in os.listdir(jobs_dir):
                job = Job(self.id, entry)
                job_json = job._get_json_data()

                # Filter based on the passed parameters
                if type and (job_json.get("type", "") != type):
                    continue
                if status and (job_json.get("status", "") != status):
                    continue

                # If it passed filters then add as long as it has job_data
                if "job_data" in job_json:
                    results.append(job_json)

        return results
