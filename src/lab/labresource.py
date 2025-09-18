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

    def _get_json_file(self):
        """Get json file containing metadata for this resource."""
        return os.path.join(self._get_dir(), "index.json")

    def _get_json_data(self):
        """
        Return the JSON data that is stored for this resource in the filesystem.
        If the file doesn't exist then return an empty dict.
        """
        json_file = self._get_json_file

        # Try opening this file location and parsing the json inside
        # On any error return an empty dict
        try:
            with open(json_file, "r", encoding="utf-8") as f:
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

        json_file = self._get_json_file
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False)

    def _get_json_data_field(self, key, default=""):
        json_data = self._get_json_data()
        return json_data.get(key, default)

    def _update_json_data_field(self, key: str, value):
        json_data = self._get_json_data()
        json_data[key] = value
        self._set_json_data(json_data)
