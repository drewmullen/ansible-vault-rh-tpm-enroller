# -*- coding: utf-8 -*-
"""Convert duration strings such as 1h into seconds for the Vault TPM modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

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


def vault_tpm_seconds(value):
    """Return a duration as an integer number of seconds."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text == "":
        return None
    if _NUMBER_RE.match(text):
        return int(float(text))
    total = 0.0
    matched = False
    for number, unit in _DURATION_RE.findall(text):
        matched = True
        total += float(number) * _UNIT_SECONDS[unit]
    if not matched:
        return text
    return int(total)


class FilterModule(object):
    def filters(self):
        return {
            "vault_tpm_seconds": vault_tpm_seconds,
        }
