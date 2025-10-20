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
        
        # Check for wandb integration and capture URL if available
        self._detect_and_capture_wandb_url()

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
        # Check for wandb URL on every log operation
        self._check_and_capture_wandb_url()

    def update_progress(self, progress: int) -> None:
        """
        Update job progress and check for wandb URL detection.
        """
        self._ensure_initialized()
        self._job.update_progress(progress)  # type: ignore[union-attr]
        # Check for wandb URL on every progress update
        self._check_and_capture_wandb_url()

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

    def _detect_and_capture_wandb_url(self) -> None:
        """
        Detect wandb run URLs from various sources and store them in job data.
        This method checks for wandb integration in multiple ways:
        1. Environment variables set by wandb
        2. Active wandb runs in the current process
        3. TRL trainer integrations
        """
        try:
            # Method 1: Check environment variables set by wandb
            wandb_url = os.environ.get('WANDB_URL')
            if wandb_url:
                self._job.update_job_data_field("wandb_run_url", wandb_url)
                print(f"📊 Detected wandb run URL: {wandb_url}")
                return
            
            # Method 2: Check for active wandb run in current process
            try:
                import wandb
                if wandb.run is not None:
                    wandb_url = wandb.run.url
                    if wandb_url:
                        self._job.update_job_data_field("wandb_run_url", wandb_url)
                        print(f"📊 Detected wandb run URL: {wandb_url}")
                        return
            except ImportError:
                pass
            
            # Method 3: Check for wandb in TRL trainers or other frameworks
            # Look for wandb integration in global variables or modules
            try:
                import wandb
                # Check if there's a wandb run that was initialized elsewhere
                if hasattr(wandb, 'api') and wandb.api and wandb.api.api_key:
                    # If wandb is configured, try to get the current run
                    current_run = wandb.run
                    if current_run and hasattr(current_run, 'url'):
                        wandb_url = current_run.url
                        if wandb_url:
                            self._job.update_job_data_field("wandb_run_url", wandb_url)
                            print(f"📊 Detected wandb run URL: {wandb_url}")
                            return
            except (ImportError, AttributeError):
                pass
                
        except Exception:
            # Silently fail - wandb detection is optional
            pass

    def _check_and_capture_wandb_url(self) -> None:
        """
        Check for wandb run URLs and capture them in job data.
        This is called automatically on every log and progress update operation.
        """
        try:
            # Only check if we haven't already captured a wandb URL
            job_data = self._job.get_job_data()
            if job_data.get("wandb_run_url"):
                return  # Already have a wandb URL
            
            # Method 1: Check environment variables
            wandb_url = os.environ.get('WANDB_URL')
            if wandb_url:
                self._job.update_job_data_field("wandb_run_url", wandb_url)
                print(f"📊 Auto-detected wandb URL from environment: {wandb_url}")
                return
            
            # Method 2: Check active wandb run
            try:
                import wandb
                if wandb.run is not None and hasattr(wandb.run, 'url'):
                    wandb_url = wandb.run.url
                    if wandb_url:
                        self._job.update_job_data_field("wandb_run_url", wandb_url)
                        print(f"📊 Auto-detected wandb URL from wandb.run: {wandb_url}")
                        return
            except ImportError:
                pass
                
        except Exception:
            # Silently fail - wandb detection is optional
            pass

    def capture_wandb_url(self, wandb_url: str) -> None:
        """
        Manually capture a wandb run URL and store it in job data.
        This can be called by scripts that have wandb integration.
        """
        if wandb_url and wandb_url.strip():
            self._ensure_initialized()
            self._job.update_job_data_field("wandb_run_url", wandb_url.strip())
            print(f"📊 Captured wandb run URL: {wandb_url.strip()}")

    # ------------- helpers -------------
    def _ensure_initialized(self) -> None:
        if self._experiment is None or self._job is None:
            raise RuntimeError("lab not initialized. Call lab.init(experiment_id=...) first.")

    @property
    def job(self) -> Job:
        self._ensure_initialized()
        return self._job  # type: ignore[return-value]

    def get_checkpoints_dir(self) -> str:
        """
        Get the checkpoints directory path for the current job.
        """
        self._ensure_initialized()
        return self._job.get_checkpoints_dir()  # type: ignore[union-attr]
    
    def get_artifacts_dir(self) -> str:
        """
        Get the artifacts directory path for the current job.
        """
        self._ensure_initialized()
        return self._job.get_artifacts_dir()  # type: ignore[union-attr]
    
    def get_checkpoint_paths(self) -> list[str]:
        """
        Get list of checkpoint file paths for the current job.
        """
        self._ensure_initialized()
        return self._job.get_checkpoint_paths()  # type: ignore[union-attr]
    
    def get_artifact_paths(self) -> list[str]:
        """
        Get list of artifact file paths for the current job.
        """
        self._ensure_initialized()
        return self._job.get_artifact_paths()  # type: ignore[union-attr]

    @property
    def experiment(self) -> Experiment:
        self._ensure_initialized()
        return self._experiment  # type: ignore[return-value]




def capture_wandb_url_from_env() -> str | None:
    """
    Utility function to capture wandb run URL from environment variables.
    This can be called by scripts that use wandb but don't use the TLabPlugin system.
    
    Returns:
        str: The wandb run URL if found, None otherwise
    """
    return os.environ.get('WANDB_URL')


def capture_wandb_url_from_run() -> str | None:
    """
    Utility function to capture wandb run URL from the current wandb run.
    This can be called by scripts that have initialized wandb.run.
    
    Returns:
        str: The wandb run URL if found, None otherwise
    """
    try:
        import wandb
        if wandb.run is not None and hasattr(wandb.run, 'url'):
            return wandb.run.url
    except ImportError:
        pass
    return None


def capture_wandb_url_from_trl() -> str | None:
    """
    Utility function to capture wandb run URL from TRL trainers.
    This checks for wandb integration in TRL-based training scripts.
    
    Returns:
        str: The wandb run URL if found, None otherwise
    """
    try:
        import wandb
        # Check for wandb in TRL trainer context
        if wandb.run is not None:
            return wandb.run.url
        
        # Check environment variables as fallback
        return os.environ.get('WANDB_URL')
    except ImportError:
        return None


