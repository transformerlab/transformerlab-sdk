from __future__ import annotations

import time
from typing import Optional, Dict, Any
import os
import shutil

from .experiment import Experiment
from .job import Job
from . import dirs
from .model import Model as ModelService
from .dataset import Dataset

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
        Initialize a job under the given experiment.
        If _TFL_JOB_ID environment variable is set, uses that existing job.
        Otherwise, creates the experiment structure if needed and creates a new job.
        """
        # Check if we should use an existing job from environment variable
        existing_job_id = os.environ.get('_TFL_JOB_ID')
        
        if existing_job_id:
            # Use existing job from environment variable
            # This will raise an error if the job doesn't exist
            self._experiment = Experiment(experiment_id, create_new=False)
            self._job = Job.get(existing_job_id)
            if self._job is None:
                raise RuntimeError(f"Job with ID {existing_job_id} not found. Check _TFL_JOB_ID environment variable.")
            print(f"Using existing job ID: {existing_job_id}")
        else:
            # Create new job as before
            self._experiment = Experiment(experiment_id, create_new=True)
            self._job = self._experiment.create_job()
            self._job.update_job_data_field("start_time", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
            self._job.set_experiment(experiment_id)
            print(f"Created new job ID: {self._job.id}")
        
        # Update status to RUNNING for both cases
        self._job.update_status("RUNNING")
        
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

    def save_dataset(self, df, dataset_id: str, additional_metadata: Optional[Dict[str, Any]] = None, suffix: Optional[str] = None, is_image: bool = False) -> str:
        """
        Save a dataset under the workspace datasets directory and mark it as generated.

        Args:
            df: A pandas DataFrame or a Hugging Face datasets.Dataset to serialize to disk.
            dataset_id: Identifier for the dataset directory under `datasets/`.
            additional_metadata: Optional dict to merge into dataset json_data.
            suffix: Optional suffix to append to the output filename stem.
            is_image: If True, save JSON Lines (for image metadata-style rows).

        Returns:
            The path to the saved dataset file on disk.
        """
        self._ensure_initialized()
        if not isinstance(dataset_id, str) or dataset_id.strip() == "":
            raise ValueError("dataset_id must be a non-empty string")

        # Normalize input: convert Hugging Face datasets.Dataset to pandas DataFrame
        try:
            if hasattr(df, "to_pandas") and callable(getattr(df, "to_pandas")):
                df = df.to_pandas()
        except Exception:
            pass

        # Prepare dataset directory
        dataset_id_safe = dataset_id.strip()
        dataset_dir = dirs.dataset_dir_by_id(dataset_id_safe)
        # If exists, then raise an error
        if os.path.exists(dataset_dir):
            raise FileExistsError(f"Dataset with ID {dataset_id_safe} already exists")
        os.makedirs(dataset_dir, exist_ok=True)

        # Determine output filename
        if is_image:
            lines = True
            output_filename = "metadata.jsonl"
        else:
            lines = False
            stem = dataset_id_safe
            if isinstance(suffix, str) and suffix.strip() != "":
                stem = f"{stem}_{suffix.strip()}"
            output_filename = f"{stem}.json"

        output_path = os.path.join(dataset_dir, output_filename)

        # Persist dataframe
        try:
            if not hasattr(df, "to_json"):
                raise TypeError("df must be a pandas DataFrame or a Hugging Face datasets.Dataset")
            df.to_json(output_path, orient="records", lines=lines)
        except Exception as e:
            raise RuntimeError(f"Failed to save dataset to {output_path}: {str(e)}")

        # Create or update filesystem metadata so it appears under generated datasets
        try:
            try:
                ds = Dataset.get(dataset_id_safe)
            except FileNotFoundError:
                ds = Dataset.create(dataset_id_safe)

            # Base json_data with generated flag for UI filtering
            json_data: Dict[str, Any] = {
                "generated": True,
                "sample_count": len(df) if hasattr(df, "__len__") else -1,
                "files": [output_filename],
            }
            if additional_metadata and isinstance(additional_metadata, dict):
                json_data.update(additional_metadata)

            ds.set_metadata(
                location="local",
                description=json_data.get("description", ""),
                size=-1,
                json_data=json_data,
            )
        except Exception as e:
            # Do not fail the save if metadata write fails; log to job data
            try:
                self._job.update_job_data_field("dataset_metadata_error", str(e))  # type: ignore[union-attr]
            except Exception:
                pass

        # Track dataset on the job for provenance
        try:
            self._job.update_job_data_field("dataset_id", dataset_id_safe)  # type: ignore[union-attr]
        except Exception:
            pass

        self.log(f"Dataset saved to '{output_path}' and registered as generated dataset '{dataset_id_safe}'")
        return output_path

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

    def save_model(self, source_path: str, name: Optional[str] = None, architecture: Optional[str] = None, pipeline_tag: Optional[str] = None, parent_model: Optional[str] = None) -> str:
        """
        Save a model file or directory to the workspace models directory.
        The model will automatically appear in the Model Zoo's Local Models list.
        
        Args:
            source_path: Path to the model file or directory to save
            name: Optional name for the model. If not provided, uses source basename.
                 The final model name will be prefixed with the job_id for uniqueness.
            architecture: Optional architecture string. If not provided, will attempt to 
                         detect from config.json for directory-based models.
            pipeline_tag: Optional pipeline tag. If not provided and parent_model is given,
                         will attempt to fetch from parent model on HuggingFace.
            parent_model: Optional parent model name/ID for provenance tracking.
        
        Returns:
            The destination path on disk.
        """
        self._ensure_initialized()
        if not isinstance(source_path, str) or source_path.strip() == "":
            raise ValueError("source_path must be a non-empty string")
        src = os.path.abspath(source_path)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Model source does not exist: {src}")

        job_id = self._job.id  # type: ignore[union-attr]
        
        # Determine base name with job_id prefix for uniqueness
        if isinstance(name, str) and name.strip() != "":
            base_name = f"{job_id}_{name}"
        else:
            base_name = f"{job_id}_{os.path.basename(src)}"
        
        # Save to main workspace models directory for Model Zoo visibility
        models_dir = dirs.get_models_dir()
        dest = os.path.join(models_dir, base_name)
        
        # Create parent directories
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Copy file or directory
        if os.path.isdir(src):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        
        # Create Model metadata so it appears in Model Zoo
        try:
            model_service = ModelService(base_name)
            
            # Use provided architecture or detect it
            if architecture is None:
                architecture = model_service.detect_architecture(dest)
            
            # Handle pipeline tag logic
            if pipeline_tag is None and parent_model is not None:
                # Try to fetch pipeline tag from parent model
                pipeline_tag = model_service.fetch_pipeline_tag(parent_model)
            # Determine model_filename for single-file models
            model_filename = "" if os.path.isdir(dest) else os.path.basename(dest)
            
            # Prepare json_data with basic info
            json_data = {
                "job_id": job_id,
                "description": f"Model generated by job {job_id}",
            }
            
            # Add pipeline tag to json_data if provided
            if pipeline_tag is not None:
                json_data["pipeline_tag"] = pipeline_tag
            
            # Use the Model class's generate_model_json method to create metadata
            model_service.generate_model_json(
                architecture=architecture,
                model_filename=model_filename,
                json_data=json_data
            )
            self.log(f"Model saved to Model Zoo as '{base_name}'")
        except Exception as e:
            self.log(f"Warning: Model saved but metadata creation failed: {str(e)}")

        # Create provenance data
        try:
            # Create MD5 checksums for all model files
            md5_objects = model_service.create_md5_checksums(dest)
            
            # Prepare provenance metadata from job data
            job_data = self._job.get_job_data()
            
            provenance_metadata = {
                "job_id": job_id,
                "model_name": parent_model or job_data.get("model_name"),
                "model_architecture": architecture,
                "input_model": parent_model,
                "dataset": job_data.get("dataset"),
                "adaptor_name": job_data.get("adaptor_name", None),
                "parameters": job_data.get("_config", {}),
                "start_time": job_data.get("start_time", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())),
                "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                "md5_checksums": md5_objects,


            }
            
            # Create the _tlab_provenance.json file
            provenance_file = model_service.create_provenance_file(
                model_path=dest,
                model_name=base_name,
                model_architecture=architecture,
                md5_objects=md5_objects,
                provenance_data=provenance_metadata
            )
            self.log(f"Provenance file created at: {provenance_file}")
        except Exception as e:
            self.log(f"Warning: Model saved but provenance creation failed: {str(e)}")

        # Track in job_data
        try:
            job_data = self._job.get_job_data()
            model_list = []
            if isinstance(job_data, dict):
                existing = job_data.get("models", [])
                if isinstance(existing, list):
                    model_list = existing
            model_list.append(dest)
            self._job.update_job_data_field("models", model_list)
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


