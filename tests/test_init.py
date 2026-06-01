import json

from kw_engine.init import init_workspace


def test_init_creates_structure(tmp_path):
    """init creates all required directories and files."""
    init_workspace(tmp_path)

    assert (tmp_path / ".kw" / "config.yaml").exists()
    assert (tmp_path / "memory" / "SCHEMA.md").exists()
    assert (tmp_path / "memory" / "index.json").exists()
    assert (tmp_path / "memory" / "papers").is_dir()
    assert (tmp_path / "memory" / "principles").is_dir()
    assert (tmp_path / "memory" / "synthesis").is_dir()
    assert (tmp_path / "memory" / "golden").is_dir()
    assert (tmp_path / "paper").is_dir()
    assert (tmp_path / "process" / "extract-template.md").exists()
    assert (tmp_path / "process" / "distill-rubric.md").exists()
    assert (tmp_path / "problems").is_dir()

    # Verify index.json is valid
    idx = json.loads((tmp_path / "memory" / "index.json").read_text())
    assert idx["version"] == 1
    assert idx["counters"]["principle"] == 0
    assert idx["papers"] == []


def test_init_idempotent(tmp_path):
    """Running init twice doesn't overwrite existing data."""
    init_workspace(tmp_path)

    # Add some data
    modified_index = json.dumps({
        "version": 1,
        "counters": {"principle": 5},
        "papers": [],
        "principles": [],
        "synthesis": {"last_run": None, "n_principles_at_last_run": 0},
    })
    (tmp_path / "memory" / "index.json").write_text(modified_index)

    # Re-init
    init_workspace(tmp_path)

    # Data should be preserved (not overwritten)
    idx = json.loads((tmp_path / "memory" / "index.json").read_text())
    assert idx["counters"]["principle"] == 5


def test_init_config_has_required_keys(tmp_path):
    """Config must have model_routing and fetch sections."""
    init_workspace(tmp_path)
    import yaml
    config = yaml.safe_load((tmp_path / ".kw" / "config.yaml").read_text())
    assert "model_routing" in config
    assert "fetch" in config
    assert config["model_routing"]["kw-reader"] == "sonnet"
