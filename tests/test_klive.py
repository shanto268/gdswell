# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import klayout.db as kdb
import pytest

import gdswell as gw
import gdswell.klive as klive


class _CaptureSocket:
    def __init__(self, messages: list[dict[str, Any]]):
        self.messages = messages

    def __enter__(self) -> _CaptureSocket:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        self.messages.append(json.loads(data.decode()))


def _capture_klive_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    def make_temp_file(suffix: str) -> tuple[int, str]:
        assert suffix == ".gds"
        return os.open(path, os.O_CREAT | os.O_RDWR), str(path)

    monkeypatch.setattr(klive.tempfile, "mkstemp", make_temp_file)
    monkeypatch.setattr(
        klive.socket,
        "create_connection",
        lambda *args, **kwargs: _CaptureSocket(messages),
    )
    return messages


def _build_layout() -> tuple[gw.Layout, gw.Cell]:
    layout = gw.Layout()
    with layout:
        child = gw.Cell()
        child.kdb.name = "child"
        child.freeze()

        selected = gw.Cell()
        selected.add_ref(child)
        selected.kdb.name = "selected"
        selected.freeze()

        unrelated = gw.Cell()
        unrelated.kdb.name = "unrelated"
        unrelated.freeze()

    return layout, selected


def test_cell_show_streams_only_selected_hierarchy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    streamed_path = tmp_path / "cell.gds"
    messages = _capture_klive_file(monkeypatch, streamed_path)
    _layout, selected = _build_layout()

    selected.show()

    streamed = kdb.Layout()
    streamed.read(str(streamed_path))
    assert {cell.name for cell in streamed.each_cell()} == {"selected", "child"}
    assert messages == [{"gds": str(streamed_path), "top_cell": "selected"}]


def test_layout_show_still_streams_entire_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    streamed_path = tmp_path / "layout.gds"
    _capture_klive_file(monkeypatch, streamed_path)
    layout, _selected = _build_layout()

    layout.show()

    streamed = kdb.Layout()
    streamed.read(str(streamed_path))
    assert {cell.name for cell in streamed.each_cell()} == {"selected", "child", "unrelated"}
