# Copyright 2026 Helge Gehring, Simon Bilodeau and contributors.
# Licensed under the Apache License, Version 2.0.
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from gdswell.config import config

if TYPE_CHECKING:
    from gdswell.cell import Cell


def save_to_disk_cache(
    cell: Cell,
    unique_name: str,
    deps: set[Path] | None = None,
    external_pkgs: set[str] | None = None,
    cache_file: Path | None = None,
) -> Path:
    """Save a cell to the disk cache atomically."""
    import klayout.db as kdb

    cache_file = cache_file or config.cache_dir / f"{unique_name}.oas"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    # Use SaveLayoutOptions to save only this cell and its dependencies
    # This is much faster than creating a temp layout and copying via Python
    options = kdb.SaveLayoutOptions()
    options.add_cell(cell.kdb.cell_index())

    # Atomic write: write to temp file then rename
    temp_path = cache_file.with_name(f"{cache_file.name}.{uuid.uuid4()}.tmp")
    cell.layout.kdb.write(str(temp_path), options)

    try:
        os.replace(temp_path, cache_file)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    # Also save dependency list if debug mode is on
    if config.debug_cache and (deps or external_pkgs):
        import json

        dep_file = cache_file.with_suffix(".dep")
        dep_data = {
            "files": [str(p) for p in sorted(deps)] if deps else [],
            "external_packages": sorted(external_pkgs) if external_pkgs else [],
        }
        dep_file.write_text(json.dumps(dep_data, indent=2))

    return cache_file


def load_from_disk_cache(cache_file: Path, unique_name: str) -> Cell:
    """Load a cached cell into an isolated layout without another copy step."""
    from gdswell.layout import Layout

    cache_layout = Layout(name=f"cache_{unique_name}")
    with cache_layout:
        cache_layout.kdb.read(str(cache_file))
        if cache_layout.kdb.cell(unique_name) is None:
            raise ValueError(f"Cell '{unique_name}' not found in {cache_file}")
        return cache_layout.cell(unique_name)
