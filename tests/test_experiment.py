import os
import json
import importlib


def _fresh(monkeypatch):
    for mod in ["lab.experiment", "lab.job", "lab.dirs", "lab.dirs_workspace"]:
        if mod in importlib.sys.modules:
            importlib.sys.modules.pop(mod)


def test_experiment_dir_and_jobs_index(tmp_path, monkeypatch):
    _fresh(monkeypatch)
    home = tmp_path / ".tfl_home"
    ws = tmp_path / ".tfl_ws"
    home.mkdir()
    ws.mkdir()
    monkeypatch.setenv("TFL_HOME_DIR", str(home))
    monkeypatch.setenv("TFL_WORKSPACE_DIR", str(ws))

    from lab.experiment import Experiment
    from lab.job import Job

    exp = Experiment.create("exp1")
    exp_dir = exp.get_dir()
    assert exp_dir.endswith(os.path.join("experiments", "exp1"))
    assert os.path.isdir(exp_dir)

    # jobs.json created with default
    jobs_index_file = os.path.join(exp_dir, "jobs.json")
    assert os.path.isfile(jobs_index_file)
    with open(jobs_index_file) as f:
        data = json.load(f)
    assert "TRAIN" in data

    # Create two jobs and assign to experiment
    j1 = Job.create("10")
    j1.set_experiment("exp1")
    j2 = Job.create("11")
    j2.set_experiment("exp1")

    # Rebuild index should discover them
    exp.rebuild_jobs_index()
    all_jobs = exp._get_all_jobs()
    assert set(all_jobs) >= {"10", "11"}


def test_get_jobs_filters(tmp_path, monkeypatch):
    _fresh(monkeypatch)
    home = tmp_path / ".tfl_home"
    ws = tmp_path / ".tfl_ws"
    home.mkdir()
    ws.mkdir()
    monkeypatch.setenv("TFL_HOME_DIR", str(home))
    monkeypatch.setenv("TFL_WORKSPACE_DIR", str(ws))

    from lab.experiment import Experiment
    from lab.job import Job

    exp = Experiment.create("exp2")

    j1 = Job.create("21")
    j1.set_experiment("exp2")
    j1.update_status("RUNNING")

    j2 = Job.create("22")
    j2.set_experiment("exp2")
    j2.update_status("NOT_STARTED")

    exp.rebuild_jobs_index()
    # get all
    jobs = exp.get_jobs()
    assert isinstance(jobs, list)
    # filter by status
    running = exp.get_jobs(status="RUNNING")
    assert all(j.get("status") == "RUNNING" for j in running)

