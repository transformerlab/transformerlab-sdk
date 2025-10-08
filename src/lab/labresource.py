from abc import ABC, abstractmethod
import os
import json
import shutil
from datetime import datetime


class BaseLabResource(ABC):
    """
    Base object for all other resources to inherit from.

    This wraps the standard file-system structure and internal access functions.
    Lab resources have an associated directory and a json file with metadata.
    """

    def __init__(self, id):
        self.id = id

    @abstractmethod
    def get_dir(self):
        """Get file system directory where this resource is stored."""
        pass

    @classmethod
    def create(cls, id):
        """
        Default method to create a new entity and initialize it with defualt metadata.
        """
        newobj = cls(id)
        newobj._initialize()
        return newobj

    @classmethod
    def get(cls, id):
        """
        Default method to get entity if it exists in the file system.
        If the entity's directory doesn't exist then throw an error.
        If the entity's metadata file does not exist then create a default.
        """
        newobj = cls(id)
        resource_dir = newobj.get_dir()
        if not os.path.isdir(resource_dir):
            raise FileNotFoundError(
                f"Directory for {cls.__name__} with id '{id}' not found"
            )
        json_file = newobj._get_json_file()
        if not os.path.exists(json_file):
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(newobj._default_json(), f)
        return newobj

    ###
    # INTERNAL METHODS
    # There are used by all subclasses to initialize, get and set JSON data
    ###

    def _initialize(self):
        """
        Default function to initialize the file system and json object.
        To alter the default metadata update the _default_json method.
        """

        # Create directory for this resource
        dir = self.get_dir()
        os.makedirs(dir, exist_ok=True)

        # Create a default json file. Throw an error if one already exists.
        json_file = self._get_json_file()
        if os.path.exists(json_file):
            raise FileExistsError(
                f"{type(self).__name__} with id '{self.id}' already exists"
            )
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self._default_json(), f)

    def _default_json(self):
        """Override in subclasses to support the initialize method."""
        return {"id": self.id}

    def _get_json_file(self):
        """Get json file containing metadata for this resource."""
        return os.path.join(self.get_dir(), "index.json")


    def get_json_data(self):
        """
        Return the JSON data that is stored for this resource in the filesystem.
        If the file doesn't exist then return an empty dict.
        """
        # Migrate from timestamped files to single index.json if needed
        self._migrate_to_single_index()
        
        json_file = self._get_json_file()

        # Try opening this file location and parsing the json inside
        # On any error return an empty dict
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _set_json_data(self, json_data):
        """
        Sets the entire JSON data that is stored for this resource in the filesystem.
        This will overwrite whatever is stored now.
        If the file doesn't exist it will be created.

        Throws:
        TypeError if json_data is not of type dict
        """
        if not isinstance(json_data, dict):
            raise TypeError("json_data must be a dict")

        # Migrate from timestamped files to single index.json if needed
        self._migrate_to_single_index()

        # Write directly to index.json
        json_file = self._get_json_file()
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False)

    def _get_json_data_field(self, key, default=""):
        """Gets the value of a single top-level field in a JSON object"""
        json_data = self.get_json_data()
        return json_data.get(key, default)

    def _update_json_data_field(self, key: str, value):
        """Sets the value of a single top-level field in a JSON object"""
        json_data = self.get_json_data()
        json_data[key] = value
        self._set_json_data(json_data)

    def _migrate_to_single_index(self):
        """
        Migrate from timestamped index files to a single index.json file.
        This method is idempotent and safe to call multiple times.
        """
        resource_dir = self.get_dir()
        if not os.path.exists(resource_dir):
            return

        # Check if we already have a single index.json file
        index_file = self._get_json_file()
        if os.path.exists(index_file):
            # Check if there are any timestamped files to migrate
            has_timestamped_files = False
            for filename in os.listdir(resource_dir):
                if filename.startswith("index-") and filename.endswith(".json"):
                    has_timestamped_files = True
                    break
            
            if not has_timestamped_files:
                return  # Already migrated

        # Find the most recent timestamped file
        latest_file = None
        latest_timestamp = None
        
        # First, try to use latest.txt if it exists
        latest_txt_path = os.path.join(resource_dir, "latest.txt")
        if os.path.exists(latest_txt_path):
            try:
                with open(latest_txt_path, "r", encoding="utf-8") as lf:
                    latest_filename = lf.read().strip()
                    if latest_filename:
                        candidate_path = os.path.join(resource_dir, latest_filename)
                        if os.path.isfile(candidate_path):
                            latest_file = candidate_path
            except Exception:
                pass

        # If no latest.txt or file doesn't exist, find the most recent by timestamp
        if not latest_file:
            for filename in os.listdir(resource_dir):
                if filename.startswith("index-") and filename.endswith(".json"):
                    try:
                        # Extract timestamp from filename
                        timestamp_str = filename[6:-5]  # Remove "index-" and ".json"
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S%fZ")
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_file = os.path.join(resource_dir, filename)
                    except ValueError:
                        # Skip files with invalid timestamp format
                        continue

        # If we found a latest file, migrate it to index.json
        if latest_file and os.path.exists(latest_file):
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Write to index.json
                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                
                # Clean up timestamped files and latest.txt
                for filename in os.listdir(resource_dir):
                    if filename.startswith("index-") and filename.endswith(".json"):
                        os.remove(os.path.join(resource_dir, filename))
                
                if os.path.exists(latest_txt_path):
                    os.remove(latest_txt_path)
                    
            except Exception:
                # If migration fails, leave everything as is
                pass

    def delete(self):
        """
        Delete this resource by deleting the containing directory.
        TODO: We should change to soft delete
        """
        resource_dir = self.get_dir()
        if os.path.exists(resource_dir):
            shutil.rmtree(resource_dir)
