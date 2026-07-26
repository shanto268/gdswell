# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
from pathlib import Path

import klayout.db as kdb

import gdswell as gw


@gw.cell
def ordered_cached_component(index: int) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [(0, 0), (float(index + 1), 0), (float(index + 1), 1), (0, 1)],
        gw.Layer(1, 0),
    )
    return cell


def _write_without_timestamps(layout: gw.Layout, path: Path) -> None:
    options = kdb.SaveLayoutOptions()
    options.write_context_info = True
    options.gds2_write_cell_properties = True
    options.gds2_write_file_properties = True
    options.gds2_write_timestamps = False
    layout.kdb.write(str(path), options)


def test_async_cold_and_warm_cache_exports_have_same_cell_order(tmp_path: Path) -> None:
    original_cache_dir = gw.config.cache_dir
    original_use_disk_cache = gw.config.use_disk_cache
    original_async_cells = gw.config.async_cells

    try:
        gw.config.cache_dir = tmp_path / "cache"
        gw.config.use_disk_cache = True
        gw.config.async_cells = True
        gw.clear_cache()

        cold_path = tmp_path / "cold.gds"
        with gw.Layout() as cold_layout:
            for index in range(16):
                ordered_cached_component(index)
            cold_layout.wait()
            cold_cell_order = [cell.name for cell in cold_layout.kdb.each_cell()]
            _write_without_timestamps(cold_layout, cold_path)

        warm_path = tmp_path / "warm.gds"
        with gw.Layout() as warm_layout:
            for index in range(16):
                ordered_cached_component(index)
            warm_layout.wait()
            warm_cell_order = [cell.name for cell in warm_layout.kdb.each_cell()]
            _write_without_timestamps(warm_layout, warm_path)

        assert cold_cell_order == warm_cell_order
        assert cold_path.read_bytes() == warm_path.read_bytes()
    finally:
        gw.config.cache_dir = original_cache_dir
        gw.config.use_disk_cache = original_use_disk_cache
        gw.config.async_cells = original_async_cells
