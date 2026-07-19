"""Shared pytest configuration and fixtures for ptools tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is importable when running `pytest` from the repo root
# without needing to install the package.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import pytest


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    """Change into a temporary working directory for the duration of a test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point $HOME at a tmp dir so user-config writes don't pollute the real home.

    Autouse: every test gets this isolation without opting in. Tests that
    still request it explicitly (or re-point $HOME themselves for their
    own tmp dir, e.g. to reload a module with import-time config writes)
    keep working -- this only sets the starting value, and function-scoped
    fixtures are resolved once per test either way.

    Does not cover config writes that happen at *import* time (before
    this fixture body runs); see ``.ongoing/test-hardening/make-config-init-lazy-3.md``.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # Some code paths read $USER too; pin it so behavior is deterministic.
    monkeypatch.setenv("USER", "test-user")
    return tmp_path
