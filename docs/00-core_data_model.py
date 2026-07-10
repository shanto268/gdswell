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
# # Core Data Model
#
# GDSwell uses a small set of objects repeatedly. A `Layout` owns a KLayout
# database, a `Cell` defines reusable geometry, an `Instance` places that cell,
# and a `Port` describes how it connects to another component.

# %%
from enum import Enum

import gdswell as gw
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    DEVICE = (1, 0)


xs = gw.CrossSection((gw.LayerSection("device", Layers.DEVICE, width=2.0),))

# %% [markdown]
# ## Layouts Own Cells
#
# Every cell belongs to one `Layout`. A layout context makes that ownership
# explicit and isolates a design from other designs in the same Python process.

# %%
with gw.Layout(name="data_model") as layout:
    empty = gw.Cell()

print(f"Layout: {empty.layout.name}")
print(f"Database unit: {layout.kdb.dbu} microns")

# %% [markdown]
# Outside a context manager, GDSwell uses a global default layout. Use an
# explicit context when testing, exporting more than one design, or measuring
# cache behavior.

# %% [markdown]
# ## Cells and Instances
#
# A cell is a definition. An instance is one transformed reference to that
# definition inside another cell. Reusing a cell keeps repeated geometry
# hierarchical and compact.


# %%
@gw.cell
def labeled_block(width: float = 10.0, height: float = 5.0) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)],
        Layers.DEVICE,
    )
    cell.add_port(gw.Port("input", (0.0, height / 2), 180, xs))
    cell.add_port(gw.Port("output", (width, height / 2), 0, xs))
    cell.add_info("kind", "labeled block")
    return cell


with gw.Layout(name="hierarchy"):
    block = labeled_block()
    top = gw.Cell()
    left = top.add_ref(block, origin=(0.0, 0.0))
    right = top.add_ref(block, origin=(25.0, 0.0), rotation=90)

print(f"Same definition: {left.cell is right.cell}")
print(f"Instances in top cell: {len(top.instances)}")
print(f"Rotated output port: {right['output'].position}")

# %% [markdown]
# ## Visualizing the Hierarchy
#
# In a notebook, displaying a `Cell` renders its KLayout geometry as a PNG.

# %%
top.layout.wait()
top

# %% [markdown]
# `left.cell` and `right.cell` are the same frozen definition. The instances
# differ only by their transformations in the parent coordinate system.

# %% [markdown]
# ## Ports Belong to Cells
#
# A port is immutable and contains a name, a position, an outward Manhattan
# angle, and a complete `CrossSection`. Accessing a port through an instance
# transforms its position and angle into the parent's coordinate system.

# %%
with gw.Layout(name="ports"):
    source = straight(xs, length=20.0)
    parent = gw.Cell()
    source_instance = parent.add_ref(source, origin=(10.0, 4.0))
    print(source_instance["0"])
    print(source_instance["1"])

# %% [markdown]
# A child port is not a global net. It becomes part of a parent interface only
# when the parent explicitly exposes it with `add_port()`.

# %%
with gw.Layout(name="exposed_ports"):
    child = labeled_block()
    parent = gw.Cell()
    instance = parent.add_ref(child)
    parent.add_port(instance["input"].renamed("in"))
    parent.add_port(instance["output"].renamed("out"))
    print(list(parent.ports))

# %% [markdown]
# ## Future Cells
#
# When asynchronous generation is enabled, a cache miss returns a `FutureCell`
# proxy. It behaves like the eventual cell, but the first operation that needs
# realized geometry may wait for the background build.


# %%
@gw.cell
def async_block(size: float = 3.0) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [(0.0, 0.0), (size, 0.0), (size, size), (0.0, size)],
        Layers.DEVICE,
    )
    return cell


gw.config.async_cells = True
with gw.Layout(name="async_data_model") as async_layout:
    future = async_block(7.0)
    print(f"Returned type: {type(future).__name__}")
    async_layout.wait()
    print(f"Realized name: {future.name}")
gw.config.async_cells = False

# %% [markdown]
# `Layout.wait()` is the explicit synchronization point for all pending cells
# in that layout. Background failures are raised when the future is resolved.
