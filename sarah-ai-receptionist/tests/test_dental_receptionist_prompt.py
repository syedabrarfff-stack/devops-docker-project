import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.prompts.dental_receptionist import build_system_prompt


def _base_config(**overrides) -> dict:
    config = {
        "name": "Test Dental",
        "sarah_name": "Sarah",
        "services": ["cleanings"],
        "insurance_accepted": ["Delta Dental"],
    }
    config.update(overrides)
    return config


def test_providers_as_plain_names_still_render():
    prompt = build_system_prompt(_base_config(providers=["Dr. Aslam", "Dr. Chen"]))
    assert "Dr. Aslam, Dr. Chen" in prompt


def test_providers_with_specialty_render_the_specialty_so_sarah_can_match_complaints():
    prompt = build_system_prompt(
        _base_config(
            providers=[
                {"name": "Dr. Aslam", "specialty": "root canals and endodontics"},
                {"name": "Dr. Chen", "specialty": "orthodontics"},
            ]
        )
    )
    assert "Dr. Aslam (root canals and endodontics)" in prompt
    assert "Dr. Chen (orthodontics)" in prompt


def test_no_providers_key_does_not_crash_or_mention_dentists():
    prompt = build_system_prompt(_base_config())
    assert "Dentists on staff" not in prompt
