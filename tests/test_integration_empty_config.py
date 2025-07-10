import yaml
from data_curator_app import curator_core
from data_curator_app.sorter import sort_documents


def test_sorter_handles_empty_config(tmp_path, monkeypatch):
    # ensure state file is isolated
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(curator_core, "STATE_FILE", str(state_file))

    # create a sample document
    doc = tmp_path / "a.txt"
    doc.write_text("sample")

    # config stored outside documents directory
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    config_path = cfg_dir / "config.yaml"
    config = {
        "documents_dir": None,
        "ignore_files": [],
        "custom_rules": {},
    }
    config_path.write_text(yaml.safe_dump(config))

    monkeypatch.chdir(tmp_path)
    files = sort_documents(config_path)

    assert files == ["a.txt"]
