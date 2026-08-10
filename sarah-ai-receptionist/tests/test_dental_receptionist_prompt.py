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


def test_prompt_explicitly_forbids_diagnosis_and_medication_advice():
    """A healthcare-adjacent receptionist that never explicitly draws this
    line can drift into answering "is this an infection?" or "should I take
    ibuprofen?" as if general dentistry knowledge covers a specific caller's
    symptoms -- it doesn't, and doing so is medical advice. This pins the
    boundary's presence in every generated prompt, not just the default
    clinic's, since build_system_prompt is what every real clinic renders."""
    prompt = " ".join(build_system_prompt(_base_config()).split())
    assert "Never diagnose a condition" in prompt
    assert "never tell a caller what medication or dosage to take" in prompt
    assert "medical advice" in prompt
