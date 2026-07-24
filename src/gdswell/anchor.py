# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from functools import cached_property
from typing import Any

import klayout.db as kdb

ABS_TOL = 1000 * sys.float_info.epsilon


@dataclass(frozen=True)
class Anchor:
    """An anchor is a reference point in a cell with a position."""

    name: str
    position: tuple[float, float]

    @property
    def x(self) -> float:
        return self.position[0]

    @property
    def y(self) -> float:
        return self.position[1]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Anchor):
            return False
        return math.isclose(self.position[0], other.position[0], abs_tol=ABS_TOL) and math.isclose(
            self.position[1], other.position[1], abs_tol=ABS_TOL
        )

    @cached_property
    def _hash_string(self) -> str:
        """Cached deterministic string for hashing."""
        # Quantize position to match ABS_TOL tolerance in __eq__
        precision = max(0, int(math.ceil(-math.log10(ABS_TOL))))
        x_str = f"{self.position[0]:.{precision}f}"
        y_str = f"{self.position[1]:.{precision}f}"
        return f"Anchor({x_str},{y_str})"

    def __hash__(self) -> int:
        return hash(self._hash_string)

    def transformed(self, transformation: kdb.DTrans) -> Anchor:
        """Returns a new Anchor with the transformation applied."""
        x, y = self.position
        dpt = kdb.DPoint(x, y)
        trans_dpt = transformation * dpt
        return replace(self, position=(trans_dpt.x, trans_dpt.y))

    def renamed(self, new_name: str) -> Anchor:
        """Returns a new Anchor with a different name."""
        return replace(self, name=new_name)

    def to_dict(self) -> dict[str, Any]:
        """Returns a JSON-serializable dictionary representation of the anchor."""
        return {
            "name": self.name,
            "position": self.position,
        }
