from __future__ import annotations

from typing import Optional, Dict, Any

from .experiment import Experiment
from .job import Job


class Lab:
    """
    Simple facade over Experiment and Job for easy usage:

    from lab import lab
    lab.init(experiment_id="alpha")
    lab.set_config({ ... })
    lab.log("message")
    lab.finish("success")
    """

    def __init__(self) -> None:
        self._experiment: Optional[Experiment] = None
        self._job: Optional[Job] = None

    # ------------- lifecycle -------------
    def init(self, experiment_id: str = "alpha") -> None:
        """
        Initialize a new job under the given experiment.
        Creates the experiment structure if needed and creates a new job.
        """
        self._experiment = Experiment(experiment_id)
        self._job = self._experiment.create_job()
        self._job.set_experiment(experiment_id)
        self._job.update_status("IN_PROGRESS")

    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Attach configuration to the current job.
        """
        self._ensure_initialized()
        # Ensure experiment_name present for downstream consumers
        if isinstance(config, dict) and "experiment_name" not in config and self._experiment is not None:
            config = {**config, "experiment_name": self._experiment.id}
        # keep the existing config with fields that are not in the new config
        config_old = self._job.get_job_data()
        config_new = {**config_old, **config}
        self._job.set_job_data(config_new)  # type: ignore[union-attr]

    # ------------- convenience logging -------------
    def log(self, message: str) -> None:
        self._ensure_initialized()
        self._job.log_info(message)  # type: ignore[union-attr]

    # ------------- completion -------------
    def finish(
        self,
        message: str = "Job completed successfully",
        score: Optional[Dict[str, Any]] = None,
        additional_output_path: Optional[str] = None,
        plot_data_path: Optional[str] = None,
    ) -> None:
        """
        Mark the job as successfully completed and set completion metadata.
        """
        self._ensure_initialized()
        self._job.update_progress(100)  # type: ignore[union-attr]
        self._job.update_status("COMPLETE")  # type: ignore[union-attr]
        self._job.update_job_data_field("completion_status", "success")  # type: ignore[union-attr]
        self._job.update_job_data_field("completion_details", message)  # type: ignore[union-attr]
        if score is not None:
            self._job.update_job_data_field("score", score)  # type: ignore[union-attr]
        if additional_output_path is not None and additional_output_path.strip() != "":
            self._job.update_job_data_field("additional_output_path", additional_output_path)  # type: ignore[union-attr]
        if plot_data_path is not None and plot_data_path.strip() != "":
            self._job.update_job_data_field("plot_data_path", plot_data_path)  # type: ignore[union-attr]

    def error(
        self,
        message: str = "",
    ) -> None:
        """
        Mark the job as failed and set completion metadata.
        """
        self._ensure_initialized()
        self._job.update_status("COMPLETE")  # type: ignore[union-attr]
        self._job.update_job_data_field("completion_status", "failed")  # type: ignore[union-attr]
        self._job.update_job_data_field("completion_details", message)  # type: ignore[union-attr]
        self._job.update_job_data_field("status", "FAILED")  # type: ignore[union-attr]

    # ------------- helpers -------------
    def _ensure_initialized(self) -> None:
        if self._experiment is None or self._job is None:
            raise RuntimeError("lab not initialized. Call lab.init(experiment_id=...) first.")

    @property
    def job(self) -> Job:
        self._ensure_initialized()
        return self._job  # type: ignore[return-value]

    @property
    def experiment(self) -> Experiment:
        self._ensure_initialized()
        return self._experiment  # type: ignore[return-value]


