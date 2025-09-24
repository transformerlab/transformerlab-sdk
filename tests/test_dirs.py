import os
import importlib


def _fresh_import_dirs(monkeypatch):
    for mod in ["lab.dirs", "lab.dirs_workspace"]:
        if mod in importlib.sys.modules:
            importlib.sys.modules.pop(mod)
    from lab import dirs  # noqa: F401
    return importlib.import_module("lab.dirs")


def test_dirs_structure_created(monkeypatch, tmp_path):
    home = tmp_path / ".tfl_home"
    ws = tmp_path / ".tfl_ws"
    home.mkdir()
    ws.mkdir()
    monkeypatch.setenv("TFL_HOME_DIR", str(home))
    monkeypatch.setenv("TFL_WORKSPACE_DIR", str(ws))

    dirs = _fresh_import_dirs(monkeypatch)

    # Key directories exist
    assert os.path.isdir(dirs.EXPERIMENTS_DIR)
    assert os.path.isdir(dirs.JOBS_DIR)
    assert os.path.isdir(dirs.MODELS_DIR)
    assert os.path.isdir(dirs.DATASETS_DIR)
    assert os.path.isdir(dirs.TEMP_DIR)
    assert os.path.isdir(dirs.PROMPT_TEMPLATES_DIR)
    assert os.path.isdir(dirs.TOOLS_DIR)
    assert os.path.isdir(dirs.BATCHED_PROMPTS_DIR)
    assert os.path.isdir(dirs.GALLERIES_CACHE_DIR)


def test_experiment_and_job_helpers(monkeypatch, tmp_path):
    home = tmp_path / ".tfl_home"
    ws = tmp_path / ".tfl_ws"
    home.mkdir()
    ws.mkdir()
    monkeypatch.setenv("TFL_HOME_DIR", str(home))
    monkeypatch.setenv("TFL_WORKSPACE_DIR", str(ws))
    dirs = _fresh_import_dirs(monkeypatch)

    exp_dir = dirs.experiment_dir_by_name("My Exp")
    assert exp_dir.endswith(os.path.join("experiments", "My Exp"))

    job_dir = dirs.job_dir_by_experiment_and_id("My Exp", "001")
    assert os.path.isdir(job_dir)
    assert job_dir.endswith(os.path.join("experiments", "My Exp", "jobs", "001"))

    # New structure returns first
    out_dir = dirs.get_job_output_dir("My Exp", "001")
    assert out_dir == job_dir

