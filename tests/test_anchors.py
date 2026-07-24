# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
import klayout.db as kdb
import pytest

import gdswell as gw


@gw.cell
def _cell_with_anchors() -> gw.Cell:
    c = gw.Cell()
    c.add_anchor(gw.Anchor(name="a1", position=(10.0, 0.0)))
    c.add_anchor(gw.Anchor(name="a2", position=(0.0, 5.0)))
    return c


@gw.cell
def _cell_empty() -> gw.Cell:
    return gw.Cell()


def test_anchor_creation() -> None:
    a = gw.Anchor(name="a1", position=(10.0, 20.0))
    assert a.name == "a1"
    assert a.position == (10.0, 20.0)
    assert a.x == 10.0
    assert a.y == 20.0


def test_anchor_transformed() -> None:
    a = gw.Anchor(name="a1", position=(10.0, 0.0))
    # Rotate 90 degrees around origin, and translate by (5, 5)
    trans = kdb.DTrans(1, False, kdb.DVector(5.0, 5.0))
    a_trans = a.transformed(trans)

    # Original position (10, 0) rotated 90 degrees -> (0, 10). Then translated by (5, 5) -> (5, 15)
    assert a_trans.position[0] == pytest.approx(5.0)
    assert a_trans.position[1] == pytest.approx(15.0)
    assert a_trans.name == "a1"


def test_cell_add_anchor() -> None:
    with gw.Layout() as layout:
        c = layout.create_cell()
        a = gw.Anchor(name="a1", position=(0.0, 0.0))
        c.add_anchor(a)

        assert c.anchors["a1"] == a
        with pytest.raises(KeyError):
            c.anchors["nonexistent"]


def test_duplicate_anchor_error() -> None:
    with gw.Layout() as layout:
        c = layout.create_cell()
        a1 = gw.Anchor(name="a1", position=(0.0, 0.0))
        a2 = gw.Anchor(name="a1", position=(10.0, 0.0))

        c.add_anchor(a1)
        with pytest.raises(ValueError, match="Anchor 'a1' already exists"):
            c.add_anchor(a2)


def test_instance_anchors() -> None:
    with gw.Layout():
        top = gw.Layout.get_active().create_cell()
        c = _cell_with_anchors()
        inst = top.add_ref(c, origin=(5.0, 5.0), rotation=90)

        # "a1" is at (10, 0) in cell.
        # Rotated 90 degrees -> (0, 10), translated by (5, 5) -> (5, 15)
        assert inst.anchors["a1"].position[0] == pytest.approx(5.0)
        assert inst.anchors["a1"].position[1] == pytest.approx(15.0)

        # "a2" is at (0, 5) in cell.
        # Rotated 90 degrees -> (-5, 0), translated by (5, 5) -> (0, 5)
        assert inst.anchors["a2"].position[0] == pytest.approx(0.0)
        assert inst.anchors["a2"].position[1] == pytest.approx(5.0)


def test_anchor_persistence() -> None:
    with gw.Layout() as layout:
        c1 = _cell_with_anchors()

        # Restore from the KDB cell
        c2 = gw.Cell._from_kdb_cell(c1.kdb, layout=layout)

        assert "a1" in c2.anchors
        assert c2.anchors["a1"].position == (10.0, 0.0)
        assert "a2" in c2.anchors
        assert c2.anchors["a2"].position == (0.0, 5.0)


def test_frozen_enforcement_anchor() -> None:
    with gw.Layout() as layout:
        c1 = _cell_empty()

        # Restore cell which will auto-freeze it
        c2 = gw.Cell._from_kdb_cell(c1.kdb, layout=layout)
        assert c2.frozen

        with pytest.raises(RuntimeError, match="frozen"):
            c2.add_anchor(gw.Anchor("a2", (0.0, 0.0)))
