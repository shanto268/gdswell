:::{div} .hero
```{image} images/logo.svg
:alt: GDSwell logo
:width: 100%
```

A modern Python framework for seamless KLayout integration and intuitive layout synthesis.

[Get Started](./01-getting_started.py){.button} [Reference](./reference/index.md){.button-outline}
:::

## Foundation Guides

Start with the concepts that the feature tutorials build on:

:::{card} Core data model
Layouts, cells, instances, ports, and asynchronous cell proxies. [Open guide ->](./00-core_data_model.py)
:::

:::{card} Geometry foundations
Coordinates, micron units, and transforms. [Open guide ->](./00-coordinates_units_transforms.py)

Layers, cross-sections, and symbolic paths: [layers](./00-layers_cross_sections.py) and [paths](./00-paths_symbolic_geometry.py).
:::

:::{card} Cell lifecycle and caching
Freezing, hierarchy, and content-addressed identities: [lifecycle](./00-cell_lifecycle_hierarchy.py). Disk caching and asynchronous generation: [caching](./00-caching_async.py).
:::

:::{card} Qiskit Metal migration
Map QDesign, QComponent, pins, QGeometry, and subtractive geometry to GDSwell. [Open guide ->](./16-qiskit_metal_migration.py)
:::

:::{grid}
:gutter: 3

:::{card} 🧠 Smart Layer API
Perform complex boolean operations, sizing, and transformations using intuitive Pythonic syntax. [Learn More →](./12-smart_layers.py)
:::

:::{card} 🚀 Hierarchical Caching
Memory + Disk caching with transitive dependency hashing ensures lightning-fast re-execution. [Learn More →](./13-caching_internals.py)
:::

:::{card} ⚡ Parallel Advantage
Leverage asynchronous cell generation and multi-core processing for massive layouts. [Guide →](./14-parallelism.py) • [Benchmark →](./06-parallel_advantage.py)
:::

:::{card} 🔌 Connectivity & Routing
Snapped hierarchical connectivity and automated component chaining for error-free assembly. [Ports](./02-ports.py) • [Routing](./11-routing.py)
:::

:::{card} 🛰️ Spatial Netlist Extraction
Extract connectivity and properties from cell hierarchies via physical collision detection. [Learn More →](./05-netlist_hierarchy.py)
:::

:::{card} 📊 Performance Insights
Detailed design statistics tracking cache performance, build times, and call tracking. [Learn More →](./08-complex_circuit.py)
:::

:::{card} 🏷️ Text Rendering
High-performance text rendering with sub-millisecond per-character placement. [Benchmarking →](./07-text_benchmark.py)
:::

:::{card} 〰️ Transitions & Paths
Define custom adiabatic tapers and generic paths using powerful SymPy expressions. [Learn More →](./03-transitions.py)
:::

:::{card} 📓 Jupyter & KLayout Native
Interactive GDSII rendering and KLive integration for a seamless developer experience. [Get Started →](./01-getting_started.py)
:::
:::
