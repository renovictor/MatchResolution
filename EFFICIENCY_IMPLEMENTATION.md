# Efficiency Tab and Smith Chart Implementation (v1.0.5)

## Overview

The Efficiency feature adds power transmission efficiency analysis to the RF Matching Resolution Tool. This document explains the complete implementation of the Efficiency tab and Smith Chart coloring mode, including all implemented formulas, data structures, UI components, and rendering pipeline.

## Efficiency Formula

### Implemented Formulas (6 modes)

The source code implements six selectable efficiency formulas:

1. `ηZ = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}` (`z_single`)
2. `ηZL,Γin=0 = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}` (`zl_gin0`, default)
3. `ηABCD = PL / Pin` (`abcd_power`)
4. `|S21|²·(1−|S22|²) / |1−S22²|²` (`h_squared`)
5. `|S21|²` (`s21_squared`)
6. `ηoverall = (1 - |S11|²) × |S21|²` (`overall`)

### Formula Inputs by Mode

- `z_single`: requires `S11`, `S21`, `S12`, `S22` (converted to Z-parameters with `ZL` from `conj(S22)`).
- `zl_gin0`: requires `S11`, `S21`, `S12`, `S22` (converted to Z-parameters, then `ZL = -Z12·Z21/(50 - Z11) - Z22`).
- `abcd_power`: requires `S11`, `S21`, `S12`, `S22` (S→Z→ABCD, then `PL/Pin`).
- `h_squared`: requires `S21`, `S22`.
- `s21_squared`: requires `S21`.
- `overall`: requires `S11`, `S21`.

### Important Limitation of the S-Parameter Efficiency Formula

The simplified formula used in this feature,

**η = (1 - |S11|²) × |S21|²**

is tied to the **50 Ω reference condition** of the network analyzer ports.

- In normal VNA measurements, port 1 and port 2 are both 50 Ω systems.
- S-parameters are therefore defined with respect to that reference impedance.
- The above simplified efficiency expression is valid for that matched reference condition and is easy to misuse as a universal efficiency formula.

Because of this, S-parameter-only efficiency can be misleading if interpreted outside its reference condition. It is best used to evaluate:

1. Matching/mismatching behavior
2. Relative transmission trends
3. Efficiency under 50 Ω reference assumptions

For **arbitrary load impedance** efficiency calculation, use the **ABCD-matrix power method** (`ηABCD = PL / Pin`) or the equivalent full Z/ABCD power derivation (`ηZ`) instead of simplified S-only formulas. ABCD/Z-based methods are the proper approach when load is not fixed at 50 Ω.

## Data Structures

### Efficiency Display Table

**Function**: `build_efficiency_display_table(df, efficiency_mode)`

**Input**:
- `df` (pandas DataFrame) with required S-parameter columns based on selected formula mode.

**Output**: 
- `presentation_rows` (list of dicts) formatted for table display
- X and Y axis headers with actual grid positions from sparse data
- Efficiency values calculated for each (x_c1, y_c2) position

**Key Features**:
- Extracts actual X/Y axis positions using `extract_xy_axis_values(df)`
- Creates grid with efficiency values at intersections
- Handles sparse/reduced grid data by using actual positions from input file
- Returns a presentation-ready structure for `QTableWidget` or `QTableView`

### Smith Chart Efficiency Lookup

**Function**: `build_smith_efficiency_lookup(df, efficiency_mode="z_single")`

**Input**:
- `df` (pandas DataFrame) with required S-parameter columns based on selected formula mode.

**Output**: 
- Dictionary mapping `(x_c1, y_c2)` → float (efficiency value)
- Keys are tuples of grid coordinates
- Values are efficiency values in range [0, 1]

**Usage in Rendering**:
```python
efficiency_values = np.array([
    self.smith_efficiency_lookup.get((point["x_c1"], point["y_c2"]), np.nan)
    for point in points
], dtype=float)
```

This allows O(1) lookup during Smith Chart scatter plot rendering.

## UI Components

### Efficiency Tab Layout

The Efficiency tab uses a **QSplitter** (vertical orientation) with two sections:

#### Section 1: Efficiency X-Y Table
- **Widget**: `efficiency_table_view` (QTableView)
- **Data**: `df_efficiency_display` (pandas DataFrame)
- **Model**: Standard table model with headers and data grid
- **Height**: 520 pixels (default split)
- **Interaction**: Click a cell to display its value in `efficiency_cell_label`

