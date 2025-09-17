import json

import .dirs

class Job:
    """
    Used to update status and info of long-running jobs.
    """


    def __init__(self, experiment_name, job_id):
        self.id = job_id
        self.experiment_name = experiment_name
        self.should_stop = False

    def _get_json_data(self):
        """
        Return the JSON data that is stored for this job in the filesystem.
        If the file doesn't exist then return an empty dict.
        """
        job_file = dirs.job_dir_by_experiment_and_id(self.experiment_name: str, self.id)

        # Try opening this file location and parsing the json inside
        # On any error return an empty dict
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def update_progress(self, progress: int):
        """
        Update the percent complete for this job.

        progress: int representing percent complete
        """
        # TODO
        pass

    def update_status(self, status: str):
        """
        Update the status of this job.

        status: str representing the status of the job
        """
        # TODO
        pass

    def get_status(self):
        """
        Get the status of this job.
        """
        # TODO
        return None

    def get_progress(self):
        """
        Get the progress of this job.
        """
        # TODO
        return None

    def get_experiment_id(self):
        """
        Get the experiment_id of this job.
        """
        # TODO
        return None

    def get_job_data(self):
        """
        Get the job_data of this job.
        """
        # TODO
        return {}

    def set_tensorboard_output_dir(self, tensorboard_dir: str):
        """
        Sets the directory that tensorboard output is stored.
        """
        # TODO
        pass

    def add_to_job_data(self, key: str, value):
        """
        Adds a key-value pair to the job_data JSON object.
        """
        # TODO
        pass

    def update_job_data(self, key: str, value):
        """
        Updates a key-value pair in the job_data JSON object.
        """
        # TODO
        pass

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
