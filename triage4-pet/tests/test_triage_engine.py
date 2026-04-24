"""Tests for PetTriageEngine + synthetic submissions + demo."""

from __future__ import annotations

import pytest

from triage4_pet.core.models import PetObservation
from triage4_pet.pet_triage.species_profiles import profile_for
from triage4_pet.pet_triage.triage_engine import PetTriageEngine
from triage4_pet.sim.demo_runner import run_demo
from triage4_pet.sim.synthetic_submission import (
    demo_submissions,
    generate_observation,
)


# ---------------------------------------------------------------------------
# Species profiles
# ---------------------------------------------------------------------------


def test_profile_for_dog():
    p = profile_for("dog")
    assert p.species == "dog"


def test_profile_for_cat_is_more_conservative_than_dog():
    """Cats hide pain aggressively — see_today threshold should
    be higher (fires sooner) for cats than for dogs."""
    dog = profile_for("dog")
    cat = profile_for("cat")
    assert cat.see_today_threshold > dog.see_today_threshold


def test_profile_for_rabbit_is_most_conservative():
    """Rabbits mask illness most severely — most conservative
    threshold in the library."""
    rabbit = profile_for("rabbit")
    dog = profile_for("dog")
    cat = profile_for("cat")
    horse = profile_for("horse")
    assert rabbit.see_today_threshold >= cat.see_today_threshold
    assert rabbit.see_today_threshold > dog.see_today_threshold
    assert rabbit.see_today_threshold > horse.see_today_threshold


def test_profile_for_unknown_raises():
    with pytest.raises(KeyError):
        profile_for("iguana")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


def test_engine_rejects_zero_weight_sum():
    with pytest.raises(ValueError):
        PetTriageEngine(weights={
            "pain": 0, "gait": 0, "respiratory": 0, "cardiac": 0,
        })


# ---------------------------------------------------------------------------
# Engine review — dual-audience output
# ---------------------------------------------------------------------------


def test_engine_healthy_dog_recommends_can_wait():
    obs = generate_observation(
        pet_token="P", species="dog", age_years=4.0, seed=1,
    )
    report = PetTriageEngine().review(obs)
    assert report.assessment.recommendation == "can_wait"
    # Always at least one owner message, even for can_wait.
    assert len(report.owner_messages) >= 1


def test_engine_limping_dog_recommends_at_least_routine():
    obs = generate_observation(
        pet_token="P", species="dog", gait_asymmetry=0.45,
        seed=2,
    )
    report = PetTriageEngine().review(obs)
    assert report.assessment.recommendation in ("routine_visit", "see_today")


def test_engine_multi_channel_distress_escalates_to_see_today():
    obs = generate_observation(
        pet_token="P", species="cat",
        pain_behavior_count=3, respiratory_elevation=0.7,
        gait_asymmetry=0.40, seed=3,
    )
    report = PetTriageEngine().review(obs)
    assert report.assessment.recommendation == "see_today"


def test_engine_cat_more_sensitive_than_dog():
    """Same observation in a cat should escalate sooner than
    in a dog — species profiles enforce this."""
    dog_obs = generate_observation(
        pet_token="P", species="dog",
        pain_behavior_count=2, respiratory_elevation=0.3,
        seed=4,
    )
    cat_obs = generate_observation(
        pet_token="P", species="cat",
        pain_behavior_count=2, respiratory_elevation=0.3,
        seed=4,
    )
    engine = PetTriageEngine()
    dog_report = engine.review(dog_obs)
    cat_report = engine.review(cat_obs)
    # Cat's recommendation should be at least as urgent as dog's.
    rec_order = {"can_wait": 0, "routine_visit": 1, "see_today": 2}
    assert rec_order[cat_report.assessment.recommendation] >= \
           rec_order[dog_report.assessment.recommendation]


def test_engine_overall_in_unit_interval():
    for seed in range(5):
        obs = generate_observation(
            pet_token=f"P{seed}", species="dog",
            gait_asymmetry=0.3, respiratory_elevation=0.3,
            cardiac_elevation=0.3, pain_behavior_count=1,
            seed=seed,
        )
        report = PetTriageEngine().review(obs)
        assert 0.0 <= report.assessment.overall <= 1.0


def test_engine_is_deterministic():
    a = generate_observation(
        pet_token="det", species="dog", gait_asymmetry=0.3,
        pain_behavior_count=1, seed=11,
    )
    b = generate_observation(
        pet_token="det", species="dog", gait_asymmetry=0.3,
        pain_behavior_count=1, seed=11,
    )
    ra = PetTriageEngine().review(a)
    rb = PetTriageEngine().review(b)
    assert ra.assessment.overall == rb.assessment.overall
    assert ra.vet_summary.text == rb.vet_summary.text
    assert [m.text for m in ra.owner_messages] == \
           [m.text for m in rb.owner_messages]


