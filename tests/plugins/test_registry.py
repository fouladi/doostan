from collections.abc import Callable
from pathlib import Path

import pytest

from doost.address import Address
from doost.plugins.io import ProgressCallback
from doost.plugins.registry import get, register


class DummyPlugin:
    format = "dummy"

    def import_data(
        self,
        path: Path,
        session_factory: Callable[[], object],
        progress_callback: ProgressCallback | None = None,
    ) -> None: ...

    def export_data(
        self,
        path: Path,
        addresses: list[Address],
        progress_callback: ProgressCallback | None = None,
    ) -> None: ...


def test_register_and_get_plugin():
    plugin = DummyPlugin()
    register(plugin)

    retrieved = get("dummy")
    assert retrieved is plugin


def test_unknown_plugin():
    with pytest.raises(ValueError):
        get("does-not-exist")


def test_register_duplicate_raises() -> None:
    """Registering a plugin with an already-used format name must raise."""

    class AnotherDummy:
        format = "dummy"  # same format as DummyPlugin registered above

        def import_data(
            self,
            path: Path,
            session_factory: Callable[[], object],
            progress_callback: ProgressCallback | None = None,
        ) -> None: ...

        def export_data(
            self,
            path: Path,
            addresses: list[Address],
            progress_callback: ProgressCallback | None = None,
        ) -> None: ...

    with pytest.raises(ValueError, match="Plugin already registered: dummy"):
        register(AnotherDummy())
