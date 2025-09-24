import os
from werkzeug.utils import secure_filename

from .dirs import MODELS_DIR
from .labresource import BaseLabResource


class Model(BaseLabResource):
    def import_model(self, model_name, model_path):
        """
        Given a model name and path, create a new model that can be used in the workspace.
        """
        pass

    def get_dir(self):
        """Abstract method on BaseLabResource"""
        model_id_safe = secure_filename(str(self.id))
        return os.path.join(MODELS_DIR, model_id_safe)
