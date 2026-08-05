# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
from pathlib import Path

import klayout.db as kdb
import pytest

import gdswell as gw
from gdswell.future_cell import FutureCell


@gw.cell
def ordered_cached_component(index: int) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon(
        [(0, 0), (float(index + 1), 0), (float(index + 1), 1), (0, 1)],
        gw.Layer(1, 0),
    )
    return cell


@gw.cell
def layered_cached_component(index: int, layer: gw.Layer) -> gw.Cell:
    cell = gw.Cell()
    x = float(index * 10)
    cell.add_polygon([(x, 0), (x + 1, 0), (x + 1, 1), (x, 1)], layer)
    return cell


@gw.cell
def mixed_shape_component(key: str) -> gw.Cell:
    layer = gw.Layer(3, 0)
    cell = gw.Cell()
    cell.add_polygon([(20, 0), (30, 0), (30, 10), (20, 10)], layer)
    shapes = cell.kdb.shapes(cell.layer(layer))
    shapes.insert(kdb.DPath([kdb.DPoint(0, 30), kdb.DPoint(10, 30)], 3))
    shapes.insert(kdb.DBox(0, 0, 10, 10))
    cell.add_info("key", key)
    return cell


@gw.cell
def hierarchical_leaf(key: str, layer: gw.Layer) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0, 0), (4, 0), (4, 2), (0, 2)], layer)
    cell.add_info("key", key)
    return cell


@gw.cell
def hierarchical_branch(key: str) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0, 10), (8, 10), (8, 12), (0, 12)], gw.Layer(30, 0))
    low = hierarchical_leaf(f"{key}_low", gw.Layer(10, 0))
    high = hierarchical_leaf(f"{key}_high", gw.Layer(20, 0))
    cell.add_ref(high)
    cell.add_ref(low, origin=(5, 0))
    return cell


@gw.cell
def hierarchical_root(key: str) -> gw.Cell:
    cell = gw.Cell()
    cell.add_polygon([(0, 20), (12, 20), (12, 22), (0, 22)], gw.Layer(50, 0))
    branch = hierarchical_branch(key)
    shared = hierarchical_leaf(f"{key}_shared", gw.Layer(40, 0))
    cell.add_ref(shared)
    cell.add_ref(branch, origin=(0, 30))
    cell.add_ref(shared, origin=(10, 0))
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


def test_async_cold_and_warm_cache_follow_same_realization_order(tmp_path: Path) -> None:
    original_cache_dir = gw.config.cache_dir
    original_use_disk_cache = gw.config.use_disk_cache
    original_async_cells = gw.config.async_cells

    try:
        gw.config.cache_dir = tmp_path / "cache"
        gw.config.use_disk_cache = True
        gw.config.async_cells = True
        gw.clear_cache()

        paths = [tmp_path / "cold.gds", tmp_path / "warm.gds"]
        cell_orders: list[list[str]] = []
        layer_orders: list[list[tuple[int, int]]] = []

        for path in paths:
            with gw.Layout() as layout:
                top = gw.Cell()
                top.kdb.name = "top"
                first = layered_cached_component(1, gw.Layer(1, 0))
                second = layered_cached_component(2, gw.Layer(2, 0))

                top.add_ref(second)
                top.add_ref(first)
                layout.wait()

                cell_orders.append([cell.name for cell in layout.kdb.each_cell()])
                layer_orders.append(
                    [(info.layer, info.datatype) for info in layout.kdb.layer_infos()]
                )
                _write_without_timestamps(layout, path)

        assert cell_orders[0] == cell_orders[1]
        assert layer_orders[0] == layer_orders[1]
        assert paths[0].read_bytes() == paths[1].read_bytes()
    finally:
        gw.config.cache_dir = original_cache_dir
        gw.config.use_disk_cache = original_use_disk_cache
        gw.config.async_cells = original_async_cells


