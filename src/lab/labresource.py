from abc import ABC, abstractmethod
import os
import json


class BaseLabResource(ABC):
    """
    Base object for all other resources to inherit from.

    This wraps the standard file-system structure and internal access functions.
    Lab resources have an associated directory and a json file with metadata.
    """

    def __init__(self, id):
        self.id = id

    @abstractmethod
    def _get_dir(self):
        """Get file system directory where this resource is stored."""
        pass

    def _get_json_data(self):
        """
        Return the JSON data that is stored for this resource in the filesystem.
        If the file doesn't exist then return an empty dict.
        """
        job_file = os.path.join(self._get_dir(), "index.json")

        # Try opening this file location and parsing the json inside
        # On any error return an empty dict
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _set_json_data(self, json_data):
        """
        Set the JSON data that is stored for this resource in the filesystem.
        This will overwrite whatever is stored now.
        If the file doesn't exist it will be created.

        Throws:
        TypeError if json_data is not of type dict
        """
        if not isinstance(json_data, dict):
            raise TypeError("json_data must be a dict")

        job_file = os.path.join(self._get_dir(), "index.json")
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False)
