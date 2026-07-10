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
# # Layers and Cross-Sections
#
# GDSwell uses four related concepts to describe waveguide geometry. A `Layer`
# identifies a GDS layer, a `LayerSection` describes one strip, a
# `CrossSection` groups strips across a path, and a `CellSection` places a
# reusable cell periodically along that path.

# %%
from enum import Enum

import gdswell as gw
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    CORE = (1, 0)
    CLADDING = (2, 0)
    MARKER = (3, 0)


# %% [markdown]
# ## Layer
#
# A `Layer` is only a GDS layer/datatype pair. It does not contain a width or a
# path. Enums make those numeric pairs readable throughout a PDK.

# %%
print(Layers.CORE.as_tuple())
print(Layers.CLADDING.as_tuple())

# %% [markdown]
# ## LayerSection
#
# A `LayerSection` is one named strip in the transverse profile of a path. Its
# width and offset are measured in microns. The offset is perpendicular to the
# path centerline.

# %%
core = gw.LayerSection(name="core", layer=Layers.CORE, width=0.5)
clad_left = gw.LayerSection(
    name="clad_left",
    layer=Layers.CLADDING,
    width=2.0,
    offset=-1.25,
)
clad_right = gw.LayerSection(
    name="clad_right",
    layer=Layers.CLADDING,
    width=2.0,
    offset=1.25,
)

print(core)
print(clad_left)

# %% [markdown]
# ## CrossSection
#
# A `CrossSection` groups all strips that follow one centerline. It is also the
# physical interface carried by a `Port`, so connectivity compares the
# cross-section rather than one scalar width.

# %%
standard = gw.CrossSection((core, clad_left, clad_right))
print(standard.evaluate(0.0))

# %% [markdown]
# Width and offset may be functions of the normalized symbol `gw.S`. `S=0` is
# the beginning of a path and `S=1` is its end, regardless of physical length.

# %%
tapered = gw.CrossSection(
    (
        gw.LayerSection("core", Layers.CORE, width=0.5 + 0.5 * gw.S),
        gw.LayerSection("clad_left", Layers.CLADDING, width=2.0, offset=-1.25 - 0.5 * gw.S),
        gw.LayerSection("clad_right", Layers.CLADDING, width=2.0, offset=1.25 + 0.5 * gw.S),
    )
)

print(f"Core at start: {tapered.evaluate(0.0).layer_sections[0].width}")
print(f"Core at end: {tapered.evaluate(1.0).layer_sections[0].width}")

# %% [markdown]
# ## Transitions Match Names
#
# `CrossSection.transition()` matches sections by name. Matching sections
# interpolate width and offset; a section that exists at only one endpoint
# tapers from or to zero width.

# %%
wide = gw.CrossSection(
    (
        gw.LayerSection("core", Layers.CORE, width=2.0),
        gw.LayerSection("clad_left", Layers.CLADDING, width=4.0, offset=-3.0),
        gw.LayerSection("clad_right", Layers.CLADDING, width=4.0, offset=3.0),
    )
)
transition = standard.transition(wide)
print(transition.evaluate(0.5).layer_sections)

# %% [markdown]
# ## Periodic Cell Sections
#
# A `CellSection` is discrete geometry, not a strip. It repeats an existing
# cell at an arclength interval and can offset each placement from the path.


# %%
@gw.cell
def marker(size: float = 0.3) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [
            (-size / 2, -size / 2),
            (size / 2, -size / 2),
            (size / 2, size / 2),
            (-size / 2, size / 2),
        ],
        Layers.MARKER,
    )
    return cell


marked = gw.CrossSection(
    layer_sections=(gw.LayerSection("core", Layers.CORE, width=0.8),),
    cell_sections=(
        gw.CellSection(
            name="markers",
            cell=marker(),
            periodicity=5.0,
            x_offset_initial=2.0,
            x_offset_final=2.0,
            y_offset=2.0,
        ),
    ),
)

waveguide = straight(marked, length=25.0)
print(f"Periodic instances: {len(waveguide.instances)}")

# %% [markdown]
# Periodic cells are rotated to the nearest Manhattan tangent. They move with
# the path, but they are not interpolated by a cross-section transition.

# %%
try:
    standard.transition(marked)
except ValueError as error:
    print(f"Expected limitation: {error}")
