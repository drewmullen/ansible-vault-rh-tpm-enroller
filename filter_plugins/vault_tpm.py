# -*- coding: utf-8 -*-
"""Compare a desired Vault auth role body with the role Vault returned."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

_DURATION_KEYS = {
    "token_ttl",
    "token_max_ttl",
    "token_period",
    "token_explicit_max_ttl",
}
_UNIT_SECONDS = {
    "h": 3600.0,
    "m": 60.0,
    "s": 1.0,
    "ms": 0.001,
    "us": 1e-6,
    "µs": 1e-6,
    "ns": 1e-9,
}
_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)(ns|us|µs|ms|h|m|s)")
_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")


def _is_duration_key(key):
    text = str(key)
    return text in _DURATION_KEYS or text.endswith("_ttl") or text.endswith("_period")


def duration_seconds(value):
    """Return duration values as seconds. Leave other values unchanged."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    if _NUMBER_RE.match(text):
        return float(text)
    total = 0.0
    matched = False
    for number, unit in _DURATION_RE.findall(text):
        matched = True
        total += float(number) * _UNIT_SECONDS[unit]
    if not matched:
        return text
    return total


def _numbers_equal(left, right):
    try:
        return abs(float(left) - float(right)) < 0.001
    except (TypeError, ValueError):
        return False


def _values_differ(key, desired, existing):
    if key == "tpm_ids" and isinstance(desired, list) and isinstance(existing, list):
        return sorted(str(item) for item in desired) != sorted(str(item) for item in existing)
    if _is_duration_key(key):
        return not _numbers_equal(duration_seconds(desired), duration_seconds(existing))
    if isinstance(desired, dict):
        if not isinstance(existing, dict):
            return True
        return role_differs(desired, existing)
    if isinstance(desired, list):
        if not isinstance(existing, list) or len(desired) != len(existing):
            return True
        return any(_values_differ("", wanted, current) for wanted, current in zip(desired, existing))
    if isinstance(desired, bool):
        if isinstance(existing, str) and existing.lower() in ("true", "false"):
            return desired != (existing.lower() == "true")
        return desired != existing
    if _numbers_equal(desired, existing) and isinstance(desired, (int, float)) and not isinstance(desired, bool):
        return False
    return desired != existing


def role_differs(desired, existing):
    """True when any desired key differs from the role Vault currently stores."""
    if not isinstance(desired, dict):
        return True
    if not isinstance(existing, dict):
        existing = {}
    for key, value in desired.items():
        if key not in existing:
            if key == "token_no_default_policy" and value is False:
                continue
            return True
        if _values_differ(key, value, existing[key]):
            return True
    return False


class FilterModule(object):
    def filters(self):
        return {
            "vault_tpm_role_differs": role_differs,
        }
