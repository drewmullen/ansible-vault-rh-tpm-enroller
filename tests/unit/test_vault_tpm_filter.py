# -*- coding: utf-8 -*-
"""Unit tests for the shared Vault TPM filters."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import unittest
from pathlib import Path

from ansible.errors import AnsibleFilterError

_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "roles/vault_tpm_common/filter_plugins/vault_tpm.py"
)
_SPEC = importlib.util.spec_from_file_location("vault_tpm_common_filter", _SOURCE)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class VaultTpmFilterTest(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(_MODULE.vault_tpm_seconds("1h"), 3600)
        self.assertEqual(_MODULE.vault_tpm_seconds("1h30m"), 5400)
        self.assertEqual(_MODULE.vault_tpm_seconds(90), 90)
        self.assertEqual(_MODULE.vault_tpm_seconds("15"), 15)
        self.assertIsNone(_MODULE.vault_tpm_seconds(""))
        self.assertIsNone(_MODULE.vault_tpm_seconds(None))

    def test_missing_inputs(self):
        missing = _MODULE.vault_tpm_missing(
            [
                {"label": "vault_tpm_api_addr", "value": "http://vault", "https": True},
                {"label": "vault_tpm_role_name", "value": ""},
                {"label": "vault_tpm_token_policies", "value": []},
                {"label": "vault_tpm_proxy_addr", "value": "https://vault", "https": True},
            ]
        )
        self.assertEqual(
            missing,
            [
                "vault_tpm_api_addr must start with https://",
                "vault_tpm_role_name",
                "vault_tpm_token_policies",
            ],
        )

    def test_role_body_keeps_unset_fields_and_appends_id(self):
        body = _MODULE.vault_tpm_role_body(
            {
                "tpm_ids": ["a"],
                "tpmgroup_ids": ["g1"],
                "token_max_ttl": 7200,
                "token_policies": ["old"],
                "display_name": "app",
            },
            {
                "token_policies": ["app-read"],
                "token_ttl": "1h",
                "token_no_default_policy": False,
                "token_max_ttl": None,
                "token_period": "",
                "token_bound_cidrs": [],
            },
            {"cert_ttl": "1h", "tpm_ids": ["c"]},
            "b",
        )
        self.assertEqual(body["tpm_ids"], ["a", "c", "b"])
        self.assertEqual(body["tpmgroup_ids"], ["g1"])
        self.assertEqual(body["token_max_ttl"], 7200)
        self.assertEqual(body["token_policies"], ["app-read"])
        self.assertEqual(body["token_ttl"], 3600)
        self.assertEqual(body["cert_ttl"], 3600)
        self.assertIs(body["token_no_default_policy"], False)
        self.assertEqual(body["display_name"], "app")
        self.assertNotIn("token_period", body)
        self.assertNotIn("token_bound_cidrs", body)

    def test_role_body_drops_duplicate_ids(self):
        body = _MODULE.vault_tpm_role_body(
            {"tpm_ids": ["b", "a"]},
            {},
            {},
            "b",
        )
        self.assertEqual(body["tpm_ids"], ["b", "a"])

    def test_role_config_overrides_group_ids(self):
        body = _MODULE.vault_tpm_role_body(
            {"tpmgroup_ids": ["old"]},
            {},
            {"tpmgroup_ids": ["new"]},
            "id-1",
        )
        self.assertEqual(body["tpmgroup_ids"], ["new"])

    def test_role_body_requires_tpm_id(self):
        with self.assertRaises(AnsibleFilterError):
            _MODULE.vault_tpm_role_body({}, {}, {}, "  ")

    def test_role_config_rejects_unknown_keys(self):
        with self.assertRaises(AnsibleFilterError):
            _MODULE.vault_tpm_role_body({}, {}, {"not_a_field": 1}, "id-1")


if __name__ == "__main__":
    unittest.main()
