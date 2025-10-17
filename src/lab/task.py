import os
from datetime import datetime
from werkzeug.utils import secure_filename

from .dirs import get_tasks_dir
from .labresource import BaseLabResource


class Task(BaseLabResource):
    def get_dir(self):
        """Abstract method on BaseLabResource"""
        task_id_safe = secure_filename(str(self.id))
        return os.path.join(get_tasks_dir(), task_id_safe)

    def _default_json(self):
        # Default metadata modeled after API tasks table fields
        return {
            "id": self.id,
            "name": "",
            "type": "",
            "inputs": {},
            "config": {},
            "plugin": "",
            "outputs": {},
            "experiment_id": None,
            "remote_task": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def set_metadata(self, *, name: str | None = None, type: str | None = None, 
                     inputs: dict | None = None, config: dict | None = None,
                     plugin: str | None = None, outputs: dict | None = None,
                     experiment_id: str | None = None, remote_task: bool | None = None):
        """Set task metadata"""
        data = self.get_json_data()
        if name is not None:
            data["name"] = name
        if type is not None:
            data["type"] = type
        if inputs is not None:
            data["inputs"] = inputs
        if config is not None:
            data["config"] = config
        if plugin is not None:
            data["plugin"] = plugin
        if outputs is not None:
            data["outputs"] = outputs
        if experiment_id is not None:
            data["experiment_id"] = experiment_id
        if remote_task is not None:
            data["remote_task"] = remote_task
        
        # Always update the updated_at timestamp
        data["updated_at"] = datetime.utcnow().isoformat()
        
        self._set_json_data(data)

    def get_metadata(self):
        """Get task metadata"""
        return self.get_json_data()

    @staticmethod
    def list_all():
        """List all tasks in the filesystem"""
        results = []
        tasks_dir = get_tasks_dir()
        if not os.path.isdir(tasks_dir):
            return results
        for entry in os.listdir(tasks_dir):
            full = os.path.join(tasks_dir, entry)
            if not os.path.isdir(full):
                continue
            # Attempt to read index.json (or latest snapshot)
            try:
                task = Task(entry)
                results.append(task.get_metadata())
            except Exception:
                continue
        # Sort by created_at descending to match database behavior
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    @staticmethod
    def list_by_type(task_type: str):
        """List all tasks of a specific type"""
        all_tasks = Task.list_all()
        return [task for task in all_tasks if task.get("type") == task_type]

    @staticmethod
    def list_by_experiment(experiment_id: int):
        """List all tasks for a specific experiment"""
        all_tasks = Task.list_all()
        return [task for task in all_tasks if task.get("experiment_id") == experiment_id]

    @staticmethod
    def list_by_type_in_experiment(task_type: str, experiment_id: int):
        """List all tasks of a specific type in a specific experiment"""
        all_tasks = Task.list_all()
        return [task for task in all_tasks 
                if task.get("type") == task_type and task.get("experiment_id") == experiment_id]

    @staticmethod
    def get_by_id(task_id: str):
        """Get a specific task by ID"""
        try:
            task = Task.get(task_id)
            return task.get_metadata()
        except FileNotFoundError:
            return None

    @staticmethod
    def delete_all():
        """Delete all tasks"""
        tasks_dir = get_tasks_dir()
        if not os.path.isdir(tasks_dir):
            return
        for entry in os.listdir(tasks_dir):
            full = os.path.join(tasks_dir, entry)
            if os.path.isdir(full):
                import shutil
                shutil.rmtree(full)
