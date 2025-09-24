import os
from werkzeug.utils import secure_filename

from . import dirs
from .labresource import BaseLabResource


class Job(BaseLabResource):
    """
    Used to update status and info of long-running jobs.
    """

    def __init__(self, job_id):
        self.id = job_id
        self.should_stop = False

    def get_dir(self):
        """Abstract method on BaseLabResource"""
        job_id_safe = secure_filename(str(self.id))
        job_dir = os.path.join(dirs.JOBS_DIR, job_id_safe)
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    def get_log_path(self):
        """
        Returns the path where this job should write logs.
        """
        try:
            job_data = self.get_job_data()
            if isinstance(job_data, dict):
                override_path = job_data.get("_tlab_logging_file", "")
                if isinstance(override_path, str) and override_path.strip() != "":
                    return override_path
        except Exception:
            pass
        return os.path.join(self.get_dir(), f"output_{self.id}.txt")

    def _default_json(self):
        return {
            "id": self.id,
            "experiment_id": "",
            "job_data": {},
            "status": "NOT_STARTED",
            "type": "TRAIN",
            "progress": 0,
            "output_file_path": self.get_log_path(),
        }

    def set_experiment(self, experiment_id: str):
        self._update_json_data_field("experiment_id", experiment_id)
        self.update_job_data_field("experiment_name", experiment_id)

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

    def get_job_data(self):
        """
        Get the job_data of this job.
        """
        return self._get_json_data_field("job_data", {})

    def set_job_data(self, job_data):
        self._update_json_data_field("job_data", job_data)

    def set_tensorboard_output_dir(self, tensorboard_dir: str):
        """
        Sets the directory that tensorboard output is stored.
        """
        self.update_job_data_field("tensorboard_output_dir", tensorboard_dir)

    def update_job_data_field(self, key: str, value):
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
        self._set_json_data(json_data)

    def set_job_completion_status(
        self,
        completion_status: str,
        completion_details: str = "",
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

        Throws:
        ValueError if completion_status isn't one of "success" or "failed"
        """
        if completion_status not in ("success", "failed"):
            raise ValueError("completion_status must be either 'success' or 'failed'")

        # Fetch current job_data
        json_data = self._get_json_data()

        # If there isn't a job_data property then make one
        if "job_data" not in json_data:
            json_data["job_data"] = {}

        # Add to job data completion_status and completion_details
        json_data["job_data"]["completion_status"] = completion_status
        json_data["job_data"]["completion_details"] = completion_details

        # Update the job status field if there's a failure
        if completion_status == "failed":
            json_data["job_data"]["status"] = "FAILED"

        if score is not None:
            json_data["job_data"]["score"] = score

        # Determine if additional_output_path and plot_data_path are valid and set
        valid_output_path = (
            additional_output_path
            if additional_output_path and additional_output_path.strip() != ""
            else None
        )
        valid_plot_data_path = (
            plot_data_path if plot_data_path and plot_data_path.strip() != "" else None
        )

        if valid_output_path is not None:
            json_data["job_data"]["additional_output_path"] = valid_output_path

        if valid_plot_data_path is not None:
            json_data["job_data"]["plot_data_path"] = valid_plot_data_path

        # Save the entire updated json blob
        self._set_json_data(json_data)

    def log_info(self, message):
        """
        Save info message to output log file and display to terminal.

        TODO: Using logging or something proper to do this.
        """
        # log_file = self.get_dir
        # self.update_output_file(message)
        print(message)
