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
# # Moving from Qiskit Metal to GDSwell
#
# Qiskit Metal and GDSwell both build hierarchical chip geometry in Python, but
# their central abstractions differ. Metal centers a mutable `QDesign` registry
# and class-based `QComponent`s. GDSwell centers immutable, content-addressed
# cells and explicit references in a KLayout database.

# %%
from enum import Enum

import gdswell as gw
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    SIGNAL = (1, 0)
    GROUND_DRAWN = (2, 0)
    ETCH = (3, 0)
    GROUND_FINAL = (4, 0)


# %% [markdown]
# ## Design and Component Mapping
#
# A Metal `DesignPlanar` owns components, QGeometry tables, pins, chips, and
# renderer state. A GDSwell `Layout` owns KLayout cells. The top-level design is
# an ordinary cell assembled from frozen component cells.


# %%
@gw.cell
def pad(width: float = 500.0, height: float = 300.0) -> gw.Cell:
    """A Metal-style rectangle rewritten with typed micron arguments."""
    cell = gw.Cell()
    cell.add_polygon(
        [
            (-width / 2, -height / 2),
            (width / 2, -height / 2),
            (width / 2, height / 2),
            (-width / 2, height / 2),
        ],
        Layers.SIGNAL,
    )
    return cell


top = gw.Cell()
top.add_ref(pad(), origin=(1_000.0, 500.0), rotation=90)
print(f"Top-level instances: {len(top.instances)}")

# %% [markdown]
# Metal's `pos_x`, `pos_y`, and `orientation` options become `add_ref`
# placement arguments. Component geometry stays reusable and location does not
# become part of the child definition.

# %% [markdown]
# ## Options and Units
#
# Metal commonly stores values such as `"10um"` in nested option dictionaries
# and parses them through `self.p`. GDSwell uses typed function parameters and
# expects public dimensions in microns.

# %%
microns = 2.0 * 1_000.0
large_pad = pad(width=microns, height=300.0)
print(f"Pad width: {large_pad.bbox().width()} microns")

# %% [markdown]
# There is no automatic design-variable parser. Convert units and evaluate
# variables before calling a cell function.

# %% [markdown]
# ## Pins Become Ports and Cross-Sections
#
# A Metal pin carries an edge, midpoint, normal, width, gap, chip, and mutable
# net ID. A GDSwell `Port` is an immutable local point with an outward Manhattan
# angle and a complete `CrossSection`.

# %%
cpw = gw.CrossSection(
    (
        gw.LayerSection("signal", Layers.SIGNAL, width=10.0),
        gw.LayerSection("gap_left", Layers.GROUND_DRAWN, width=6.0, offset=-8.0),
        gw.LayerSection("gap_right", Layers.GROUND_DRAWN, width=6.0, offset=8.0),
    )
)


@gw.cell
def lead(length: float = 100.0) -> gw.Cell:
    cell = gw.Cell()
    instance = cell.add_ref(straight(cpw, length=length))
    cell.add_port(instance["0"])
    cell.add_port(instance["1"])
    return cell


first = lead()
second_parent = gw.Cell()
first_instance = second_parent.add_ref(first)
second_instance = second_parent.add_ref_connected(lead(50.0), "0", first_instance["1"])
print(f"Port connection: {first_instance['1'].connects_to(second_instance['0'])}")

# %% [markdown]
# Cross-section equality is the compatibility check for a connection. A scalar
# Metal pin width is not enough to describe a multilayer CPW or photonic route.

# %% [markdown]
# ## Subtractive Geometry Becomes a Recipe
#
# Metal uses `subtract=True` rows that render against a ground plane. In GDSwell,
# the polarity is explicit in a Smart Layer expression.


# %%
@gw.cell
def raw_ground() -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [(-20.0, -20.0), (20.0, -20.0), (20.0, 20.0), (-20.0, 20.0)],
        Layers.GROUND_DRAWN,
    )
    cell.add_polygon([(-5.0, -2.0), (5.0, -2.0), (5.0, 2.0), (-5.0, 2.0)], Layers.ETCH)
    return cell


ground_mask = (Layers.GROUND_DRAWN - Layers.ETCH).onto(Layers.GROUND_FINAL)
final_ground = ground_mask(raw_ground())
print(f"Mapped mask frozen: {final_ground.frozen}")

# %% [markdown]
# This recipe is explicit and composable. It does not rely on a renderer
# interpreting a row-level subtract flag.

# %% [markdown]
# ## What Metal Users Must Supply
#
# GDSwell does not currently include Metal's GUI, unit-string parser, mutable
# component registry, QGeometry dataframe extensions, renderer registry, or
# built-in EPR/eigenmode/quantization analyses. It also does not provide every
# Metal route family, such as anchor-driven meanders and A* pathfinding.
#
# A migration therefore needs a PDK layer enum, cell factories, explicit mask
# recipes, a routing policy, and a separate owner for meshing and simulation.

# %% [markdown]
# ## Migration Checklist
#
# 1. Convert all Metal option values to micron-valued Python arguments.
# 2. Replace each `QComponent` subclass with a module-level `@gw.cell` function.
# 3. Move position and orientation into `add_ref` calls.
# 4. Replace pins with ports and complete cross-sections.
# 5. Replace `subtract=True` with Smart Layer boolean recipes.
# 6. Build and test a top-cell hierarchy instead of a global component registry.
# 7. Re-check route clearances against GDSwell's Manhattan L/Z/U constraints.
# 8. Choose a downstream package for stackup meshing and electromagnetic analysis.
