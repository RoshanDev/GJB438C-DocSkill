from __future__ import annotations

"""Load self-contained GJB 438C document profiles.

The runtime never needs the repository-level DOCX template bundle.  Each YAML
profile contains the extracted chapter outline plus this repository's writing,
evidence, traceability and volume policy for one document type.
"""

from copy import deepcopy
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import yaml

from .profile_catalog import TIERS


class ProfileError(RuntimeError):
    pass


def _profile_name(code: str) -> str:
    return f"{code.strip().lower()}.yaml"


def profile_directory() -> Path:
    return Path(__file__).resolve().parent / "data" / "profiles"


def _validate_profile(value: Any, *, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"文档 Profile 必须是 YAML 对象：{source}")
    required = (
        "schema_version",
        "code",
        "document_name",
        "purpose",
        "outline",
        "artifact_contracts",
        "volume_policy",
        "release_rules",
    )
    missing = [key for key in required if key not in value]
    if missing:
        raise ProfileError(f"文档 Profile 缺少字段 {missing}：{source}")
    code = str(value["code"]).strip().upper()
    if not code:
        raise ProfileError(f"文档 Profile code 为空：{source}")
    outline = value.get("outline")
    if not isinstance(outline, list) or not outline:
        raise ProfileError(f"文档 Profile outline 为空：{source}")
    for index, heading in enumerate(outline, 1):
        if not isinstance(heading, dict):
            raise ProfileError(f"outline[{index}] 不是对象：{source}")
        level = heading.get("level")
        title = heading.get("title")
        if not isinstance(level, int) or not 1 <= level <= 9 or not str(title or "").strip():
            raise ProfileError(f"outline[{index}] 非法：{source}")
    contracts = value.get("artifact_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise ProfileError(f"文档 Profile artifact_contracts 为空：{source}")
    policy = value.get("volume_policy")
    if not isinstance(policy, dict) or any(tier not in policy for tier in TIERS):
        raise ProfileError(f"文档 Profile volume_policy 不完整：{source}")
    value["code"] = code
    return value


@lru_cache(maxsize=None)
def load_profile(code: str) -> dict[str, Any]:
    """Return a defensive copy of a packaged profile."""
    normalized = code.strip().upper()
    filename = _profile_name(normalized)
    local = profile_directory() / filename
    if local.is_file():
        raw = local.read_text(encoding="utf-8")
        return deepcopy(_validate_profile(yaml.safe_load(raw), source=str(local)))

    # Wheel/zip import fallback.
    try:
        resource = resources.files("gjb438c_suite").joinpath("data", "profiles", filename)
        raw = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise ProfileError(
            f"未找到 {normalized} 的内置文档 Profile。请重新安装完整的 gjb438c-md-first skill。"
        ) from exc
    return deepcopy(_validate_profile(yaml.safe_load(raw), source=str(resource)))


def iter_profiles() -> Iterable[dict[str, Any]]:
    from .registry import iter_document_types

    for item in iter_document_types():
        yield load_profile(item.code)


def outline_for(code: str) -> list[dict[str, Any]]:
    return deepcopy(load_profile(code)["outline"])


def volume_policy_for(code: str, tier: str) -> dict[str, Any]:
    profile = load_profile(code)
    normalized = tier.strip().lower()
    if normalized not in TIERS:
        raise ProfileError(f"未知规模档位 {tier!r}；支持：{', '.join(TIERS)}")
    return deepcopy(profile["volume_policy"][normalized])


def artifact_contracts_for(code: str) -> list[dict[str, Any]]:
    return deepcopy(load_profile(code)["artifact_contracts"])
