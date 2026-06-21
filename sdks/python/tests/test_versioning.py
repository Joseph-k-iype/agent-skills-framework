import pytest

from skill_sdk.versioning import SemVer, satisfies, resolve_latest, max_version, is_semver


class TestSemVer:
    def test_parse_full(self):
        v = SemVer("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_prerelease(self):
        v = SemVer("2.0.0-alpha.1")
        assert v.major == 2
        assert v.prerelease == "alpha.1"

    def test_parse_with_build(self):
        v = SemVer("1.0.0+build.42")
        assert v.major == 1
        assert v.build == "build.42"

    def test_invalid(self):
        with pytest.raises(ValueError):
            SemVer("not-a-version")

    def test_comparison(self):
        assert SemVer("1.0.0") < SemVer("2.0.0")
        assert SemVer("1.0.0") < SemVer("1.1.0")
        assert SemVer("1.0.0") < SemVer("1.0.1")
        assert SemVer("1.0.0") == SemVer("1.0.0")
        assert SemVer("1.0.0") <= SemVer("1.0.0")
        assert SemVer("2.0.0") > SemVer("1.0.0")

    def test_prerelease_less(self):
        assert SemVer("1.0.0-alpha") < SemVer("1.0.0")


class TestSatisfies:
    def test_exact(self):
        assert satisfies("1.0.0", "=1.0.0")
        assert not satisfies("1.0.1", "=1.0.0")

    def test_pin(self):
        assert satisfies("1.0.0", "1.0.0")
        assert not satisfies("1.0.1", "1.0.0")

    def test_caret(self):
        assert satisfies("1.3.0", "^1.0.0")
        assert satisfies("1.9.9", "^1.0.0")
        assert not satisfies("2.0.0", "^1.0.0")

    def test_tilde(self):
        assert satisfies("1.2.1", "~1.2.0")
        assert not satisfies("1.3.0", "~1.2.0")

    def test_gte(self):
        assert satisfies("2.0.0", ">=1.0.0")
        assert satisfies("1.0.0", ">=1.0.0")
        assert not satisfies("0.9.0", ">=1.0.0")

    def test_lte(self):
        assert satisfies("0.9.0", "<=1.0.0")
        assert satisfies("1.0.0", "<=1.0.0")
        assert not satisfies("1.1.0", "<=1.0.0")

    def test_range(self):
        assert satisfies("1.5.0", "1.0.0 - 2.0.0")
        assert not satisfies("2.1.0", "1.0.0 - 2.0.0")


class TestResolveLatest:
    def test_basic(self):
        v = resolve_latest(["1.0.0", "1.1.0", "2.0.0"], "^1.0.0")
        assert v == "1.1.0"

    def test_no_match(self):
        v = resolve_latest(["2.0.0", "3.0.0"], "^1.0.0")
        assert v is None

    def test_exact_match(self):
        v = resolve_latest(["1.0.0", "1.0.1", "1.1.0"], "=1.0.1")
        assert v == "1.0.1"

    def test_empty_list(self):
        v = resolve_latest([], "^1.0.0")
        assert v is None

    def test_unsorted_input(self):
        v = resolve_latest(["2.0.0", "1.5.0", "1.0.0"], "^1.0.0")
        assert v == "1.5.0"

    def test_mixed_constraint(self):
        versions = ["1.0.0", "1.5.0", "2.0.0", "2.5.0", "3.0.0"]
        v = resolve_latest(versions, ">=1.5.0 <3.0.0")
        assert v == "2.5.0"


class TestSemVerPrecedenceFixes:
    """Regression tests for SemVer precedence / equality bugs."""

    def test_build_metadata_ignored_in_equality(self):
        # SemVer §10: build metadata MUST be ignored when determining precedence.
        assert SemVer("1.0.0+build.1") == SemVer("1.0.0+build.2")
        assert SemVer("1.0.0+build.1") == SemVer("1.0.0")

    def test_numeric_prerelease_compared_numerically(self):
        # Lexical comparison would wrongly order "alpha.10" < "alpha.2".
        assert SemVer("1.0.0-alpha.2") < SemVer("1.0.0-alpha.10")
        assert SemVer("1.0.0-2") < SemVer("1.0.0-10")

    def test_numeric_lower_than_alphanumeric(self):
        assert SemVer("1.0.0-1") < SemVer("1.0.0-alpha")

    def test_more_prerelease_fields_wins(self):
        assert SemVer("1.0.0-alpha") < SemVer("1.0.0-alpha.1")

    def test_is_hashable(self):
        # __eq__ without __hash__ would make SemVer unhashable.
        assert len({SemVer("1.0.0"), SemVer("1.0.0+x"), SemVer("2.0.0")}) == 2


class TestCaretZeroSemantics:
    """Caret on 0.x has special upper bounds (npm semantics)."""

    def test_caret_zero_minor(self):
        # ^0.2.3 := >=0.2.3 <0.3.0  -> 0.9.0 must NOT satisfy.
        assert satisfies("0.2.5", "^0.2.3")
        assert not satisfies("0.9.0", "^0.2.3")
        assert not satisfies("0.3.0", "^0.2.3")

    def test_caret_zero_patch(self):
        # ^0.0.3 := >=0.0.3 <0.0.4
        assert satisfies("0.0.3", "^0.0.3")
        assert not satisfies("0.0.4", "^0.0.3")

    def test_caret_partial(self):
        # ^1 := >=1.0.0 <2.0.0 ; ^0 := >=0.0.0 <1.0.0
        assert satisfies("1.9.9", "^1")
        assert not satisfies("2.0.0", "^1")
        assert satisfies("0.9.0", "^0")
        assert not satisfies("1.0.0", "^0")


class TestTildePartial:
    def test_tilde_partial_minor(self):
        # ~1.2 := >=1.2.0 <1.3.0  (used to raise ValueError)
        assert satisfies("1.2.9", "~1.2")
        assert not satisfies("1.3.0", "~1.2")

    def test_tilde_partial_major(self):
        # ~1 := >=1.0.0 <2.0.0
        assert satisfies("1.5.0", "~1")
        assert not satisfies("2.0.0", "~1")


class TestPrereleaseRangeExclusion:
    def test_prerelease_excluded_from_caret(self):
        # 2.0.0-rc < 2.0.0 numerically, but must not satisfy ^1.0.0.
        assert not satisfies("2.0.0-rc.1", "^1.0.0")

    def test_prerelease_included_when_bound_has_prerelease(self):
        assert satisfies("1.0.0-rc.2", ">=1.0.0-rc.1")


class TestMaxVersion:
    def test_numeric_not_lexical(self):
        # Lexical max of these is "0.9.0"; SemVer max is "0.10.0".
        assert max_version(["0.9.0", "0.10.0", "0.2.0"]) == "0.10.0"

    def test_ignores_unparseable(self):
        assert max_version(["1.0.0", "garbage", "2.0.0"]) == "2.0.0"

    def test_empty(self):
        assert max_version([]) is None


class TestIsSemver:
    def test_full_semver_accepted(self):
        assert is_semver("1.0.0")
        assert is_semver("1.0.0-rc.1")
        assert is_semver("1.0.0-rc.1+build.5")

    def test_rejects_partial(self):
        assert not is_semver("1.0")
        assert not is_semver("v1.0.0")

    def test_rejects_leading_zeros(self):
        # Per the SemVer BNF, numeric identifiers must not have leading zeros.
        assert not is_semver("01.0.0")
        assert not is_semver("1.00.0")
        assert not is_semver("1.0.00")
        assert not is_semver("1.0.0-01")

    def test_accepts_alphanumeric_prerelease_with_leading_digit(self):
        # Only *purely numeric* identifiers are restricted — "0a" contains a
        # letter, so it's an alphanumeric identifier and leading zeros are fine.
        assert is_semver("1.0.0-0a")
        assert is_semver("1.0.0-0")
