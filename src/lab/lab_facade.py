from __future__ import annotations

from typing import Optional, Dict, Any
import os
import shutil

from .experiment import Experiment
from .job import Job
from . import dirs


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
        self._experiment = Experiment(experiment_id, create_new=True)
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

    def save_artifact(self, source_path: str, name: Optional[str] = None) -> str:
        """
        Save an artifact file or directory into this job's artifacts folder.
        Returns the destination path on disk.
        """
        self._ensure_initialized()
        if not isinstance(source_path, str) or source_path.strip() == "":
            raise ValueError("source_path must be a non-empty string")
        src = os.path.abspath(source_path)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Artifact source does not exist: {src}")

        job_id = self._job.id  # type: ignore[union-attr]
        artifacts_dir = dirs.get_job_artifacts_dir(job_id)
        base_name = name if (isinstance(name, str) and name.strip() != "") else os.path.basename(src)
        dest = os.path.join(artifacts_dir, base_name)

        # Create parent directories
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Copy file or directory
        if os.path.isdir(src):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

        # Track in job_data
        try:
            job_data = self._job.get_job_data()
            artifact_list = []
            if isinstance(job_data, dict):
                existing = job_data.get("artifacts", [])
                if isinstance(existing, list):
                    artifact_list = existing
            artifact_list.append(dest)
            self._job.update_job_data_field("artifacts", artifact_list)
        except Exception:
            pass

        return dest

    def save_checkpoint(self, source_path: str, name: Optional[str] = None) -> str:
        """
        Save a checkpoint file or directory into this job's checkpoints folder.
        Returns the destination path on disk.
        """
        self._ensure_initialized()
        if not isinstance(source_path, str) or source_path.strip() == "":
            raise ValueError("source_path must be a non-empty string")
        src = os.path.abspath(source_path)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Checkpoint source does not exist: {src}")

        job_id = self._job.id  # type: ignore[union-attr]
        ckpts_dir = dirs.get_job_checkpoints_dir(job_id)
        base_name = name if (isinstance(name, str) and name.strip() != "") else os.path.basename(src)
        dest = os.path.join(ckpts_dir, base_name)

        # Create parent directories
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Copy file or directory
        if os.path.isdir(src):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

        # Track in job_data and update latest pointer
        try:
            job_data = self._job.get_job_data()
            ckpt_list = []
            if isinstance(job_data, dict):
                existing = job_data.get("checkpoints", [])
                if isinstance(existing, list):
                    ckpt_list = existing
            ckpt_list.append(dest)
            self._job.update_job_data_field("checkpoints", ckpt_list)
            self._job.update_job_data_field("latest_checkpoint", dest)
        except Exception:
            pass

        return dest

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


