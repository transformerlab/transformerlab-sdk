import os
from werkzeug.utils import secure_filename

from .dirs import get_config_dir
from .labresource import BaseLabResource


class Config(BaseLabResource):
    def get_dir(self):
        key_safe = secure_filename(str(self.id))
        return os.path.join(get_config_dir(), key_safe)

    def _default_json(self):
        return {"key": self.id, "value": None}

    def set_value(self, value):
        data = self.get_json_data()
        data["value"] = value
        self._set_json_data(data)

    def get_value(self):
        data = self.get_json_data()
        return data.get("value", None)

    @staticmethod
    def get_value_by_key(key: str):
        try:
            item = Config.get(key)
        except FileNotFoundError:
            return None
        return item.get_value()

    @staticmethod
    def set_value_by_key(key: str, value):
        try:
            item = Config.get(key)
        except FileNotFoundError:
            item = Config.create(key)
        item.set_value(value)


