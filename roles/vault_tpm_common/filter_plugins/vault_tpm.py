# -*- coding: utf-8 -*-
"""Shared filters for the Vault TPM roles."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from ansible.errors import AnsibleFilterError

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

# Fields tpm_role accepts. Vault replaces a role with the fields in the write.
_ROLE_FIELDS = (
    "display_name",
    "cert_ttl",
    "tpm_ids",
    "tpmgroup_ids",
    "token_ttl",
    "token_max_ttl",
    "token_period",
    "token_explicit_max_ttl",
    "token_policies",
    "token_bound_cidrs",
    "token_no_default_policy",
    "token_num_uses",
    "token_type",
    "alias_metadata",
)
_DURATION_FIELDS = {
    "cert_ttl",
    "token_ttl",
    "token_max_ttl",
    "token_period",
    "token_explicit_max_ttl",
}


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


def _blank(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _assign(body, field, value, coerce):
    if field in _DURATION_FIELDS and coerce:
        value = vault_tpm_seconds(value)
    if _blank(value):
        return
    body[field] = value


def _id_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(item) for item in value if str(item).strip()]


def vault_tpm_role_body(existing, play, role_config, tpm_id):
    """Build a tpm_role body that keeps unset fields and appends one TPM id.

    Vault replaces the role with the fields in the write. Start from the current
    role, overlay play values, then overlay vault_tpm_role_config. tpm_ids are
    always the union of the current list, config ids, and this host's id.
    """
    host_id = "" if tpm_id is None else str(tpm_id).strip()
    if host_id == "":
        raise AnsibleFilterError("identity_tpm did not return a tpm_id")

    existing = existing or {}
    play = play or {}
    role_config = role_config or {}
    if not isinstance(existing, dict):
        raise AnsibleFilterError("existing TPM auth role must be a mapping")
    if not isinstance(play, dict) or not isinstance(role_config, dict):
        raise AnsibleFilterError("TPM auth role play values and vault_tpm_role_config must be mappings")

    for field in play:
        if field not in _ROLE_FIELDS or field == "tpm_ids":
            raise AnsibleFilterError("play field %r is not written by vault_tpm_enroll" % field)

    unknown = [field for field in role_config if field not in _ROLE_FIELDS]
    if unknown:
        known = ", ".join(_ROLE_FIELDS)
        raise AnsibleFilterError(
            "vault_tpm_role_config has unknown keys: %s. Known fields: %s" % (", ".join(unknown), known)
        )

    body = {}
    for field in _ROLE_FIELDS:
        if field == "tpm_ids" or field not in existing:
            continue
        _assign(body, field, existing[field], coerce=False)
    for field, value in play.items():
        _assign(body, field, value, coerce=True)
    for field, value in role_config.items():
        if field == "tpm_ids":
            continue
        _assign(body, field, value, coerce=True)

    ids = []
    for item in _id_list(existing.get("tpm_ids")) + _id_list(role_config.get("tpm_ids")) + [host_id]:
        if item not in ids:
            ids.append(item)
    body["tpm_ids"] = ids
    return body


def vault_tpm_missing(requirements):
    """Return labels for empty required values and non-HTTPS addresses."""
    missing = []
    for item in requirements or []:
        label = item["label"]
        value = item.get("value")
        if _blank(value):
            missing.append(label)
            continue
        if item.get("https") and not (isinstance(value, str) and value.startswith("https://")):
            missing.append("%s must start with https://" % label)
    return missing


class FilterModule(object):
    def filters(self):
        return {
            "vault_tpm_seconds": vault_tpm_seconds,
            "vault_tpm_role_body": vault_tpm_role_body,
            "vault_tpm_missing": vault_tpm_missing,
        }
