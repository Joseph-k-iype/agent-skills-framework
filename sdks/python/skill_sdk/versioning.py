from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .validation import ValidationError

# Core ``MAJOR.MINOR.PATCH`` with optional ``-prerelease`` and ``+build`` metadata.
# Exposed (without anchors) so other modules can embed it in larger patterns
# (directory names, skill-id URIs, git tags) and keep one source of truth.
SEMVER_PATTERN = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
_FULL_SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


def is_semver(version: str) -> bool:
    return isinstance(version, str) and _FULL_SEMVER_RE.match(version) is not None


def _cmp_prerelease(a: str, b: str) -> int:
    """Compare two prerelease strings per SemVer §11.

    Empty prerelease (a release) has *higher* precedence than any prerelease.
    """
    if a == b:
        return 0
    if not a:
        return 1  # release > prerelease
    if not b:
        return -1
    a_ids = a.split(".")
    b_ids = b.split(".")
    for ai, bi in zip(a_ids, b_ids):
        a_num = ai.isdigit()
        b_num = bi.isdigit()
        if a_num and b_num:
            if int(ai) != int(bi):
                return -1 if int(ai) < int(bi) else 1
        elif a_num != b_num:
            # numeric identifiers always have lower precedence than alphanumeric
            return -1 if a_num else 1
        elif ai != bi:
            return -1 if ai < bi else 1
    # all shared identifiers equal -> the longer set has higher precedence
    if len(a_ids) != len(b_ids):
        return -1 if len(a_ids) < len(b_ids) else 1
    return 0


class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: str
    build: str

    def __init__(self, version: str):
        m = _FULL_SEMVER_RE.match(version.strip()) if isinstance(version, str) else None
        if not m:
            raise ValueError(f"Invalid SemVer: {version!r}")
        self.major = int(m.group("major"))
        self.minor = int(m.group("minor"))
        self.patch = int(m.group("patch"))
        self.prerelease = m.group("prerelease") or ""
        self.build = m.group("build") or ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        if self.build:
            base += f"+{self.build}"
        return base

    def __repr__(self) -> str:
        return f"SemVer({str(self)!r})"

    @property
    def _precedence(self) -> tuple:
        # Build metadata is explicitly ignored for precedence (SemVer §10).
        return (self.major, self.minor, self.patch)

    def _cmp(self, other: "SemVer") -> int:
        if self._precedence != other._precedence:
            return -1 if self._precedence < other._precedence else 1
        return _cmp_prerelease(self.prerelease, other.prerelease)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp(other) == 0

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def __lt__(self, other: "SemVer") -> bool:
        return self._cmp(other) < 0

    def __le__(self, other: "SemVer") -> bool:
        return self._cmp(other) <= 0

    def __gt__(self, other: "SemVer") -> bool:
        return self._cmp(other) > 0

    def __ge__(self, other: "SemVer") -> bool:
        return self._cmp(other) >= 0


# ---------------------------------------------------------------------------
# Constraint parsing / matching
# ---------------------------------------------------------------------------

