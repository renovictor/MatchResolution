# MatchResolution User Manual (v1.0.7)

## 1. What this app does

MatchResolution converts RF matching datasets into analysis views and charts:
- **Display** row table
- **X-Y Table** for selected S-parameter
- **Phase Magnitude** table with 0-360° rotation
- **Contour** edge-only table and Smith view
- **Impedance**, **dZ**, **Reflect Coefficient**, **Efficiency**
- **Smith Chart** with search, manual points, P/M mode, and image save
- **Component** plots

During conversion, the app can **de-embed cable effects** using Cable1/Cable2 S-parameters.

---

## 2. Install and run

### Python mode
1. Install Python 3.10+.
2. Install packages:
   ```powershell
   pip install numpy pandas PySide6 matplotlib openpyxl
   ```
3. Run:
   ```powershell
   python MatchResolution.py
   ```

### EXE mode (Windows)
Run:
```powershell
.\dist\MatchResolution_V1.0.7.exe
```

The app opens **maximized** by default.

On startup, a splash screen shows the program name, version, and loading progress for a few seconds before the main window appears.

---

## 3. Main workflow

1. **File**: select your raw S-parameter data file.
2. **Cable** (optional): select a cable de-embed file.
3. Click **Convert**.
4. Review results in each tab.
5. Click **Export CSV** to save the current tab data.

If Cable file is empty, the app uses built-in **no-cable defaults** (identity-equivalent behavior).

---

## 4. Input file formats

### 4.1 Raw measurement file
Supported extensions include `csv`, `txt`, `dat`, `s2p`, `log`.  
The parser supports:
- Table style with columns (`Frequency`, `CMD` or expanded C1/C2 columns, and S11/S21/S12/S22 real/imag)
- Legacy CMD row style (`caps hf x1 x2 x3 x4` and `caps hf ps1 x1 x2 x3 x4`)
- Vertical block style

### 4.2 Cable de-embed file (optional)
Must contain both rows `Cable1` and `Cable2`, with columns:

`cable, S11R, S11X, S21R, S21X, S12R, S12X, S22R, S22X`

Example:

| cable | S11R | S11X | S21R | S21X | S12R | S12X | S22R | S22X |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cable1 | 0.016788 | 0.004683 | 0.67576 | -0.71964 | 0.67565 | -0.71961 | 0.018742 | 0.004242 |
| Cable2 | 0.019153 | 0.001615 | 0.612062 | -0.77358 | 0.612133 | -0.77335 | 0.017781 | 0.00219 |

---

## 5. De-embedding process used by app

For each data row:
1. Convert measured **S → T**
2. Convert Cable1/Cable2 **S → T**
3. Compute inverse cable matrices
4. De-embed:
   `T_final = inv(T_cable1) × T_measured × inv(T_cable2)`
5. Convert **T_final → S**
6. Store final S11/S21/S12/S22 back into the dataset

All tabs and plots use these de-embedded S-parameters.

---

## 6. Tabs and controls

- **Display**: converted row table (de-embedded values).
- **X-Y Table**: grid view by selected S-parameter.
- **Phase Magnitude**: magnitude/phase table with a 0-360° rotation control on the Smith Chart tab.
- **Contour**: edge-only grid view and contour Smith mode.
- **Impedance**: derived impedance table/plot.
- **dZ**: delta-impedance maps.
- **Reflect Coefficient**: delta-Γ analysis.
- **Efficiency**: `|S21|²` and `ηoverall = (1 - |S11|²) × |S21|²`.
- **Smith Chart**:
  - Modes: X-Y Table / dZ / dΓ / Efficiency / Contour / P/M
  - **Search ZL** by `C1%` and `C2%`
  - **Demo** runs `C1% = C2% = 0, 10, ..., 100` with Search ZL → Carry Over → Plot Points
  - **Carry Over** inserts search result into manual points
  - **Save Image** exports the current Smith chart as PNG
  - Hover text appears below **Parameter**
- **Component**: capacitor and resolution plots.

---

## 7. Export behavior

**Export CSV** exports data for the currently selected tab:
- X-Y Table / Phase Magnitude / Contour / Impedance / dZ / Reflect Coefficient / Efficiency views export grid-style tables.
- Otherwise, default export uses main converted table.

---

## 8. Build executable

Use:
```powershell
.\build_exe.ps1
```

This script reads version from `VERSION`, bundles required files (including `VERSION`), and writes EXE to `dist\`.
