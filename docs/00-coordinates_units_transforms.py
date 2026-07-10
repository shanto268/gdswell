# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Coordinates, Units, and Transforms
#
# GDSwell's public geometry API uses microns and local cell coordinates. KLayout
# stores polygons on an integer database grid underneath, but users normally
# work with floating-point micron values.

# %%
from enum import Enum

import gdswell as gw
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    SIGNAL = (1, 0)


xs = gw.CrossSection((gw.LayerSection("signal", Layers.SIGNAL, width=1.0),))

# %% [markdown]
# ## Microns at the API Boundary
#
# `length=10.0` means 10 microns. GDSwell does not parse unit-bearing strings,
# so convert millimeters or nanometers before calling a component.

# %%
length_mm = 0.025
length_um = length_mm * 1_000.0
line = straight(xs, length=length_um)
print(f"Length in microns: {line.info['length']}")

# %% [markdown]
# The underlying layout exposes its database unit (`dbu`) in microns per integer
# grid step. Region operations and exported GDS/OASIS geometry use that grid.

# %%
print(f"KLayout database unit: {line.layout.kdb.dbu} microns")

# %% [markdown]
# ## Local Coordinates
#
# A component defines geometry around its own origin. `add_ref` chooses where
# that coordinate system appears in the parent.


# %%
@gw.cell
def local_block() -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0.0, 0.0), (8.0, 0.0), (8.0, 4.0), (0.0, 4.0)], Layers.SIGNAL)
    cell.add_port(gw.Port("left", (0.0, 2.0), 180, xs))
    cell.add_port(gw.Port("right", (8.0, 2.0), 0, xs))
    return cell


child = local_block()
parent = gw.Cell()
normal = parent.add_ref(child, origin=(10.0, 5.0))
rotated = parent.add_ref(child, origin=(30.0, 5.0), rotation=90)
mirrored = parent.add_ref(child, origin=(50.0, 5.0), mirror=True)

print(f"Normal right port: {normal['right'].position}")
print(f"Rotated right port: {rotated['right'].position}")
print(f"Mirrored right angle: {mirrored['right'].angle}")

# %% [markdown]
# Public placement rotations are Manhattan: `0`, `90`, `180`, and `270`.
# Arbitrary-angle placement is not currently supported by `Cell.add_ref()` or
# `add_ref_connected()`.

# %% [markdown]
# ## Connecting in Parent Coordinates
#
# `add_ref_connected` transforms the source component so one of its ports meets
# a target port already expressed in the parent coordinate system.

# %%
connected_parent = gw.Cell()
first = connected_parent.add_ref(straight(xs, length=10.0))
second = connected_parent.add_ref_connected(
    straight(xs, length=6.0),
    port_name="0",
    target_port=first["1"],
)

print(f"First output: {first['1'].position}")
print(f"Second input: {second['0'].position}")
print(f"Connected: {first['1'].connects_to(second['0'])}")

# %% [markdown]
# Port angles point outward. Therefore the input port of a component that is
# placed after another component normally points opposite the previous output.
