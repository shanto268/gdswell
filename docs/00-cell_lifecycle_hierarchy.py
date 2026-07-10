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
# # Cell Lifecycle and Hierarchy
#
# A decorated cell function is a reproducible geometry factory. GDSwell builds
# the cell, records its identity, freezes it, and can reuse it in memory or from
# the disk cache.

# %%
from enum import Enum

import gdswell as gw

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    DEVICE = (1, 0)


# %% [markdown]
# ## Building a Cell
#
# The function body receives ordinary Python values and creates a mutable
# `Cell`. Metadata should be attached while the cell is being built.


# %%
@gw.cell
def plate(width: float = 10.0, height: float = 4.0) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)], Layers.DEVICE)
    cell.add_info("dimensions_um", {"width": width, "height": height})
    return cell


one = plate()
two = plate()
three = plate(width=20.0)

print(f"Same arguments reuse identity: {one is two}")
print(f"Different arguments produce a new cell: {one is three}")
print(f"Generated name: {one.name}")
print(f"Metadata: {dict(one.info)}")

# %% [markdown]
# The generated name includes the function identity, serialized parameters, and
# a source hash. It is a cache identity, not a stable human-facing component
# name.

# %% [markdown]
# ## Frozen Cells
#
# A decorated call returns a frozen cell. Frozen cells can be referenced by
# other cells, but their polygons, ports, metadata, and instances cannot be
# changed.

# %%
try:
    one.add_polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)], Layers.DEVICE)
except RuntimeError as error:
    print(f"Expected frozen-cell error: {error}")

# %% [markdown]
# If a design needs a variation, call the factory with new arguments or create a
# new parent cell. Do not modify a cached child in place.

# %% [markdown]
# ## References Preserve Hierarchy
#
# `add_ref` places a frozen child without copying its geometry into the parent.
# This is the normal way to assemble a larger design.

# %%
top = gw.Cell()
top.add_ref(one, origin=(0.0, 0.0))
top.add_ref(one, origin=(0.0, 10.0))
top.add_ref(three, origin=(20.0, 0.0))

print(f"Top-level instances: {len(top.instances)}")
print(f"Top bounding box: {top.bbox()}")

# %% [markdown]
# Repeated references remain visible as one compact hierarchical layout.

# %%
top.layout.wait()
top

# %% [markdown]
# The two `one` references point to the same definition. KLayout can therefore
# keep repeated structures compact in memory and in exported GDS/OASIS files.

# %% [markdown]
# ## Module-Level Functions
#
# Decorated functions must be defined at module scope. This gives the source
# hasher a stable module and function identity for persistent caching.

# %% [markdown]
# A decorated function must return a new, unfrozen `Cell`. To compose one cell
# from another, call the child factory and add the result as a reference inside
# a new parent cell.


# %%
@gw.cell
def assembly() -> gw.Cell:
    cell = gw.Cell()
    cell.add_ref(plate(width=6.0, height=2.0))
    cell.add_ref(plate(width=3.0, height=8.0), origin=(10.0, 0.0))
    return cell


assembled = assembly()
print(f"Assembly children: {len(assembled.instances)}")

# %%
assembled

# %% [markdown]
# ## Exporting a Layout
#
# A `Cell.write()` call waits for pending work and writes the containing layout.
# The same layout can also be streamed to KLayout with `layout.show()` when the
# Klive plugin is available.

# %%
with gw.Layout(name="export_demo") as export_layout:
    export_top = gw.Cell()
    export_top.add_ref(assembly())
    export_layout.wait()
    print(f"Ready to export: {export_top.name}")
