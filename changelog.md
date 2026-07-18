# Changelog

## V1.0.6

- Switched application version to load from the root `VERSION` file so releases only require changing one version source.

## V1.0.5

- Replaced VSWR tab with Efficiency tab showing power transmission efficiency η = (1 - |S11|²) × |S21|²
- Added X-Y grid display for efficiency values with interactive cell selection
- Implemented Smith Chart Efficiency mode displaying impedance (S11) data color-coded by efficiency
- Added user-configurable good/poor efficiency thresholds (default: 50% good, 10% poor) for Smith Chart coloring
- Updated Smith Chart modes: replaced dVSWR with Efficiency mode
- Added CSV export support for efficiency tables

## V1.0.4

- Added robust reduced-grid import support by counting data rows and handling trailing-comma CSV rows.
- Added legacy command parsing compatibility for `caps hf ps1 x1 x2 x3 x4`.
- Updated initial defaults: `ΔΓ good=0, poor=0.03` and `ΔZ good=0.001, poor=1`.

## V1.0.3

- Added support for reduced/sparse fine-position input files (for example: `0,15,16,31,32,47,48,63`) by building X/Y axes from actual positions present in the data.
- Improved CSV import detection by counting data rows (supports full `200,704` and reduced `3,136` grids) and handling trailing-comma rows during parsing.
- Added support for legacy command format with pulse token: `caps hf ps1 x1 x2 x3 x4`.
- Updated initial delta-`Γ` thresholds to `good=0` and `poor=0.03`.
- Added Smith Chart view selectors: `X-Y Table`, `dZ`, `dΓ` (under construction), `dVSWR` (under construction).
- Added dZ color-mapped Smith plotting using S22 delta-impedance resolution.
- Implemented `Reflect Coefficient` tab with X-Y-derived delta-`Γ` resolution (`current - previous`) table and green/red range plot.
- Implemented Smith Chart `dΓ` mode using delta-`Γ` resolution coloring with Reflect Coefficient mode/thresholds.

## V1.0.2

- Added the `dZ` tab after `Impedance`.
- Added delta impedance display for `S22 horizontal` and `S22 vertical`.
- Added a `Plot` button with good/poor resolution thresholds.
- Added a `Smith Chart` tab with dot-only plotting, conjugate toggle, and hover details.
- Updated the executable name to include the version suffix.