#### Section 2: Threshold Controls
- **Widget**: `efficiency_plot_frame` (QFrame)
- **Height**: 220 pixels (default split)
- **Contents**:
  - Good efficiency threshold input: `efficiency_good_edit` (default: 50%)
  - Poor efficiency threshold input: `efficiency_poor_edit` (default: 10%)
  - Status label: `efficiency_status_label`
  - Styling: Pink/magenta theme (#FCE4EC, #F8BBD0, #C2185B)

### Threshold Input Fields

```python
# Good efficiency threshold (higher is better)
self.efficiency_good_edit = QLineEdit("50")
self.efficiency_good_edit.setValidator(QDoubleValidator(0.0, 100.0, 1))
self.efficiency_good_edit.editingFinished.connect(self._on_efficiency_threshold_changed)

# Poor efficiency threshold (lower is worse)
self.efficiency_poor_edit = QLineEdit("10")
self.efficiency_poor_edit.setValidator(QDoubleValidator(0.0, 100.0, 1))
self.efficiency_poor_edit.editingFinished.connect(self._on_efficiency_threshold_changed)
```

**Validation**:
- Input range: 0-100 (percentage)
- Constraints enforced by `QDoubleValidator`
- Converted to [0, 1] range internally for calculations

## Threshold System

### Threshold Properties

```python
self.efficiency_good_threshold = 0.50    # Default: 50%
self.efficiency_poor_threshold = 0.10    # Default: 10%
```

These are stored as decimal values [0, 1] for consistency with efficiency calculations.

### Threshold Validation

**Function**: `_get_efficiency_thresholds(show_message=False)`

**Validation Rules**:
1. Both inputs must be numeric
2. Both must be in range [0, 100%]
3. Good threshold must be **greater than** poor threshold
4. Returns tuple `(good_threshold, poor_threshold)` as [0, 1] values
5. Returns `None` if validation fails

**Example**:
```python
thresholds = self._get_efficiency_thresholds(show_message=True)
if thresholds is not None:
    good_pct, poor_pct = thresholds
    # Use for rendering
```

### Threshold Change Handler

**Function**: `_on_efficiency_threshold_changed()`

**Triggered**: When either threshold input field loses focus

**Actions**:
1. Parse and validate new threshold values
2. Update `efficiency_good_threshold` and `efficiency_poor_threshold` properties
3. If Smith Chart is in Efficiency mode, call `refresh_smith_chart()` to redraw
4. New colors applied immediately

## Smith Chart Integration

### Mode Selection

The Smith Chart supports 4 display modes:
1. **xy** - Basic impedance plotting without coloring
2. **dz** - Color-coded by delta impedance (S22 resolution)
3. **dgamma** - Color-coded by delta reflection coefficient
4. **efficiency** - Color-coded by power transmission efficiency (NEW in v1.0.5)

Mode selection via radio buttons in Smith Chart controls.

### Refresh Pipeline

**Function**: `refresh_smith_chart()`

**Flow**:
1. Extract Smith Chart points from `df_smith_points`
2. Build lookup tables for all modes:
   - `smith_dz_lookup` (if S22 available)
   - `smith_dgamma_lookup` (always built)
   - `smith_efficiency_lookup` (NEW)
3. Determine current mode and get appropriate thresholds
4. Count how many points have coloring data available
5. Update status label with statistics
6. Call `_draw_smith_chart()` for rendering

**Status Label Format** (Efficiency mode):
```
S11/S21: 12,345 points | Efficiency colors on 12,345 points | green≥50.0%, red≤10.0%
```

### Rendering Logic

**Function**: `_draw_smith_chart(points, parameter_name)`

**Efficiency Mode** (`elif self.current_smith_mode == "efficiency"`):

1. **Extract efficiency values** for each plotted point:
   ```python
   efficiency_values = np.array([
       self.smith_efficiency_lookup.get((point["x_c1"], point["y_c2"]), np.nan)
       for point in points
   ], dtype=float)
   ```

2. **Check for finite values**:
   ```python
   finite_mask = np.isfinite(efficiency_values)
   if np.any(finite_mask):
       # Has coloring data
   else:
       # Fall back to viridis coloring
   ```

3. **Create scatter plot** with efficiency coloring:
   ```python
   plotted_values = np.where(finite_mask, efficiency_values, poor_threshold)
   self.smith_scatter = ax.scatter(
       values.real,           # S11 real part (impedance)
       values.imag,           # S11 imaginary part (impedance)
       c=plotted_values,      # Color by efficiency
       cmap="RdYlGn",         # Red-Yellow-Green colormap
       vmin=poor_threshold,   # Poor threshold → red
       vmax=good_threshold,   # Good threshold → green
       s=14,
       alpha=0.9,
       picker=True
   )
   ```

4. **Add colorbar** with labels:
   ```python
   colorbar.set_label(
       f"Efficiency (S11/S21)  green≥{good_pct:.1f}%, red≤{poor_pct:.1f}%",
       fontsize=9
   )
   ```

### Color Mapping

**Colormap**: `RdYlGn` (Red-Yellow-Green)
- **Green** → High efficiency (≥ good threshold)
- **Yellow** → Medium efficiency (between thresholds)
- **Red** → Low efficiency (≤ poor threshold)

**Normalization**:
```python
norm = Normalize(vmin=poor_threshold, vmax=good_threshold, clip=True)
```
- Values below poor_threshold clipped to red
- Values above good_threshold clipped to green
- Linear interpolation between thresholds

## Data Export

### CSV Export for Efficiency Table

**Function**: `export_csv()` - Efficiency mode handling

**Export Format**:
- Filename: `{prefix}_efficiency_table.csv`
- Content: Full efficiency X-Y grid from `df_efficiency_display`
- Headers: X/Y axis positions with efficiency values

**Example**:
```csv
,0,15,16,31,32,47,48,63,...
0,0.87,0.92,0.85,...
15,0.91,0.88,0.93,...
...
```

## Integration with Existing Features

### Workflow Integration

1. **File Import** → `convert_file()` processes CSV data
2. **Data Available** → `refresh_efficiency_table()` builds efficiency display
3. **Efficiency Tab Active** → Table shows efficiency values by grid position
4. **User Adjusts Thresholds** → `_on_efficiency_threshold_changed()` updates Smith Chart
5. **Export** → Efficiency table exported alongside other analysis data

### Compatibility Notes

- Required columns depend on formula mode:
  - `z_single`, `zl_gin0`, `abcd_power`: S11/S21/S12/S22
  - `h_squared`: S21/S22
  - `s21_squared`: S21
  - `overall`: S11/S21
- Works with both full (200×704) and reduced grid data
- Smith Chart points use S11 impedance coordinates; colors follow the selected efficiency formula mode
- No dependency on other modes (dz, dgamma) - independent calculation

## Key Files and Line References

**File**: `MatchResolution.py`

**Function Definitions**:
- Line 683-730: `build_efficiency_display_table(df)`
- Line 806-847: `build_smith_efficiency_lookup(df)`

**UI Construction**:
- Line 1770-1856: Efficiency tab layout and controls
- Line 1827-1838: Threshold input fields with validators

**Methods**:
- Line 2422-2460: Threshold validation and callback methods
  - `_on_efficiency_threshold_changed()`
  - `_get_efficiency_thresholds(show_message=False)`
- Line 2555-2614: Smith Chart refresh pipeline
- Line 2663-2753: Smith Chart rendering with efficiency mode

**Documentation**:
- Line 1863-1864: Help note text updated for v1.0.5

## Testing Checklist

- [ ] Load CSV with full S-parameter data (S11/S21/S12/S22) for complete formula coverage
- [ ] Verify Efficiency tab shows correct X-Y grid with values in [0, 1]
- [ ] Click cell to display value in status label
- [ ] Switch Smith Chart to Efficiency mode
- [ ] Switch Efficiency formula dropdown across all 5 modes and verify recalculation
- [ ] Verify points color-coded by efficiency
- [ ] Adjust good threshold, verify green colors update
- [ ] Adjust poor threshold, verify red colors update
- [ ] Verify validation: good > poor constraint
- [ ] Verify validation: threshold range [0, 100]
- [ ] Test with reduced grid data (sparse positions)
- [ ] Export CSV and verify efficiency table integrity
- [ ] Test with missing required columns per mode and verify mode-specific validation message

## Version History

- **v1.0.5**: Initial Efficiency tab and Smith Chart mode implementation
  - Added efficiency formula calculation
  - Implemented Efficiency tab with X-Y grid display
  - Added Smith Chart Efficiency mode with threshold-based coloring
  - User-configurable good/poor efficiency thresholds

## Future Enhancements

Potential improvements for future versions:

1. **Efficiency Statistics**: Add min/max/mean efficiency to status label
2. **Histogram View**: Show distribution of efficiency values
3. **Export Formats**: Add efficiency-only CSV export option
4. **Threshold Presets**: Save/load threshold configurations
5. **Comparative Analysis**: Show efficiency change across multiple datasets
6. **Interactive Colormap**: Allow user to switch between colormaps (RdYlGn, viridis, etc.)
