"""Phase-one smoke tests for the shared test scaffold."""

from __future__ import annotations


def test_aegis_package_imports() -> None:
    import aegis

    assert "Aegis" in (aegis.__doc__ or "")
