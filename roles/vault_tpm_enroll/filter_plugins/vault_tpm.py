# -*- coding: utf-8 -*-
"""Re-export the shared Vault TPM filters."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
from pathlib import Path

_source = Path(__file__).resolve().parents[2] / "vault_tpm_common/filter_plugins/vault_tpm.py"
_spec = importlib.util.spec_from_file_location("vault_tpm_common_filter", _source)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


class FilterModule(object):
    def filters(self):
        return _module.FilterModule().filters()
