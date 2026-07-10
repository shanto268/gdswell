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
# # Caching and Asynchronous Cells
#
# GDSwell combines deterministic cell identities with two cache tiers. The
# memory cache preserves identity within a `Layout`; the disk cache stores OASIS
# cells across Python sessions.

# %%
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

import gdswell as gw


class Layers(gw.Layer, Enum):
    DEVICE = (1, 0)


# %% [markdown]
# ## Memory Cache
#
# A decorated function with the same arguments returns the same cell object
# when called again in the same layout.

# %%
gw.config.async_cells = False


@gw.cell
def cache_square(size: float = 5.0) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0.0, 0.0), (size, 0.0), (size, size), (0.0, size)], Layers.DEVICE)
    return cell


with gw.Layout(name="memory_cache"):
    first = cache_square(5.0)
    second = cache_square(5.0)
    other = cache_square(7.0)
    print(f"Same arguments reuse identity: {first is second}")
    print(f"Different arguments reuse identity: {first is other}")

# %% [markdown]
# A separate layout has its own in-memory identity map. The disk tier can still
# provide a realized cell when enabled.

# %% [markdown]
# ## Disk Cache
#
# The persistent cache defaults to `.gdswell_cache` relative to the working
# directory. This example uses a temporary directory so the documentation build
# leaves no project artifacts behind.

# %%
with TemporaryDirectory() as cache_dir:
    old_cache_dir = gw.config.cache_dir
    old_use_disk = gw.config.use_disk_cache
    gw.config.cache_dir = Path(cache_dir)
    gw.config.use_disk_cache = True
    try:
        with gw.Layout(name="disk_writer"):
            written = cache_square(11.0)
        with gw.Layout(name="disk_reader"):
            loaded = cache_square(11.0)
            print(f"Disk artifact exists: {any(Path(cache_dir).glob('*.oas'))}")
            print(f"Loaded cell is realized: {loaded.frozen}")
            print(f"Writer and reader wrappers differ: {written is not loaded}")
    finally:
        gw.config.cache_dir = old_cache_dir
        gw.config.use_disk_cache = old_use_disk

# %% [markdown]
# `gw.clear_cache()` removes files from the disk cache. It does not empty an
# already populated layout memory cache; use a new layout for a fresh process-
# like lookup.

# %% [markdown]
# ## Asynchronous Generation
#
# With asynchronous generation enabled, cache misses submit work to a global
# thread pool and return `FutureCell` proxies immediately.


# %%
@gw.cell
def async_square(size: float) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0.0, 0.0), (size, 0.0), (size, size), (0.0, size)], Layers.DEVICE)
    return cell


gw.config.async_cells = True
with gw.Layout(name="async_cache") as async_layout:
    futures = [async_square(float(size)) for size in range(4, 8)]
    print(f"Returned type: {type(futures[0]).__name__}")
    async_layout.wait()
    print(f"Generated cells: {[future.name for future in futures]}")
gw.config.async_cells = False

# %% [markdown]
# `Layout.wait()` resolves every pending cell in that layout and propagates
# background exceptions. Accessing geometry or ports through a future may also
# wait implicitly.

# %% [markdown]
# ## What Invalidates a Cell
#
# The generated name includes serialized arguments, the source file of the
# defining module and its imported local dependency closure, external package
# versions, and the Python version. Editing a low-level dependency therefore
# invalidates cells whose source hash includes that dependency.