def test_warm_async_cache_hit_remains_lazy_in_home_layout(tmp_path: Path) -> None:
    original_cache_dir = gw.config.cache_dir
    original_use_disk_cache = gw.config.use_disk_cache
    original_async_cells = gw.config.async_cells

    try:
        gw.config.cache_dir = tmp_path / "cache"
        gw.config.use_disk_cache = True
        gw.config.async_cells = True
        gw.clear_cache()

        with gw.Layout() as cold_layout:
            cold_cell = mixed_shape_component("lazy")
            cold_layout.wait()
            unique_name = cold_cell.name

        with gw.Layout() as warm_layout:
            warm_cell = mixed_shape_component("lazy")
            assert isinstance(warm_cell, FutureCell)
            assert warm_layout.kdb.cell(unique_name) is None
            assert mixed_shape_component("lazy") is warm_cell

            warm_layout.wait()

            assert warm_layout.kdb.cell(unique_name) is not None
            assert warm_layout.cell(unique_name) is warm_cell
            assert object.__getattribute__(warm_cell, "_future") is None
    finally:
        gw.config.cache_dir = original_cache_dir
        gw.config.use_disk_cache = original_use_disk_cache
        gw.config.async_cells = original_async_cells


@pytest.mark.parametrize("async_cells", [False, True])
def test_cold_cache_miss_uses_persisted_oas_representation(
    tmp_path: Path, async_cells: bool
) -> None:
    original_cache_dir = gw.config.cache_dir
    original_use_disk_cache = gw.config.use_disk_cache
    original_async_cells = gw.config.async_cells

    try:
        gw.config.cache_dir = tmp_path / f"cache_{async_cells}"
        gw.config.use_disk_cache = True
        gw.config.async_cells = async_cells
        gw.clear_cache()

        paths = [tmp_path / "cold.gds", tmp_path / "warm.gds"]
        shape_orders: list[list[int]] = []

        for path in paths:
            with gw.Layout() as layout:
                cell = mixed_shape_component(str(async_cells))
                layout.wait()
                assert cell.layout is layout
                layer_index = cell.layer(gw.Layer(3, 0))
                shape_orders.append([shape.type() for shape in cell.kdb.each_shape(layer_index)])
                _write_without_timestamps(layout, path)

        assert shape_orders[0] == shape_orders[1]
        assert paths[0].read_bytes() == paths[1].read_bytes()
    finally:
        gw.config.cache_dir = original_cache_dir
        gw.config.use_disk_cache = original_use_disk_cache
        gw.config.async_cells = original_async_cells


@pytest.mark.parametrize("async_cells", [False, True])
def test_hierarchical_cache_roundtrip_is_byte_stable(tmp_path: Path, async_cells: bool) -> None:
    original_cache_dir = gw.config.cache_dir
    original_use_disk_cache = gw.config.use_disk_cache
    original_async_cells = gw.config.async_cells

    try:
        gw.config.cache_dir = tmp_path / "cache"
        gw.config.use_disk_cache = True
        gw.config.async_cells = async_cells
        gw.clear_cache()

        paths = [tmp_path / "cold.gds", tmp_path / "warm.gds"]
        cell_orders: list[list[str]] = []
        layer_orders: list[list[tuple[int, int]]] = []
        hierarchies: list[dict[str, list[str]]] = []

        for path in paths:
            with gw.Layout() as layout:
                root = hierarchical_root(str(async_cells))
                layout.wait()
                assert root.layout is layout

                cell_orders.append([cell.name for cell in layout.kdb.each_cell()])
                layer_orders.append(
                    [(info.layer, info.datatype) for info in layout.kdb.layer_infos()]
                )
                hierarchies.append(
                    {
                        cell.name: [
                            layout.kdb.cell(instance.cell_index).name
                            for instance in cell.each_inst()
                        ]
                        for cell in layout.kdb.each_cell()
                    }
                )
                _write_without_timestamps(layout, path)

        assert cell_orders[0] == cell_orders[1]
        assert layer_orders[0] == layer_orders[1]
        assert hierarchies[0] == hierarchies[1]
        assert paths[0].read_bytes() == paths[1].read_bytes()
    finally:
        gw.config.cache_dir = original_cache_dir
        gw.config.use_disk_cache = original_use_disk_cache
        gw.config.async_cells = original_async_cells
