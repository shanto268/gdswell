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
# # Paths and Symbolic Geometry
#
# GDSwell generates waveguides by sampling a centerline and offsetting it with
# a `CrossSection`. Built-in components provide optimized evaluators, while
# `generic_path` accepts SymPy expressions for arbitrary paths.

# %%
from enum import Enum

import gdswell as gw
from gdswell.components.generic_path import generic_path
from gdswell.components.straight import straight

gw.config.async_cells = False


class Layers(gw.Layer, Enum):
    CORE = (1, 0)
    CLADDING = (2, 0)


xs = gw.CrossSection(
    (
        gw.LayerSection("core", Layers.CORE, width=0.5),
        gw.LayerSection("clad", Layers.CLADDING, width=2.0),
    )
)

# %% [markdown]
# ## The Normalized Parameter S
#
# `gw.S` is a SymPy symbol that runs from `0` at the path start to `1` at the
# path end. It is a parameter, not a distance in microns.

# %%
taper = gw.CrossSection(
    (
        gw.LayerSection("core", Layers.CORE, width=0.5 + gw.S),
        gw.LayerSection("clad", Layers.CLADDING, width=2.0 + 2.0 * gw.S),
    )
)

print(f"Start width: {taper.evaluate(0.0).layer_sections[0].width}")
print(f"End width: {taper.evaluate(1.0).layer_sections[0].width}")

# %% [markdown]
# For a 200-micron straight, `S=0.5` corresponds to 100 microns. On a curved
# path, the physical midpoint depends on the path speed.

# %% [markdown]
# ## A Generic Smooth Path
#
# `generic_path` itself is a low-level constructor that returns a mutable cell.
# Wrap it in a module-level `@gw.cell` function when the path should participate
# in GDSwell's normal freezing and caching lifecycle.


# %%
@gw.cell
def smooth_path(length: float = 40.0, amplitude: float = 3.0) -> gw.Cell:
    x_expr = length * gw.S
    # Smoothstep has zero slope at both endpoints, so both ports are horizontal.
    y_expr = amplitude * (3 * gw.S**2 - 2 * gw.S**3)
    return generic_path(xs, x_expr=x_expr, y_expr=y_expr, npoints=200)


s_curve = smooth_path()
print(f"Smooth path length: {s_curve.info['length']:.3f} microns")
print(f"Start port: {s_curve['0'].position}, end port: {s_curve['1'].position}")

# %% [markdown]
# The `npoints` argument controls polygon discretization. More samples better
# approximate tight curves but produce more vertices. The endpoint tangents
# must also produce Manhattan port angles for use with `add_ref_connected`.

# %% [markdown]
# ## Connecting a Transition
#
# A transition is just another cross-section, so it can be passed to any path
# component. The transition profile can be linear or any SymPy expression that
# moves from zero to one.

# %%
parabolic = xs.transition(taper, f_s=gw.S**2)
transition_cell = straight(parabolic, length=20.0)
print(f"Transition start: {transition_cell['0'].cross_section}")
print(f"Transition end: {transition_cell['1'].cross_section}")

# %% [markdown]
# Sections are matched by name. If a section exists at only one endpoint, it
# tapers from or to zero width; if both endpoints use a different GDS layer,
# GDSwell raises a `ValueError`.

# %% [markdown]
# ## Physical Length
#
# Every path component records its physical arclength in `cell.info["length"]`.
# A straight has an exact length; sampled evaluators estimate variable-speed
# paths numerically.

# %%
parent = gw.Cell()
parent.add_ref(s_curve)
parent.add_ref(straight(xs, length=10.0), origin=(0.0, -10.0))
print(f"Parent children: {len(parent.instances)}")
