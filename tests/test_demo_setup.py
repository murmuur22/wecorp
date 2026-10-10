from pathlib import Path
import pytest
import setup_explorer_demo as demo


def test_standalone_demo_preflights_photo_inputs_without_partial_workspace(tmp_path):
    assert hasattr(demo, 'prepare_photos'), 'Standalone demo has no photo preparation step'
    missing = tmp_path / 'demo-inputs'
    with pytest.raises(ValueError, match='download-photos'):
        demo.prepare_photos(missing, download=False)
    assert not missing.exists()
    missing.mkdir()
    for name in demo.REFERENCES.values():
        (missing / name).write_bytes(b'cached reference fixture')
    demo.prepare_photos(missing, download=False)
    assert set(p.name for p in missing.iterdir()) == set(demo.REFERENCES.values())
