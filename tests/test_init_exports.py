def test_exports():
    import lab

    assert hasattr(lab, "WORKSPACE_DIR")
    assert hasattr(lab, "HOME_DIR")
    assert hasattr(lab, "Job")
    assert hasattr(lab, "Experiment")
    assert hasattr(lab, "Model")

