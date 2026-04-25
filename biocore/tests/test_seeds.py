"""Tests for biocore.seeds."""

from __future__ import annotations

import random

import pytest

from biocore.seeds import crc32_seed


def test_crc32_seed_deterministic_within_process():
    a = crc32_seed("obs-1", "salmon", 0)
    b = crc32_seed("obs-1", "salmon", 0)
    assert a == b


def test_crc32_seed_differs_with_different_parts():
    a = crc32_seed("obs-1", "salmon", 0)
    b = crc32_seed("obs-2", "salmon", 0)
    c = crc32_seed("obs-1", "trout", 0)
    d = crc32_seed("obs-1", "salmon", 1)
    assert len({a, b, c, d}) == 4


def test_crc32_seed_returns_32_bit_unsigned():
    seed = crc32_seed("obs-1", "salmon", 12345)
    assert isinstance(seed, int)
    assert 0 <= seed <= 0xFFFFFFFF


def test_crc32_seed_known_value_is_stable():
    """Property check — the CRC of a known input MUST stay
    constant across Python releases. If this test ever
    fails, biocore.seeds is producing non-portable seeds
    and existing test suites break."""
    seed = crc32_seed("triage4", 42)
    expected = 0x3564C16C  # zlib.crc32(b"triage4|42")
    assert seed == expected


def test_crc32_seed_works_with_random_random():
    rng = random.Random(crc32_seed("obs-1", "salmon", 0))
    drawn = [rng.random() for _ in range(5)]
    rng2 = random.Random(crc32_seed("obs-1", "salmon", 0))
    drawn2 = [rng2.random() for _ in range(5)]
    assert drawn == drawn2


def test_crc32_seed_rejects_no_parts():
    with pytest.raises(ValueError):
        crc32_seed()


def test_crc32_seed_accepts_arbitrary_types():
    """Non-string parts are converted via str() — supports
    the typical ``crc32_seed(string_id, enum_value, int)``
    call shape."""
    seed_a = crc32_seed("obs", 0)
    seed_b = crc32_seed("obs", 1)
    assert seed_a != seed_b
    # None / tuple / float all str()-able.
    seed_c = crc32_seed(None, (1, 2), 3.14)
    assert isinstance(seed_c, int)
