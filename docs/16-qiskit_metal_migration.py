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
from gdswell.components.bend_circular import bend_circular
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    SIGNAL = (1, 0)
    GROUND_DRAWN = (2, 0)
    ETCH = (3, 0)
    GROUND_FINAL = (4, 0)
    QUBIT = (5, 0)
    JUNCTION = (6, 0)


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
# The basic Metal-style component is still an ordinary hierarchical cell that
# can be rendered directly in a notebook.

# %%
top

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
# ## A Qubit-Resonator-Feedline Design
#
# A common planar architecture contains three distinct pieces:
#
# 1. a CPW feedline for input and output signals;
# 2. a quarter-wave-style resonator coupled to the feedline by proximity; and
# 3. a two-pad transmon-like qubit coupled to the open end of the resonator.
#
# In GDSwell, the feedline and resonator are ordinary cells with CPW ports. The
# qubit is a polygon cell because its capacitive coupling is defined by spatial
# gaps rather than by a waveguide connection. The dimensions here are an
# educational layout example, not a fabrication-ready PDK or EM design.


# %%
@gw.cell
def feedline(length: float = 900.0) -> gw.Cell:
    """A straight CPW feedline with exposed input and output ports."""
    cell = gw.Cell()
    instance = cell.add_ref(straight(cpw, length=length))
    cell.add_port(instance["0"].renamed("input"))
    cell.add_port(instance["1"].renamed("output"))
    cell.add_info("role", "feedline")
    return cell


@gw.cell
def resonator(
    first_run: float = 220.0,
    vertical_run: float = 80.0,
    middle_run: float = 180.0,
    final_run: float = 100.0,
    radius: float = 20.0,
) -> gw.Cell:
    """A routed resonator with a feedline-side input and an open end."""
    cell = gw.Cell()
    first = cell.add_ref(straight(cpw, length=first_run))
    bend_1 = cell.add_ref_connected(bend_circular(cpw, radius=radius, angle=90.0), "0", first["1"])
    vertical = cell.add_ref_connected(straight(cpw, length=vertical_run), "0", bend_1["1"])
    bend_2 = cell.add_ref_connected(
        bend_circular(cpw, radius=radius, angle=-90.0), "0", vertical["1"]
    )
    middle = cell.add_ref_connected(straight(cpw, length=middle_run), "0", bend_2["1"])
    bend_3 = cell.add_ref_connected(bend_circular(cpw, radius=radius, angle=90.0), "0", middle["1"])
    vertical_2 = cell.add_ref_connected(straight(cpw, length=vertical_run), "0", bend_3["1"])
    bend_4 = cell.add_ref_connected(
        bend_circular(cpw, radius=radius, angle=-90.0), "0", vertical_2["1"]
    )
    open_end = cell.add_ref_connected(straight(cpw, length=final_run), "0", bend_4["1"])

    cell.add_port(first["0"].renamed("coupling"))
    cell.add_port(open_end["1"].renamed("open_end"))
    cell.add_info("role", "resonator")
    cell.add_info("length", first_run + vertical_run + middle_run + vertical_run + final_run)
    return cell


@gw.cell
def transmon_like_qubit(
    pad_width: float = 90.0,
    pad_height: float = 140.0,
    pad_gap: float = 12.0,
    junction_length: float = 12.0,
    junction_width: float = 0.2,
) -> gw.Cell:
    """Two capacitive pads joined by a small junction-layer bridge."""
    cell = gw.Cell()
    left = pad_gap / 2 + pad_width
    cell.add_polygon(
        [
            (-left, -pad_height / 2),
            (-pad_gap / 2, -pad_height / 2),
            (-pad_gap / 2, pad_height / 2),
            (-left, pad_height / 2),
        ],
        Layers.QUBIT,
    )
    cell.add_polygon(
        [
            (pad_gap / 2, -pad_height / 2),
            (left, -pad_height / 2),
            (left, pad_height / 2),
            (pad_gap / 2, pad_height / 2),
        ],
        Layers.QUBIT,
    )
    half_junction = junction_length / 2
    cell.add_polygon(
        [
            (-half_junction, -junction_width / 2),
            (half_junction, -junction_width / 2),
            (half_junction, junction_width / 2),
            (-half_junction, junction_width / 2),
        ],
        Layers.JUNCTION,
    )
    cell.add_info("role", "transmon-like qubit")
    return cell


@gw.cell
def qubit_resonator_feedline() -> gw.Cell:
    """Assemble the feedline, resonator, and qubit in one top cell."""
    cell = gw.Cell()
    feed = cell.add_ref(feedline(), origin=(0.0, 0.0))

    # Keep the resonator close to, but not connected to, the feedline.
    resonator_instance = cell.add_ref(resonator(), origin=(120.0, 45.0))

    # The qubit sits near the open resonator end; its capacitive gap is geometric.
    qubit_instance = cell.add_ref(transmon_like_qubit(), origin=(665.0, 330.0))

    cell.add_label("feedline", (25.0, -18.0), Layers.SIGNAL)
    cell.add_label("resonator", (130.0, 25.0), Layers.SIGNAL)
    cell.add_label("qubit", (620.0, 420.0), Layers.QUBIT)
    cell.add_info(
        "architecture",
        "CPW feedline, capacitively coupled resonator, transmon-like qubit",
    )
    cell.add_info("feedline_ports", list(feed.cell.ports))
    cell.add_info("resonator_ports", list(resonator_instance.cell.ports))
    cell.add_info("qubit_instance", qubit_instance.name)
    return cell


architecture = qubit_resonator_feedline()
print(f"Architecture instances: {len(architecture.instances)}")
print(f"Architecture bounding box: {architecture.bbox()}")

# %% [markdown]
# The resonator is intentionally not snapped to the feedline: the coupling is
# a designed gap. The qubit is likewise placed near the resonator's open end,
# where the pad geometry controls capacitive coupling. Use a dedicated EM flow
# to tune those gaps, lengths, materials, and junction representation.

# %%
architecture

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
