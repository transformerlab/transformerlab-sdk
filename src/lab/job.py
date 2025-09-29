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
        # Default location for log file
        log_path = os.path.join(self.get_dir(), f"output_{self.id}.txt")

        # Then check if there is a path explicitly set in the job data
        try:
            job_data = self.get_job_data()
            if isinstance(job_data, dict):
                override_path = job_data.get("output_file_path", "")
                if isinstance(override_path, str) and override_path.strip() != "":
                    log_path = override_path
        except Exception:
            pass

        # Make sure whatever log_path we return actually exists
        # Put an empty file there if not
        if not os.path.exists(log_path):
            with open(log_path, "w") as f:
                f.write("")

        return log_path

    def _default_json(self):
        default_job_data = {
            "output_file_path": self.get_log_path(),
        }
        return {
            "id": self.id,
            "experiment_id": "",
            "job_data": default_job_data,
            "status": "NOT_STARTED",
            "type": "TRAIN",
            "progress": 0,
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

    def log_info(self, message):
        """
        Save info message to output log file and display to terminal.

        TODO: Using logging or something proper to do this.
        """
        # Always print to console
        print(message)

        # Coerce message to string and ensure newline termination
        try:
            message_str = str(message)
        except Exception:
            message_str = "<non-string message>"

        if not message_str.endswith("\n"):
            message_str = message_str + "\n"

        # Append to the job's log file, creating directories as needed
        try:
            log_path = self.get_log_path()
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message_str)
        except Exception:
            # Best-effort file logging; ignore file errors to avoid crashing job
            pass
