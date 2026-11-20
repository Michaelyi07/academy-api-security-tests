"""Acceptance gate: every academy endpoint has >= 2 executed dimensions.
Runs last (file name z_) so the ledger is fully populated by pytest_sessionfinish.
"""
from __future__ import annotations

from tests import conftest as C
from tests.endpoints import ENDPOINTS


def test_coverage_matrix_complete() -> None:
    # This test runs during the call phase; all parametrized security tests in
    # tests/security/ are collected and executed before tests/ root files.
    thin = [(e.key, sorted(C.COVERAGE.get(e.key, set()))) for e in ENDPOINTS if len(C.COVERAGE.get(e.key, set())) < 2]
    assert not thin, f"endpoints with <2 dimensions: {thin}"