_PARTIAL_RE = re.compile(
    r"^(?P<major>\d+|[xX*])"
    r"(?:\.(?P<minor>\d+|[xX*]))?"
    r"(?:\.(?P<patch>\d+|[xX*]))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


def _parse_partial(token: str):
    """Parse a possibly-partial version token (``1``, ``1.2``, ``1.2.3-rc``).

    Returns (major, minor, patch, prerelease, minor_spec, patch_spec) where the
    ``*_spec`` flags record whether the component was explicitly given (vs.
    defaulted to 0). ``x``/``*`` wildcards count as unspecified.
    """
    m = _PARTIAL_RE.match(token.strip())
    if not m:
        raise ValueError(f"Invalid version constraint token: {token!r}")

    def _num(part):
        if part is None or part in ("x", "X", "*"):
            return None
        return int(part)

    major = _num(m.group("major"))
    minor = _num(m.group("minor"))
    patch = _num(m.group("patch"))
    pre = m.group("prerelease") or ""
    if major is None:
        major = 0
    return (
        major,
        minor if minor is not None else 0,
        patch if patch is not None else 0,
        pre,
        minor is not None,
        patch is not None,
    )


def _sv(major: int, minor: int, patch: int, pre: str = "") -> SemVer:
    s = f"{major}.{minor}.{patch}"
    if pre:
        s += f"-{pre}"
    return SemVer(s)


def _allows_prerelease(v: SemVer, low: SemVer | None) -> bool:
    """A prerelease version only satisfies a range when the lower bound carries a
    prerelease on the *same* core triple (npm ``includePrerelease=false``)."""
    if not v.prerelease:
        return True
    if low is not None and low.prerelease and low._precedence == v._precedence:
        return True
    return False


def _satisfies_caret(v: SemVer, token: str) -> bool:
    major, minor, patch, pre, minor_spec, patch_spec = _parse_partial(token)
    low = _sv(major, minor, patch, pre)
    if major != 0:
        high = _sv(major + 1, 0, 0)
    elif not minor_spec:
        high = _sv(1, 0, 0)
    elif minor != 0:
        high = _sv(0, minor + 1, 0)
    elif not patch_spec:
        high = _sv(0, 1, 0)
    else:
        high = _sv(0, 0, patch + 1)
    return v >= low and v < high and _allows_prerelease(v, low)


def _satisfies_tilde(v: SemVer, token: str) -> bool:
    major, minor, patch, pre, minor_spec, patch_spec = _parse_partial(token)
    low = _sv(major, minor, patch, pre)
    if minor_spec:
        high = _sv(major, minor + 1, 0)
    else:
        high = _sv(major + 1, 0, 0)
    return v >= low and v < high and _allows_prerelease(v, low)


def _satisfies_comparator(v: SemVer, op: str, token: str) -> bool:
    major, minor, patch, pre, minor_spec, patch_spec = _parse_partial(token)
    bound = _sv(major, minor, patch, pre)
    if op == ">=":
        ok = v >= bound
    elif op == "<=":
        ok = v <= bound
    elif op == ">":
        ok = v > bound
    elif op == "<":
        ok = v < bound
    else:  # "="
        # Exact: a partial "=1.2" pins the given components only.
        if not minor_spec:
            ok = v.major == major
        elif not patch_spec:
            ok = (v.major, v.minor) == (major, minor)
        else:
            ok = v == bound
        return ok and _allows_prerelease(v, bound if pre else None)
    # For one-sided comparators, keep prerelease versions out unless the bound
    # itself is a prerelease sharing the core triple.
    return ok and _allows_prerelease(v, bound if pre else None)


def _satisfies_partial_pin(v: SemVer, token: str) -> bool:
    major, minor, patch, pre, minor_spec, patch_spec = _parse_partial(token)
    if minor_spec and patch_spec and not _has_wildcard(token):
        # Fully specified pin == exact match.
        return v == _sv(major, minor, patch, pre) and _allows_prerelease(
            v, _sv(major, minor, patch, pre) if pre else None
        )
    # Partial pin behaves like an x-range: >=low <next-unspecified-component.
    low = _sv(major, minor, patch)
    if not minor_spec:
        high = _sv(major + 1, 0, 0)
    elif not patch_spec:
        high = _sv(major, minor + 1, 0)
    else:
        high = _sv(major, minor, patch + 1)
    return v >= low and v < high and _allows_prerelease(v, None)


def _has_wildcard(token: str) -> bool:
    return any(c in token for c in ("x", "X", "*"))


def satisfies(version: str, constraint: str) -> bool:
    v = SemVer(version)
    constraint = constraint.strip()
    if not constraint or constraint in ("*", "x", "X", "latest"):
        return not v.prerelease

    # Hyphen range: "1.0.0 - 2.0.0"
    if " - " in constraint:
        lo_s, hi_s = (p.strip() for p in constraint.split(" - ", 1))
        lo_major, lo_minor, lo_patch, lo_pre, _, _ = _parse_partial(lo_s)
        low = _sv(lo_major, lo_minor, lo_patch, lo_pre)
        hi_major, hi_minor, hi_patch, hi_pre, hi_minor_spec, hi_patch_spec = _parse_partial(hi_s)
        if hi_minor_spec and hi_patch_spec:
            return low <= v <= _sv(hi_major, hi_minor, hi_patch, hi_pre) and _allows_prerelease(v, low)
        # Partial upper bound is inclusive of the whole component range.
        if not hi_minor_spec:
            high = _sv(hi_major + 1, 0, 0)
        else:
            high = _sv(hi_major, hi_minor + 1, 0)
        return low <= v < high and _allows_prerelease(v, low)

    # Whitespace/comma separated AND of multiple comparators.
    tokens = [t for t in re.split(r"[\s,]+", constraint) if t]
    if len(tokens) > 1:
        return all(satisfies(version, t) for t in tokens)

    if constraint.startswith("^"):
        return _satisfies_caret(v, constraint[1:])
    if constraint.startswith("~"):
        return _satisfies_tilde(v, constraint[1:])
    for op in (">=", "<=", ">", "<", "="):
        if constraint.startswith(op):
            return _satisfies_comparator(v, op, constraint[len(op):])
    return _satisfies_partial_pin(v, constraint)


def resolve_latest(versions: list[str], constraint: str) -> str | None:
    matching = []
    for ver in versions:
        try:
            if satisfies(ver, constraint):
                matching.append(ver)
        except ValueError:
            continue
    if not matching:
        return None
    matching.sort(key=SemVer)
    return matching[-1]


def max_version(versions: list[str]) -> str | None:
    """Return the highest valid SemVer string, ignoring unparseable entries."""
    parsed = []
    for ver in versions:
        try:
            parsed.append((SemVer(ver), ver))
        except ValueError:
            continue
    if not parsed:
        return None
    parsed.sort(key=lambda pair: pair[0])
    return parsed[-1][1]


def find_repo_root(start: str | Path) -> Path | None:
    """Walk up from ``start`` looking for the nearest ``.git`` directory."""
    start = Path(start)
    for parent in [start] + list(start.parents):
        if (parent / ".git").exists():
            return parent
    return None


def git_tag_skill(name: str, version: str, skill_id: str, repo_root: str | Path) -> None:
    tag = f"skill/{name}/{version}"
    msg = f"Skill: {name}@{version}\nID: {skill_id}"

    try:
        subprocess.run(
            ["git", "tag", "-a", tag, "-m", msg],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        if "already exists" in (e.stderr or ""):
            raise ValidationError(f"Git tag '{tag}' already exists")
        raise ValidationError(f"Git tag failed: {(e.stderr or '').strip()}")
    except FileNotFoundError:
        raise ValidationError("Git not found — cannot create tag")


def git_tag_exists(name: str, version: str, repo_root: str | Path) -> bool:
    tag = f"skill/{name}/{version}"
    try:
        result = subprocess.run(
            ["git", "tag", "-l", tag],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    # Exact match: ``git tag -l <pattern>`` treats the arg as a glob, and a
    # naive substring test would let ``skill/a/1.0`` match ``skill/a/1.0.0``.
    return tag in result.stdout.split()
