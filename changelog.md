# Changelog

## V2.0.2

- Added a new **Iout** tab next to **Efficiency**.
- Added **Input power (W)** input for Iout calculation with default **100 W**.
- Implemented Iout calculation using **`Iout = -C·V1 + A·I1`** with fixed input impedance **`Zin = 50 Ω`**.
- Updated Iout display to show **RMS current magnitude** (A) instead of complex values.
- Added CSV export support for the Iout table.

## V2.0.1

- Fixed `S12` sign inversion in `T -> S` conversion by correcting the sign in the `s12` reconstruction formula.
- Added **ABCD Matrix** tab next to **Zpar**, with selectable `A / B / C / D` terms derived from the converted 2-port matrix.
- Added freeze panes for analysis tables to keep C1/C2 context visible while scrolling (freeze at row 4 / column 4):
  - X-Y Table
  - Phase Magnitude
  - Contour
  - Impedance
  - Zpar
  - ABCD Matrix
  - Reflect Coefficient
  - Efficiency
- Fixed runtime error in freeze-pane event handling by importing `QEvent`.
- Added a fourth **Efficiency** formula based on the **ABCD matrix** and made it the default mode.
- Fixed the ABCD-efficiency load handling to use **conjugate `S22`** as the load reflection coefficient before converting to `ZL`.

## V2.0.0

- **Efficiency formula correction:** replaced the incorrect `|S21/(1−S22²)|²` formula with the correct transducer gain formula `G_T = |S21|²·(1−|S22|²) / |1−S22²|²` (where Γ_L = S22 at each grid point), ensuring η never exceeds 100%.
- **New default efficiency formula:** added `|S21|²·(1−|S22|²) / |1−S22²|²` as the new default formula in the Efficiency tab combo box. The original `|S21|²` and `ηoverall = (1−|S11|²)×|S21|²` formulas are retained as options.
- **Smith Chart efficiency sync:** Smith Chart efficiency coloring now uses the same formula selected in the Efficiency tab and refreshes automatically when the formula is changed.
- **Good η default changed to 100%:** the default "Good η ≥" threshold in the Efficiency tab is now 100% (was 50%).
- **Component Analysis defaults:** pre-filled Component Analysis tab with standard values — Frequency 27.12 MHz; C1: Coarse=75, Fine6=43, Fine5=34, Fine4=15, Fine3=0.1, Fine2=4.7, Fine1=2.2 pF; C2: Coarse=75, Fine6=75, Fine5=43, Fine4=21, Fine3=15, Fine2=0.1, Fine1=4.7 pF.

- Smith Chart tab: added an **Import** button next to the Clear button that opens a file explorer for the user to select an impedance data CSV file (`R`, `jX` columns). Imported rows are appended directly into the manual impedance points table, making it easy to batch-plot many impedance points without manual entry.

## V1.0.8

- Changed application window icon, taskbar icon, and EXE file icon to `smithchart.ico`.
- Updated `build_exe.ps1` to bundle `smithchart.ico` into the PyInstaller build (`--icon` and `--add-data`) so the icon works in both Python and EXE modes.
- Reflect Coefficient tab: removed the "Mode" dropdown and now renders **both** horizontal (ΔC1) and vertical (ΔC2) |ΔΓ| heatmaps side by side at the same time instead of showing only one at a time.
- Smith Chart tab: added a `Demo` button between `Search ZL` and `Carry Over` that automatically runs `C1%=C2%=0,10,...,100` with the sequence `Search ZL → Carry Over → Plot Points` for each step.

## V1.0.7

- Added a custom splash screen with version and startup progress.
- Added Phase Magnitude, Contour, and P/M Smith Chart modes.
- Added Smith Chart image saving and contour edge display.

## V1.0.6

- Switched application version to load from the root `VERSION` file so releases only require changing one version source.
- Fixed one-file executable startup by bundling `VERSION` in PyInstaller builds and adding frozen-app version path fallback.
- Added cable de-embedding workflow (S→T, cable inverse T, de-embed, T→S) applied during conversion so Display/plots use de-embedded S-parameters.
- Added optional cable file input path in the UI with default no-cable fallback values when no cable file is provided.
- Updated Smith search panel layout: `Search ZL` moved under `C1%` and `Carry Over` moved under `C2%`, with wider controls for full label visibility.
- Moved Smith hover hint text directly under `Parameter:` in the Smith toolbar.
- App window now launches maximized on startup.

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
