import os
from werkzeug.utils import secure_filename

from .dirs import EXPERIMENTS_DIR, JOBS_DIR
from .labresource import BaseLabResource
from .job import Job
import json


class Experiment(BaseLabResource):
    """
    Base object for managing all config associated with an experiment
    """

    DEFAULT_JOBS_INDEX = {"TRAIN": []}

    def __init__(self, experiment_id):
        self.id = experiment_id

    def get_dir(self):
        """Abstract method on BaseLabResource"""
        experiment_id_safe = secure_filename(str(self.id))
        return os.path.join(EXPERIMENTS_DIR, experiment_id_safe)

    def _default_json(self):
        return {"name": self.id, "config": {}}

    def _initialize(self):
        super()._initialize()

        # Create a empty jobs index and write
        jobs_json_path = self._jobs_json_file()
        empty_jobs_list = self.DEFAULT_JOBS_INDEX
        with open(jobs_json_path, "w") as f:
            json.dump(empty_jobs_list, f, indent=4)

    @classmethod
    def get(cls, id):
        # First call the base get method to make sure it works
        exp = super().get(id)

        # Rebuild the jobs index to make sure it is up to date
        exp.rebuild_jobs_index()

        return exp

    def create_job(self):
        """
        Creates a new job with a blank template and returns a Job object.
        """

        # Choose an ID for the new job
        # Scan the jobs directory for subdirectories with numberic names
        # Find the largest number and increment to get the new job ID
        largest_numeric_subdir = 0
        for entry in os.listdir(JOBS_DIR):
            if entry.isdigit():
                full_path = os.path.join(JOBS_DIR, entry)
                if os.path.isdir(full_path):
                    job_id = int(entry)
                    if job_id > largest_numeric_subdir:
                        largest_numeric_subdir = job_id

        new_job_id = largest_numeric_subdir + 1
        new_job = Job.create(new_job_id)
        return new_job

    def get_jobs(self, type: str = "", status: str = ""):
        """
        Get a list of IDs for jobs stored in this experiment.
        type: If not blank, filter by jobs with this type.
        status: If not blank, filter by jobs with this status.
        """

        # First get jobs of the passed type
        job_list = []
        if type:
            job_list = self._get_jobs_of_type(type)
        else:
            job_list = self._get_all_jobs()

        # Iterate through the job list to return Job objects for valid jobs.
        # Also filter for status if that parameter was passed.
        results = []
        for job in job_list:
            try:
                job = Job.get(self.id, entry)
                job_json = job._get_json_data()
            except:
                continue

            # Filter for status
            if status and (job_json.get("status", "") != status):
                continue

            # If it passed filters then add as long as it has job_data
            if "job_data" in job_json:
                results.append(job_json)

        return results

    ###############################
    # jobs.json MANAGMENT FUNCTIONS
    # Index for tracking which jobs belong to this Experiment
    ###############################

    def _jobs_json_file(self):
        """
        Path to jobs.json index file for this experiment.
        """
        return os.path.join(self.get_dir, "jobs.json")

    def rebuild_jobs_index(self):
        print("REBUiLDING JOB INDEX")
        results = {}
        try:
            # Iterate through jobs directories and check for index.json
            for entry in os.listdir(JOBS_DIR):
                entry_path = os.path.join(JOBS_DIR, entry)
                if not os.path.isdir(entry_path):
                    continue
                index_file = os.path.join(entry_path, "index.json")
                if not os.path.isfile(index_file):
                    continue

                # Check the metadata for a type parameter and add to index
                try:
                    with open(index_file, "r") as jf:
                        data = json.load(jf)
                        job_type = data.get("type", "")
                        if job_type:
                            results.setdefault(job_type, []).append(entry)
                except Exception:
                    continue

            # Write discovered index to jobs.json
            if results:
                try:
                    with open(self._jobs_json_file(), "w") as out:
                        json.dump(results, out, indent=4)
                except Exception:
                    pass
        except Exception:
            pass
        print(results)

    def _get_all_jobs(self):
        """
        Amalgamates all jobs in the index file.
        """
        try:
            with open(self._jobs_json_file(), "r") as f:
                jobs = json.load(f)
                results = []
                for key, value in jobs.items():
                    if isinstance(value, list):
                        results.extend(value)
                return results
        except Exception:
            return []

    def _get_jobs_of_type(self, type="TRAIN"):
        """ "
        Returns all jobs of a specific type in this experiment's index file.
        """
        try:
            with open(self._jobs_json_file(), "r") as f:
                jobs = json.load(f)
                print("JOB SEARCH")
                print(jobs)
                return jobs.get(type, [])
        except Exception:
            return []

    def _add_job(self, job_id, type):
        with open(self._jobs_json_file(), "r") as f:
            jobs = json.load(f)
            if type in jobs:
                jobs[type].append(job_id)
            else:
                jobs[type] = [job_id]
