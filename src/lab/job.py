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
        job_dir = os.path.join(dirs.get_jobs_dir(), job_id_safe)
        return job_dir

    def get_log_path(self):
        """
        Returns the path where this job should write logs.
        """
        # Default location for log file
        log_path = os.path.join(self.get_dir(), f"output_{self.id}.txt")

        if not os.path.exists(log_path):
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
            "type": "REMOTE",
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
        json_data = self.get_json_data()

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

        # Read existing content, append new message, and write back to log file
        try:
            log_path = self.get_log_path()
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            # Read existing content if file exists
            existing_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            
            # Append new message to existing content on a new line
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"
            new_content = existing_content + message_str
            
            # Write back the complete content
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                f.flush()  # Ensure immediate write to disk, especially important in fused file systems
        except Exception:
            # Best-effort file logging; ignore file errors to avoid crashing job
            pass

    def set_type(self, job_type: str):
        """
        Set the type of this job.
        """
        self._update_json_data_field("type", job_type)

    def get_experiment_id(self):
        """
        Get the experiment_id of this job.
        """
        return self._get_json_data_field("experiment_id")

    def set_error_message(self, error_msg: str):
        """
        Set an error message in the job_data.
        """
        self.update_job_data_field("error_msg", str(error_msg))

    def update_sweep_progress(self, value):
        """
        Update the 'sweep_progress' key in the job_data JSON object.
        """
        self.update_job_data_field("sweep_progress", value)

    @classmethod
    def count_running_jobs(cls):
        """
        Count how many jobs are currently running.
        """
        count = 0
        jobs_dir = dirs.get_jobs_dir()
        if os.path.exists(jobs_dir):
            for entry in os.listdir(jobs_dir):
                job_path = os.path.join(jobs_dir, entry)
                if os.path.isdir(job_path):
                    try:
                        job = cls.get(entry)
                        job_data = job.get_json_data()
                        if job_data.get("status") == "RUNNING":
                            count += 1
                    except Exception:
                        pass
        return count

    @classmethod
    def get_next_queued_job(cls):
        """
        Get the next queued job (oldest first based on directory creation time).
        Returns Job data dict or None if no queued jobs.
        """
        queued_jobs = []
        jobs_dir = dirs.get_jobs_dir()
        if os.path.exists(jobs_dir):
            for entry in os.listdir(jobs_dir):
                job_path = os.path.join(jobs_dir, entry)
                if os.path.isdir(job_path):
                    try:
                        job = cls.get(entry)
                        job_data = job.get_json_data()
                        if job_data.get("status") == "QUEUED":
                            # Use filesystem creation time for sorting
                            creation_time = os.path.getctime(job_path)
                            queued_jobs.append((creation_time, job_data))
                    except Exception:
                        pass
        
        if queued_jobs:
            # Sort by creation time and return the oldest
            queued_jobs.sort(key=lambda x: x[0])
            return queued_jobs[0][1]
        return None

    def delete(self):
        """
        Mark this job as deleted.
        """
        self.update_status("DELETED")