from . import dirs
from .labresource import BaseLabResource


class Job(BaseLabResource):
    """
    Used to update status and info of long-running jobs.
    """

    def __init__(self, experiment_name, job_id):
        self.id = job_id
        self.experiment_name = experiment_name
        self.should_stop = False

    def _get_dir(self):
        """Abstract method on BaseLabResource"""
        return dirs.job_dir_by_experiment_and_id(self.experiment_name, self.id)

    def update_progress(self, progress: int):
        """
        Update the percent complete for this job.

        progress: int representing percent complete
        """
        self._update_json_data_field("progress", progress)

    def update_status(self, status: str):
        """
        Update the status of this job.

        status: str representing the status of the job
        """
        self._update_json_data_field("status", status)

    def get_status(self):
        """
        Get the status of this job.
        """
        return self._get_json_data_field("status")

    def get_progress(self):
        """
        Get the progress of this job.
        """
        return self._get_json_data_field("progress")

    def get_experiment_id(self):
        """
        Get the experiment_id of this job.
        """
        return self.experiment_name

    def get_job_data(self):
        """
        Get the job_data of this job.
        """
        return self._get_json_data_field("job_data", {})

    def set_tensorboard_output_dir(self, tensorboard_dir: str):
        """
        Sets the directory that tensorboard output is stored.
        """
        self.update_job_data("tensorboard_output_dir", tensorboard_dir)

    def update_job_data(self, key: str, value):
        """
        Updates a key-value pair in the job_data JSON object.
        """
        # Fetch current job_data
        json_data = self._get_json_data()

        # If there isn't a job_data property then make one
        if "job_data" not in json_data:
            json_data["job_data"] = {}

        # Set the key property to value and save the whole object
        json_data["job_data"][key] = value
        self._set_json_data()

    def set_job_completion_status(
        self,
        completion_status: str,
        completion_details: str,
        score: dict = None,
        additional_output_path: str = None,
        plot_data_path: str = None,
    ):
        """
        A job could be in the "complete" state but still have failed, so this
        function is used to set the job completion status. i.e. how the task
        that the job is executing has completed.
        and if the job failed, the details of the failure.
        Score should be a json of the format {"metric_name": value, ...}
        """
        # TODO
        pass