def test_engine_video_quality_scales_confidence():
    """Poor video quality should blend gait + pain channels
    toward neutral — fused overall ends up HIGHER (less
    confident call either way)."""
    obs_good = generate_observation(
        pet_token="P", species="dog", gait_asymmetry=0.35,
        pain_behavior_count=1, video_quality="good", seed=7,
    )
    obs_occluded = generate_observation(
        pet_token="P", species="dog", gait_asymmetry=0.35,
        pain_behavior_count=1, video_quality="occluded", seed=7,
    )
    engine = PetTriageEngine()
    good_overall = engine.review(obs_good).assessment.overall
    occluded_overall = engine.review(obs_occluded).assessment.overall
    assert occluded_overall > good_overall


# ---------------------------------------------------------------------------
# Dual-audience output properties
# ---------------------------------------------------------------------------


def test_engine_always_emits_one_vet_summary():
    obs = generate_observation(pet_token="P", species="dog", seed=9)
    report = PetTriageEngine().review(obs)
    assert report.vet_summary.text  # non-empty


def test_engine_always_emits_at_least_one_owner_message():
    """Every recommendation tier yields at least a headline
    message. The owner is never left without context."""
    for rec_setup in [
        {"seed": 1},  # can_wait
        {"gait_asymmetry": 0.45, "seed": 2},  # routine_visit
        {
            "pain_behavior_count": 3, "respiratory_elevation": 0.7,
            "gait_asymmetry": 0.40, "seed": 3,
        },  # see_today
    ]:
        obs = generate_observation(pet_token="P", species="cat", **rec_setup)
        report = PetTriageEngine().review(obs)
        assert len(report.owner_messages) >= 1


def test_engine_vet_summary_can_contain_clinical_vocabulary():
    """Critical property — vet summary is PERMISSIVE on
    clinical vocab. An obviously lame dog's vet summary
    should contain clinical terminology."""
    obs = generate_observation(
        pet_token="P", species="dog",
        gait_asymmetry=0.55, seed=6,
    )
    report = PetTriageEngine().review(obs)
    low = report.vet_summary.text.lower()
    # One of these clinical tokens should appear.
    assert "lameness" in low or "asymmetry" in low


def test_engine_owner_messages_never_contain_clinical_jargon():
    """Critical property — every owner message has passed
    through the strict layperson guard at construction
    time. Demo-level property test: the whole demo's owner
    messages are free of blocked clinical tokens."""
    submissions = demo_submissions()
    engine = PetTriageEngine()
    for obs in submissions:
        report = engine.review(obs)
        for m in report.owner_messages:
            low = m.text.lower()
            for jargon in (
                "arthritis", "fracture", "infection", "tumor",
                "neoplasia", "cardiomyopathy", "diabetes",
                "seizure", "stroke",
            ):
                assert jargon not in low


# ---------------------------------------------------------------------------
# Synthetic submissions + demo runner
# ---------------------------------------------------------------------------


def test_generate_observation_rejects_bad_args():
    with pytest.raises(ValueError):
        generate_observation(gait_asymmetry=2.0)
    with pytest.raises(ValueError):
        generate_observation(respiratory_elevation=-0.1)
    with pytest.raises(ValueError):
        generate_observation(cardiac_elevation=2.0)
    with pytest.raises(ValueError):
        generate_observation(pain_behavior_count=-1)
    with pytest.raises(ValueError):
        generate_observation(pain_behavior_count=10)
    with pytest.raises(ValueError):
        generate_observation(window_duration_s=-5)


def test_demo_submissions_length():
    assert len(demo_submissions()) == 5


def test_demo_submissions_cover_all_species():
    species_seen = {sub.species for sub in demo_submissions()}
    assert species_seen == {"dog", "cat", "horse", "rabbit"}


def test_demo_submissions_is_deterministic():
    a = demo_submissions()
    b = demo_submissions()
    for oa, ob in zip(a, b):
        assert [s.limb_asymmetry for s in oa.gait_samples] == \
               [s.limb_asymmetry for s in ob.gait_samples]


def test_run_demo_covers_every_recommendation_tier():
    text = run_demo()
    for rec in ("can_wait", "routine_visit", "see_today"):
        assert rec in text


def test_run_demo_survives_dual_audience_claims_guards():
    # Every OwnerMessage + VetSummary is constructed through
    # its respective guard. Demo running cleanly = proof the
    # dual-audience guard holds end-to-end.
    text = run_demo()
    assert "VET SUMMARY" in text
    assert "OWNER MESSAGES" in text


def test_run_demo_owner_messages_never_reassure():
    """Property test: owner messages in the demo never contain
    reassurance phrases that would imply the owner can skip
    the vet."""
    text = run_demo().lower()
    # Split out the owner-messages sections and verify.
    for phrase in (
        "everything is fine",
        "your pet is fine",
        "no need to worry",
        "no vet visit needed",
    ):
        assert phrase not in text


def test_unsupported_species_is_gated_by_consumer_app():
    """PetObservation rejects unsupported species at
    construction — the library never tries to triage
    species it doesn't cover."""
    with pytest.raises(ValueError):
        PetObservation(
            pet_token="P",
            species="iguana",  # type: ignore[arg-type]
            window_duration_s=60.0,
        )
