# -*- coding: utf-8 -*-

import json
import os
import hashlib
from fnmatch import fnmatch
from odoo import api, fields, models
from odoo.modules.module import get_module_path

PARAM_INSTALLED_CHECKSUMS = "module_auto_update.installed_checksums"
PARAM_EXCLUDE_PATTERNS = "module_auto_update.exclude_patterns"
DEFAULT_EXCLUDE_PATTERNS = "*.pyc,*.pyo,i18n/*.pot,i18n_extra/*.pot,static/*"

def _fnmatch(filename, patterns):
    for pattern in patterns:
        if fnmatch(filename, pattern):
            return True
    return False

def _walk(top, exclude_patterns, keep_langs):
    keep_langs = {l.split("_")[0] for l in keep_langs}
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames.sort()
        reldir = os.path.relpath(dirpath, top)
        if reldir == ".":
            reldir = ""
        for filename in sorted(filenames):
            filepath = os.path.join(reldir, filename)
            if _fnmatch(filepath, exclude_patterns):
                continue
            if keep_langs and reldir in {"i18n", "i18n_extra"}:
                basename, ext = os.path.splitext(filename)
                if ext == ".po":
                    if basename.split("_")[0] not in keep_langs:
                        continue
            yield filepath

def addon_hash(top, exclude_patterns, keep_langs):
    """Compute a sha1 digest of file contents."""
    m = hashlib.sha1()
    for filepath in _walk(top, exclude_patterns, keep_langs):
        # hash filename so empty files influence the hash
        m.update(filepath.encode("utf-8"))
        # hash file content
        with open(os.path.join(top, filepath), "rb") as f:
            m.update(f.read())
    return m.hexdigest()

class ConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def create_installed_checksums(self):
        self._save_installed_checksums()

    def _get_param(self, key, default=None):
        self.env.cr.execute("SELECT value FROM ir_config_parameter WHERE key=%s", (key,))
        result = self.env.cr.fetchone()
        return result and result[0] or default

    def _set_param(self, key, value):
        self.env.cr.execute("UPDATE ir_config_parameter SET value=%s WHERE key=%s", (value, key))
        if not self.env.cr.rowcount:
            self.env.cr.execute(
                "INSERT INTO ir_config_parameter (key, value) VALUES (%s, %s)", (key, value)
            )

    def _get_checksum_dir(self, module_name):
        exclude_patterns = self._get_param(PARAM_EXCLUDE_PATTERNS, DEFAULT_EXCLUDE_PATTERNS)
        exclude_patterns = [p.strip() for p in exclude_patterns.split(",")]
        self.env.cr.execute("SELECT code FROM res_lang WHERE active")
        keep_langs = [r[0] for r in self.env.cr.fetchall()]
        module_path = get_module_path(module_name)
        if module_path and os.path.isdir(module_path):
            checksum_dir = addon_hash(module_path, exclude_patterns, keep_langs)
        else:
            checksum_dir = False
        return checksum_dir

    def _save_installed_checksums(self):
        checksums = {}
        self.env.cr.execute("SELECT name FROM ir_module_module WHERE state='installed'")
        for (module_name,) in self.env.cr.fetchall():
            checksums[module_name] = self._get_checksum_dir(module_name)
        self._set_param(PARAM_INSTALLED_CHECKSUMS, json.dumps(checksums))