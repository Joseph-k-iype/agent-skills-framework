"""Semver parsing/comparison used by skill publishing."""

from __future__ import annotations

import pytest

from app.api.errors import ValidationError
from app.services.skill_service import _semver


def test_parse_valid():
    assert _semver("1.2.3") == (1, 2, 3)


def test_ordering():
    assert _semver("0.2.0") > _semver("0.1.0")
    assert _semver("1.0.0") > _semver("0.9.9")


@pytest.mark.parametrize("bad", ["1.0", "v1.0.0", "1.2.x", ""])
def test_rejects_invalid(bad):
    with pytest.raises(ValidationError):
        _semver(bad)
