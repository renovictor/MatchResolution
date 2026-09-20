from __future__ import annotations

import os
import re
import sys

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QEvent, QEventLoop, QElapsedTimer, QTimer
from PySide6.QtGui import QColor, QBrush, QFont, QDoubleValidator, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QMainWindow,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QProgressBar,
    QTableView,
    QMessageBox,
    QFrame,
    QHeaderView,
    QTabWidget,
    QRadioButton,
    QScrollArea,
    QSplitter,
)

EXPECTED_S_COLUMNS = [
    "S11_r", "S11_x",
    "S21_r", "S21_x",
    "S12_r", "S12_x",
    "S22_r", "S22_x",
]

REQUIRED_TABLE_COLUMNS = ["Frequency", "CMD", *EXPECTED_S_COLUMNS]
EXPANDED_CMD_COLUMNS = ["C1_coarse", "C1_fine", "C2_coarse", "C2_fine"]
FULL_GRID_ROWS = 7 * 64 * 7 * 64
REDUCED_GRID_ROWS = 7 * 8 * 7 * 8
XY_PARAMETERS = ["S11", "S21", "S12", "S22"]
IMPEDANCE_PARAMETERS = ["S11", "S22"]
ZPAR_PARAMETERS = ["Z11", "Z21", "Z12", "Z22"]
ABCD_PARAMETERS = ["A", "B", "C", "D"]
DEFAULT_Z0 = 50.0
CABLE_REQUIRED_COLUMNS = ["cable", "s11r", "s11x", "s21r", "s21x", "s12r", "s12x", "s22r", "s22x"]
DEFAULT_CABLE_S_PARAMETERS = {
    "cable1": {
        "s11": 0.000001 + 0.000001j,
        "s21": -1.0 + 0.000001j,
        "s12": -1.0 + 0.000001j,
        "s22": 0.000001 + 0.000001j,
    },
    "cable2": {
        "s11": 0.000001 + 0.000001j,
        "s21": -1.0 + 0.000001j,
        "s12": -1.0 + 0.000001j,
        "s22": 0.000001 + 0.000001j,
    },
}
APP_NAME = "Palantir"

np = None
pd = None
_matplotlib = None
FigureCanvas = None
Figure = None
Normalize = None
_mpl_cm = None
_MATPLOTLIB_OK = False


def load_runtime_libraries():
    global np, pd, _matplotlib, FigureCanvas, Figure, Normalize, _mpl_cm, _MATPLOTLIB_OK

    import numpy as _np
    import pandas as _pd
    np = _np
    pd = _pd

    try:
        import matplotlib as _matplotlib_module
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as _FigureCanvas
        from matplotlib.figure import Figure as _Figure
        from matplotlib.colors import Normalize as _Normalize
        import matplotlib.cm as _mpl_cm_module

        _matplotlib = _matplotlib_module
        FigureCanvas = _FigureCanvas
        Figure = _Figure
        Normalize = _Normalize
        _mpl_cm = _mpl_cm_module

        def _get_cmap(name):
            """Compatibility: matplotlib ≥3.9 removed cm.get_cmap; use colormaps registry."""
            if hasattr(_matplotlib, "colormaps"):
                return _matplotlib.colormaps[name]
            return _mpl_cm.get_cmap(name)   # matplotlib < 3.9 fallback

        globals()["_get_cmap"] = _get_cmap
        _MATPLOTLIB_OK = True
    except ImportError:
        _MATPLOTLIB_OK = False


def app_base_path():
    if hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.dirname(os.path.abspath(__file__))


def load_app_icon() -> QIcon:
    icon_path = os.path.join(app_base_path(), "smithchart.ico")
    return QIcon(icon_path)


class StartupSplash(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(860, 520)
        self.setStyleSheet("background-color: #F3E5F5; border: 1px solid #9575CD;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(12)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6A1B9A,
                    stop:0.55 #8E24AA,
                    stop:1 #3949AB
                );
                border-radius: 18px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(4)

        title_label = QLabel(APP_NAME)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: white;")
        subtitle_label = QLabel("RF Matching Network Palantir")
        subtitle_label.setStyleSheet("font-size: 16px; color: #EDE7F6;")
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setStyleSheet("font-size: 15px; color: #E1BEE7; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(version_label)
        layout.addWidget(header)

        body = QFrame()
        body.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D1C4E9;
                border-radius: 16px;
            }
        """)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 18, 18, 18)
        body_layout.setSpacing(10)

        self.status_label = QLabel("Starting application...")
        self.status_label.setStyleSheet("font-size: 14px; color: #4527A0; padding: 4px 2px;")
        body_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #EDE7F6;
                border: 1px solid #9575CD;
                border-radius: 10px;
                text-align: center;
                color: #4527A0;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #7E57C2;
                border-radius: 10px;
            }
        """)
        body_layout.addWidget(self.progress_bar)

        self.detail_label = QLabel("Loading modules and preparing the main window...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #6A1B9A;")
        body_layout.addWidget(self.detail_label)

        layout.addWidget(body, stretch=1)

        self.footer_label = QLabel("© ASM · V. Huang · victor.huang@asm.com")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("font-size: 12px; color: #6A1B9A; padding-top: 4px;")
        layout.addWidget(self.footer_label)

    def set_status(self, message, progress=None):
        self.status_label.setText(message)
        self.detail_label.setText("Please wait while the application initializes.")
        if progress is not None:
            self.progress_bar.setValue(max(0, min(100, int(progress))))


class SmithZoomWindow(QWidget):
    def __init__(self, title_text):
        super().__init__()
        self.setWindowTitle(title_text)
        self.setFixedSize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.annotation_edit = QLineEdit()
        self.annotation_edit.setPlaceholderText("輸入註解...")
        layout.addWidget(self.annotation_edit)

        if _MATPLOTLIB_OK:
            self.figure = Figure(figsize=(6, 4))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas, stretch=1)
        else:
            self.figure = None
            self.canvas = None
            layout.addWidget(QLabel("matplotlib is not installed.\nRun: pip install matplotlib"))

    def draw_zoom_chart(self, values, manual_values, search_value, x_min, x_max, y_min, y_max, parameter_name):
        if not _MATPLOTLIB_OK or self.figure is None or self.canvas is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        draw_smith_chart_grid(ax)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_title(f"Smith Chart Zoom - {parameter_name}", fontsize=10, fontweight="bold")
        if values.size > 0:
            ax.scatter(
                values.real,
                values.imag,
                c="#1565C0",
                s=16,
                alpha=0.9,
                edgecolors="none",
            )
        if manual_values.size > 0:
            ax.scatter(
                manual_values.real,
                manual_values.imag,
                marker="*",
                s=90,
                c="#D32F2F",
                edgecolors="white",
                linewidths=0.8,
                zorder=5,
            )
        if search_value is not None:
            ax.scatter(
                [search_value.real],
                [search_value.imag],
                marker="D",
                s=70,
                c="#000000",
                edgecolors="white",
                linewidths=0.8,
                zorder=6,
            )
        self.canvas.draw()


def _read_app_version() -> str:
    candidate_dirs = []
    if hasattr(sys, "_MEIPASS"):
        candidate_dirs.append(getattr(sys, "_MEIPASS"))
    candidate_dirs.extend([
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.abspath(sys.executable)),
    ])

    checked_paths = []
    for base_dir in candidate_dirs:
        version_path = os.path.join(base_dir, "VERSION")
        checked_paths.append(version_path)
        if not os.path.isfile(version_path):
            continue

        with open(version_path, encoding="utf-8") as version_file:
            version_text = version_file.read().strip()
        if not version_text:
            raise ValueError(f"VERSION file is empty: {version_path}")
        return version_text if version_text.upper().startswith("V") else f"V{version_text}"

    raise FileNotFoundError(
        "VERSION file not found. Checked: " + ", ".join(checked_paths)
    )


APP_VERSION = _read_app_version()


def is_float_text(text: str) -> bool:
    try:
        float(text)
        return True
    except Exception:
        return False


def clean_column_name(name: str) -> str:
    return str(name).replace("\ufeff", "").strip()


def normalize_key(name: str) -> str:
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


def _complex_to_t_matrix(s11: complex, s21: complex, s12: complex, s22: complex, context: str) -> np.ndarray:
    if abs(s21) <= 1e-18:
        raise ValueError(f"{context}: S21 is zero; cannot convert S to T.")

    determinant = s11 * s22 - s12 * s21
    return np.array(
        [
            [-determinant / s21, s11 / s21],
            [-s22 / s21, 1.0 / s21],
        ],
        dtype=np.complex128,
    )


def _t_matrix_to_s_parameters(t_matrix: np.ndarray, context: str):
    a11 = t_matrix[0, 0]
    a12 = t_matrix[0, 1]
    a21 = t_matrix[1, 0]
    a22 = t_matrix[1, 1]

    if abs(a22) <= 1e-18:
        raise ValueError(f"{context}: T22 is zero; cannot convert T to S.")

    s11 = a12 / a22
    s21 = 1.0 / a22
    s12 = ((a11 * a22) - (a12 * a21)) / a22
    s22 = -a21 / a22
    return s11, s21, s12, s22


def load_cable_s_parameters(file_path: str):
    if not file_path:
        return DEFAULT_CABLE_S_PARAMETERS, "default (no cable)"

    raw_df = pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8-sig")
    if raw_df.empty:
        raise ValueError("Cable file is empty.")

    rename_map = {}
    for column in raw_df.columns:
        normalized = normalize_key(column)
        if normalized in CABLE_REQUIRED_COLUMNS:
            rename_map[column] = normalized
    normalized_df = raw_df.rename(columns=rename_map)

    missing_columns = [column for column in CABLE_REQUIRED_COLUMNS if column not in normalized_df.columns]
    if missing_columns:
        raise ValueError(
            "Cable file is missing required columns: "
            + ", ".join(missing_columns)
            + ". Expected cable,S11R,S11X,S21R,S21X,S12R,S12X,S22R,S22X."
        )

    cable_rows = {}
    for record in normalized_df.itertuples(index=False):
        cable_name = normalize_key(getattr(record, "cable"))
        if cable_name not in ("cable1", "cable2"):
            continue
        cable_rows[cable_name] = {
            "s11": complex(float(getattr(record, "s11r")), float(getattr(record, "s11x"))),
            "s21": complex(float(getattr(record, "s21r")), float(getattr(record, "s21x"))),
            "s12": complex(float(getattr(record, "s12r")), float(getattr(record, "s12x"))),
            "s22": complex(float(getattr(record, "s22r")), float(getattr(record, "s22x"))),
        }

    for cable_name in ("cable1", "cable2"):
        if cable_name not in cable_rows:
            raise ValueError(f"Cable file must include both Cable1 and Cable2 rows. Missing {cable_name}.")

    return cable_rows, file_path


def deembed_s_parameters(df: pd.DataFrame, cable_s_parameters: dict) -> pd.DataFrame:
    cable1 = cable_s_parameters["cable1"]
    cable2 = cable_s_parameters["cable2"]
    cable1_t = _complex_to_t_matrix(cable1["s11"], cable1["s21"], cable1["s12"], cable1["s22"], "Cable1")
    cable2_t = _complex_to_t_matrix(cable2["s11"], cable2["s21"], cable2["s12"], cable2["s22"], "Cable2")
    cable1_t_inv = np.linalg.inv(cable1_t)
    cable2_t_inv = np.linalg.inv(cable2_t)

    result_df = df.copy()
    s11_values = result_df["S11_r"].to_numpy(dtype=float) + 1j * result_df["S11_x"].to_numpy(dtype=float)
    s21_values = result_df["S21_r"].to_numpy(dtype=float) + 1j * result_df["S21_x"].to_numpy(dtype=float)
    s12_values = result_df["S12_r"].to_numpy(dtype=float) + 1j * result_df["S12_x"].to_numpy(dtype=float)
    s22_values = result_df["S22_r"].to_numpy(dtype=float) + 1j * result_df["S22_x"].to_numpy(dtype=float)

    out_s11 = np.empty(len(result_df), dtype=np.complex128)
    out_s21 = np.empty(len(result_df), dtype=np.complex128)
    out_s12 = np.empty(len(result_df), dtype=np.complex128)
    out_s22 = np.empty(len(result_df), dtype=np.complex128)

    for row_index in range(len(result_df)):
        context = f"Row {row_index + 1}"
        measured_t = _complex_to_t_matrix(
            s11_values[row_index],
            s21_values[row_index],
            s12_values[row_index],
            s22_values[row_index],
            context,
        )
        deembedded_t = cable1_t_inv @ measured_t @ cable2_t_inv
        out_s11[row_index], out_s21[row_index], out_s12[row_index], out_s22[row_index] = _t_matrix_to_s_parameters(
            deembedded_t,
            context,
        )

    result_df["S11_r"] = out_s11.real
    result_df["S11_x"] = out_s11.imag
    result_df["S21_r"] = out_s21.real
    result_df["S21_x"] = out_s21.imag
    result_df["S12_r"] = out_s12.real
    result_df["S12_x"] = out_s12.imag
    result_df["S22_r"] = out_s22.real
    result_df["S22_x"] = out_s22.imag
    return result_df


def parse_cmd_line(cmd_line: str):
    """
    Example:
        caps hf  0 0 0 0

    Meaning:
        command = caps
        band = hf
        x1 = c1 coarse
        x2 = c1 fine
        x3 = c2 coarse
        x4 = c2 fine
    """
    tokens = cmd_line.strip().split()

    if len(tokens) < 6:
        raise ValueError(f"CMD line format error: {cmd_line}")

    command_name = tokens[0]
    band = tokens[1]

    c1_coarse = int(tokens[-4])
    c1_fine = int(tokens[-3])
    c2_coarse = int(tokens[-2])
    c2_fine = int(tokens[-1])

    x_c1 = c1_coarse * 64 + c1_fine
    y_c2 = c2_coarse * 64 + c2_fine

    return {
        "CMD_name": command_name,
        "Band": band,
        "C1_coarse": c1_coarse,
        "C1_fine": c1_fine,
        "C2_coarse": c2_coarse,
        "C2_fine": c2_fine,
        "X_C1": x_c1,
        "Y_C2": y_c2,
    }


def position_label(position_index: int) -> str:
    coarse = position_index // 64
    fine = position_index % 64
    return f"{coarse} {fine}"


def format_complex_text(real_value, imag_value):
    if pd.isna(real_value) or pd.isna(imag_value):
        return ""

    sign = "+" if imag_value >= 0 else "-"
    return f"{real_value:.3g}{sign}{abs(imag_value):.3g}i"


def format_phase_magnitude_text(complex_value, rotation_degrees=0):
    if complex_value is None:
        return ""

    rotated_value = complex_value * np.exp(1j * np.deg2rad(rotation_degrees))
    magnitude = abs(rotated_value)
    if magnitude < 1e-12:
        phase_degrees = 0.0
    else:
        phase_degrees = (np.degrees(np.angle(rotated_value)) + 360.0) % 360.0
    return f"{magnitude:.4g} ∠ {phase_degrees:.1f}°"


def parse_full_row(tokens):
    """
    Support row format like:

    1.29E+07 caps hf 0 0 0 0 1.31E-01 -2.52E-01 ...
    1.29E+07 caps hf ps1 0 0 0 0 1.31E-01 -2.52E-01 ...

    Total tokens:
        Frequency + command section + 8 S-parameter values
        command section may be either:
            caps hf x1 x2 x3 x4
        or:
            caps hf ps1 x1 x2 x3 x4
    """
    if len(tokens) < 15:
        raise ValueError("Not enough columns for one full row.")

    frequency = float(tokens[0])

    cmd_tokens = tokens[1:-8]
    if len(cmd_tokens) < 6:
        raise ValueError("Not enough command tokens in full row.")
    cmd_line = " ".join(cmd_tokens)
    cmd_info = parse_cmd_line(cmd_line)

    s_values = [float(v) for v in tokens[-8:]]

    row = {
        "Frequency": frequency,
        **cmd_info,
    }

    for col, value in zip(EXPECTED_S_COLUMNS, s_values):
        row[col] = value

    return row


def parse_vertical_block(lines, start_index):
    """
    Support vertical format like:

    Frequency
    CMD
    S11_r
    ...

    1.29E+07
    caps hf  0 0 0 0
    1.31E-01
    -2.52E-01
    ...
    """
    frequency_line = lines[start_index].strip()
    frequency = float(frequency_line)

    cmd_line = lines[start_index + 1].strip()
    cmd_info = parse_cmd_line(cmd_line)

    s_values = []
    for k in range(8):
        value_line = lines[start_index + 2 + k].strip()
        s_values.append(float(value_line))

    row = {
        "Frequency": frequency,
        **cmd_info,
    }

    for col, value in zip(EXPECTED_S_COLUMNS, s_values):
        row[col] = value

    next_index = start_index + 10
    return row, next_index


def find_header_row(file_path):
    """
    Find the first row that looks like the table header.

    This lets us ignore any title or comment lines before the data table.
    """
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        for index, line in enumerate(f):
            stripped = line.strip()
            if not stripped:
                continue

            tokens = [token.strip() for token in re.split(r"[,\t]+|\s{2,}", stripped) if token.strip()]
            normalized = {token for token in tokens}

            if "Frequency" in normalized and "CMD" in normalized and "S11_r" in normalized and "S22_x" in normalized:
                return index

    return None


def count_non_empty_data_lines(file_path, header_row):
    non_empty_count = 0
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        for index, line in enumerate(f):
            if index <= header_row:
                continue
            if line.strip():
                non_empty_count += 1
    return non_empty_count


def build_table_from_dataframe(raw_df, expected_data_rows=None):
    """
    Convert a CSV/TSV-style dataframe into the normalized X-Y table.
    """
    raw_df = raw_df.copy()
    raw_df.columns = [clean_column_name(column) for column in raw_df.columns]
    raw_df = raw_df.dropna(how="all")

    has_cmd_column = all(column in raw_df.columns for column in REQUIRED_TABLE_COLUMNS)
    has_expanded_columns = (
        "Frequency" in raw_df.columns
        and all(column in raw_df.columns for column in EXPANDED_CMD_COLUMNS)
        and all(column in raw_df.columns for column in EXPECTED_S_COLUMNS)
    )
    if not has_cmd_column and not has_expanded_columns:
        raise ValueError(
            "Missing required columns. Need either [Frequency, CMD, Sxx] or [Frequency, C1/C2 coarse/fine, Sxx]."
        )

    rows = []
    for record in raw_df.itertuples(index=False):
        try:
            frequency = float(getattr(record, "Frequency"))
            if has_cmd_column:
                cmd_info = parse_cmd_line(str(getattr(record, "CMD")))
            else:
                c1_coarse = int(float(getattr(record, "C1_coarse")))
                c1_fine = int(float(getattr(record, "C1_fine")))
                c2_coarse = int(float(getattr(record, "C2_coarse")))
                c2_fine = int(float(getattr(record, "C2_fine")))
                cmd_info = {
                    "CMD_name": "caps",
                    "Band": "hf",
                    "C1_coarse": c1_coarse,
                    "C1_fine": c1_fine,
                    "C2_coarse": c2_coarse,
                    "C2_fine": c2_fine,
                    "X_C1": c1_coarse * 64 + c1_fine,
                    "Y_C2": c2_coarse * 64 + c2_fine,
                }

            row = {
                "Frequency": frequency,
                **cmd_info,
            }

            for column in EXPECTED_S_COLUMNS:
                row[column] = float(getattr(record, column))

            rows.append(row)
        except Exception:
            continue

    if not rows:
        row_hint = f" (file has {expected_data_rows:,} data lines)" if expected_data_rows else ""
        raise ValueError(f"No valid data rows found. Please check file format.{row_hint}")

    df = pd.DataFrame(rows)
    return finalize_table(df)


def finalize_table(df):
    ordered_columns = [
        "Frequency",
        "CMD_name",
        "Band",
        "C1_coarse",
        "C1_fine",
        "C2_coarse",
        "C2_fine",
        "X_C1",
        "Y_C2",
        "S11_r",
        "S11_x",
        "S21_r",
        "S21_x",
        "S12_r",
        "S12_x",
        "S22_r",
        "S22_x",
    ]

    df = df[ordered_columns]
    df = df.sort_values(["X_C1", "Y_C2"]).reset_index(drop=True)
    df["X_Label"] = df["X_C1"].map(position_label)
    df["Y_Label"] = df["Y_C2"].map(position_label)

    return df[
        [
            "Frequency",
            "CMD_name",
            "Band",
            "C1_coarse",
            "C1_fine",
            "C2_coarse",
            "C2_fine",
            "X_C1",
            "X_Label",
            "Y_C2",
            "Y_Label",
            "S11_r",
            "S11_x",
            "S21_r",
            "S21_x",
            "S12_r",
            "S12_x",
            "S22_r",
            "S22_x",
        ]
    ]


def extract_xy_axis_values(df):
    """
    Return sorted X/Y axis positions that actually exist in the input data.
    Supports sparse/reduced fine-position formats.
    """
    x_values = sorted({int(value) for value in df["X_C1"].dropna().tolist()})
    y_values = sorted({int(value) for value in df["Y_C2"].dropna().tolist()})
    if not x_values or not y_values:
        raise ValueError("X-Y table is empty.")
    return x_values, y_values


def build_xy_display_table(df, parameter_name):
    """
    Build a spreadsheet-like X-Y table with header rows and headers inside the grid.
    """
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)

    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_complex_text(row[2], row[3])

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", parameter_name, "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def s_to_z_parameter_values(s11, s21, s12, s22, z0=DEFAULT_Z0):
    """Convert a 2-port S matrix to Z-parameters for one grid point."""
    if any(pd.isna(value) for value in [s11, s21, s12, s22]):
        return None

    denom = (1.0 - s11) * (1.0 - s22) - (s12 * s21)
    if abs(denom) < 1e-12:
        return None

    z11 = z0 * (((1.0 + s11) * (1.0 - s22)) + (s12 * s21)) / denom
    z12 = z0 * (2.0 * s12) / denom
    z21 = z0 * (2.0 * s21) / denom
    z22 = z0 * (((1.0 - s11) * (1.0 + s22)) + (s12 * s21)) / denom
    return {
        "Z11": z11,
        "Z12": z12,
        "Z21": z21,
        "Z22": z22,
    }


def build_zpar_display_table(df, parameter_name):
    """
    Build a spreadsheet-like X-Y table showing Z-parameters derived from the S matrix.
    """
    if parameter_name not in ZPAR_PARAMETERS:
        raise ValueError(f"Unknown Z parameter: {parameter_name}")

    required_columns = ["S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for Z-parameter conversion.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    for row in df[["X_C1", "Y_C2", "S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11 = complex(row[2], row[3])
        s21 = complex(row[4], row[5])
        s12 = complex(row[6], row[7])
        s22 = complex(row[8], row[9])

        z_values = s_to_z_parameter_values(s11, s21, s12, s22)
        if z_values is None:
            continue

        z_value = z_values[parameter_name]
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_complex_text(z_value.real, z_value.imag)

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Zpar({parameter_name})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def z_to_abcd_parameter_values(z11, z12, z21, z22):
    """Convert a 2-port Z matrix to ABCD parameters for one grid point."""
    if any(pd.isna(value) for value in [z11, z12, z21, z22]):
        return None

    if abs(z21) < 1e-12:
        return None

    determinant = (z11 * z22) - (z12 * z21)
    return {
        "A": z11 / z21,
        "B": determinant / z21,
        "C": 1.0 / z21,
        "D": z22 / z21,
    }


def build_abcd_display_table(df, parameter_name):
    """
    Build a spreadsheet-like X-Y table showing ABCD matrix terms derived from Z-parameters.
    """
    if parameter_name not in ABCD_PARAMETERS:
        raise ValueError(f"Unknown ABCD parameter: {parameter_name}")

    required_columns = ["S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for ABCD conversion.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    for row in df[["X_C1", "Y_C2", "S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11 = complex(row[2], row[3])
        s21 = complex(row[4], row[5])
        s12 = complex(row[6], row[7])
        s22 = complex(row[8], row[9])

        z_values = s_to_z_parameter_values(s11, s21, s12, s22)
        if z_values is None:
            continue

        abcd_values = z_to_abcd_parameter_values(
            z_values["Z11"],
            z_values["Z12"],
            z_values["Z21"],
            z_values["Z22"],
        )
        if abcd_values is None:
            continue

        abcd_value = abcd_values[parameter_name]
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_complex_text(abcd_value.real, abcd_value.imag)

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"ABCD({parameter_name})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_phase_magnitude_display_table(df, parameter_name, rotation_degrees=0):
    """
    Build a spreadsheet-like table that shows magnitude and phase in degrees.
    """
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        real_value = row[2]
        imag_value = row[3]
        if pd.isna(real_value) or pd.isna(imag_value):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_phase_magnitude_text(
            complex(real_value, imag_value),
            rotation_degrees=rotation_degrees,
        )

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Phase({parameter_name})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_contour_display_table(df, parameter_name):
    """
    Build a spreadsheet-like contour table that keeps only the outer edge values.
    """
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_min = x_values[0]
    x_max = x_values[-1]
    y_min = y_values[0]
    y_max = y_values[-1]
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        if x_pos not in (x_min, x_max) and y_pos not in (y_min, y_max):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_complex_text(row[2], row[3])

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Contour({parameter_name})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def reflect_to_impedance_value(s_r, s_x, z0=DEFAULT_Z0):
    """Convert reflection coefficient (S_r + j*S_x) to a complex impedance value."""
    if pd.isna(s_r) or pd.isna(s_x):
        return None

    gamma = complex(s_r, s_x)
    denom = 1.0 - gamma
    if abs(denom) < 1e-12:
        return None

    return z0 * (1.0 + gamma) / denom


def impedance_to_reflection_value(z_r, z_x, z0=DEFAULT_Z0):
    """Convert impedance (R + jX) to a reflection coefficient."""
    if pd.isna(z_r) or pd.isna(z_x):
        return None

    z = complex(z_r, z_x)
    denom = z + z0
    if abs(denom) < 1e-12:
        return None

    return (z - z0) / denom


def format_impedance_text(z_value):
    if z_value is None:
        return ""

    sign = "+" if z_value.imag >= 0 else "-"
    return f"{z_value.real:.6g}{sign}{abs(z_value.imag):.6g}j"


def calculate_zl_gamma_in0_value(z11, z12, z21, z22, z0=DEFAULT_Z0):
    """Return ZL for the Γin=0 condition using the Z-parameter formula."""
    if any(pd.isna(value) for value in [z11, z12, z21, z22]):
        return None

    denom = z0 - z11
    if abs(denom) < 1e-12:
        return None

    return -((z12 * z21) / denom) - z22


def find_nearest_load_impedance(df, c1_pct, c2_pct, parameter_name="S22", conjugate=False):
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    candidates = df[["X_C1", "Y_C2", real_col, imag_col]].dropna().copy()
    if candidates.empty:
        raise ValueError("No impedance data available.")

    x_max = float(candidates["X_C1"].max())
    y_max = float(candidates["Y_C2"].max())
    if x_max <= 0 or y_max <= 0:
        raise ValueError("Unable to resolve percentage positions from the loaded data.")

    candidates["X_pct"] = candidates["X_C1"] / x_max * 100.0
    candidates["Y_pct"] = candidates["Y_C2"] / y_max * 100.0
    candidates["distance"] = (candidates["X_pct"] - c1_pct) ** 2 + (candidates["Y_pct"] - c2_pct) ** 2
    best_row = candidates.sort_values(["distance", "X_C1", "Y_C2"]).iloc[0]

    gamma = complex(best_row[real_col], best_row[imag_col])
    if conjugate:
        gamma = np.conjugate(gamma)
    impedance = reflect_to_impedance_value(gamma.real, gamma.imag)
    if impedance is None:
        raise ValueError("Unable to calculate load impedance at the selected position.")

    return {
        "requested_c1_pct": float(c1_pct),
        "requested_c2_pct": float(c2_pct),
        "x_c1": int(best_row["X_C1"]),
        "y_c2": int(best_row["Y_C2"]),
        "x_c1_pct": float(best_row["X_pct"]),
        "y_c2_pct": float(best_row["Y_pct"]),
        "gamma": gamma,
        "impedance": impedance,
        "distance": float(np.sqrt(best_row["distance"])),
        "exact_match": abs(float(best_row["X_pct"]) - float(c1_pct)) < 1e-12 and abs(float(best_row["Y_pct"]) - float(c2_pct)) < 1e-12,
        "parameter_name": parameter_name,
    }


def reflect_to_impedance_text(s_r, s_x, z0=DEFAULT_Z0):
    """Convert reflection coefficient (S_r + j*S_x) to impedance text."""
    z = reflect_to_impedance_value(s_r, s_x, z0)
    if z is None:
        return "inf"

    sign = "+" if z.imag >= 0 else "-"
    return f"{z.real:.3g}{sign}{abs(z.imag):.3g}j"


def _format_complex_delta_text(value):
    if value is None:
        return ""

    if np.isnan(value.real) or np.isnan(value.imag):
        return ""

    if abs(value.real) < 1e-12 and abs(value.imag) < 1e-12:
        return "0"

    sign = "+" if value.imag >= 0 else "-"
    return f"{value.real:.3g}{sign}{abs(value.imag):.3g}j"


def build_impedance_matrix(df, parameter_name, z0=DEFAULT_Z0):
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)

    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}

    matrix = np.full((len(y_values), len(x_values)), np.nan + 0j, dtype=complex)

    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        z_value = reflect_to_impedance_value(row[2], row[3], z0)
        if z_value is None:
            continue
        matrix[y_lookup[y_pos]][x_lookup[x_pos]] = z_value

    return matrix, x_values, y_values


def build_impedance_display_table(df, parameter_name, z0=DEFAULT_Z0):
    """
    Build a spreadsheet-like X-Y table identical in layout to build_xy_display_table,
    but each cell contains impedance Z = Z0*(1+Γ)/(1-Γ) instead of the raw
    reflection coefficient.  Only meaningful for reflection parameters (S11, S22).
    """
    matrix, x_values, y_values = build_impedance_matrix(df, parameter_name, z0)
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Z({parameter_name})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        grid_row = []
        for value in matrix[y_index]:
            if np.isnan(value.real) or np.isnan(value.imag):
                grid_row.append("")
            else:
                sign = "+" if value.imag >= 0 else "-"
                grid_row.append(f"{value.real:.3g}{sign}{abs(value.imag):.3g}j")
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid_row,
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_zl_gin0_display_table(df, z0=DEFAULT_Z0):
    """Build a spreadsheet-like X-Y table showing ZL for Γin=0."""
    required_columns = ["S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for ZL calculation.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    iter_cols = [
        "X_C1", "Y_C2",
        "S11_r", "S11_x",
        "S21_r", "S21_x",
        "S12_r", "S12_x",
        "S22_r", "S22_x",
    ]

    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11 = complex(row[2], row[3])
        s21 = complex(row[4], row[5])
        s12 = complex(row[6], row[7])
        s22 = complex(row[8], row[9])

        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            continue

        z_load = calculate_zl_gamma_in0_value(
            z_values["Z11"],
            z_values["Z12"],
            z_values["Z21"],
            z_values["Z22"],
            z0,
        )
        if z_load is None:
            continue

        grid[y_lookup[y_pos]][x_lookup[x_pos]] = format_complex_text(z_load.real, z_load.imag)

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", "ZL,Γin=0", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_delta_impedance_display_table(df, orientation, z0=DEFAULT_Z0):
    """
    Build a spreadsheet-like X-Y table that shows delta impedance values for S22.
    Horizontal means delta against the previous C1 position in the same row.
    Vertical means delta against the previous C2 position in the same column.
    """
    if orientation not in ("S22 horizontal", "S22 vertical"):
        raise ValueError(f"Unknown delta-impedance orientation: {orientation}")

    matrix, x_values, y_values = build_impedance_matrix(df, "S22", z0)
    delta_matrix = np.full(matrix.shape, np.nan, dtype=float)

    if orientation == "S22 horizontal":
        delta_matrix[:, 0] = 0.0
        for row_index in range(len(y_values)):
            for col_index in range(1, len(x_values)):
                current = matrix[row_index, col_index]
                previous = matrix[row_index, col_index - 1]
                if np.isnan(current.real) or np.isnan(current.imag) or np.isnan(previous.real) or np.isnan(previous.imag):
                    continue
                delta_matrix[row_index, col_index] = abs(current - previous)
    else:
        delta_matrix[0, :] = 0.0
        for row_index in range(1, len(y_values)):
            for col_index in range(len(x_values)):
                current = matrix[row_index, col_index]
                previous = matrix[row_index - 1, col_index]
                if np.isnan(current.real) or np.isnan(current.imag) or np.isnan(previous.real) or np.isnan(previous.imag):
                    continue
                delta_matrix[row_index, col_index] = abs(current - previous)

    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"ΔZ({orientation})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        grid_row = []
        for value in delta_matrix[y_index]:
            if np.isnan(value):
                grid_row.append("")
            elif abs(value) < 1e-12:
                grid_row.append("0")
            else:
                grid_row.append(f"{value:.6g}")
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid_row,
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_delta_impedance_plot_data(df, z0=DEFAULT_Z0):
    """Return horizontal and vertical |ΔZ| grids for plotting."""
    matrix, x_values, y_values = build_impedance_matrix(df, "S22", z0)

    horizontal = np.full(matrix.shape, np.nan, dtype=float)
    vertical = np.full(matrix.shape, np.nan, dtype=float)

    horizontal[:, 0] = 0.0
    for row_index in range(len(y_values)):
        for col_index in range(1, len(x_values)):
            current = matrix[row_index, col_index]
            previous = matrix[row_index, col_index - 1]
            if np.isnan(current.real) or np.isnan(current.imag) or np.isnan(previous.real) or np.isnan(previous.imag):
                continue
            horizontal[row_index, col_index] = abs(current - previous)

    vertical[0, :] = 0.0
    for row_index in range(1, len(y_values)):
        for col_index in range(len(x_values)):
            current = matrix[row_index, col_index]
            previous = matrix[row_index - 1, col_index]
            if np.isnan(current.real) or np.isnan(current.imag) or np.isnan(previous.real) or np.isnan(previous.imag):
                continue
            vertical[row_index, col_index] = abs(current - previous)

    return horizontal, vertical, x_values, y_values


def build_reflection_coefficient_matrix(df, parameter_name):
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)

    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}

    matrix = np.full((len(y_values), len(x_values)), np.nan, dtype=float)

    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        real_value = row[2]
        imag_value = row[3]
        if pd.isna(real_value) or pd.isna(imag_value):
            continue
        matrix[y_lookup[y_pos]][x_lookup[x_pos]] = abs(complex(real_value, imag_value))

    return matrix, x_values, y_values


def build_delta_reflection_plot_data(df, parameter_name):
    """Return horizontal and vertical ΔΓ grids for plotting (current - previous)."""
    matrix, x_values, y_values = build_reflection_coefficient_matrix(df, parameter_name)

    horizontal = np.full(matrix.shape, np.nan, dtype=float)
    vertical = np.full(matrix.shape, np.nan, dtype=float)

    horizontal[:, 0] = 0.0
    for row_index in range(len(y_values)):
        for col_index in range(1, len(x_values)):
            current = matrix[row_index, col_index]
            previous = matrix[row_index, col_index - 1]
            if np.isnan(current) or np.isnan(previous):
                continue
            horizontal[row_index, col_index] = current - previous

    vertical[0, :] = 0.0
    for row_index in range(1, len(y_values)):
        for col_index in range(len(x_values)):
            current = matrix[row_index, col_index]
            previous = matrix[row_index - 1, col_index]
            if np.isnan(current) or np.isnan(previous):
                continue
            vertical[row_index, col_index] = current - previous

    return horizontal, vertical, x_values, y_values


def build_reflection_display_table(df, parameter_name, orientation):
    if orientation not in ("horizontal", "vertical"):
        raise ValueError(f"Unknown reflection orientation: {orientation}")

    horizontal, vertical, x_values, y_values = build_delta_reflection_plot_data(df, parameter_name)
    delta_matrix = horizontal if orientation == "horizontal" else vertical
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"ΔΓ({parameter_name} {orientation})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        grid_row = []
        for value in delta_matrix[y_index]:
            if np.isnan(value):
                grid_row.append("")
            elif abs(value) < 1e-12:
                grid_row.append("0")
            else:
                grid_row.append(f"{value:.6g}")
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid_row,
            ]
        )

    return pd.DataFrame(presentation_rows)


def _efficiency_mode_label(efficiency_mode):
    if efficiency_mode == "z_single":
        return "ηZ = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}"
    if efficiency_mode == "zl_gin0":
        return "ηZL,Γin=0 = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}"
    if efficiency_mode == "abcd_power":
        return "ηABCD = PL / Pin"
    if efficiency_mode == "h_squared":
        return "|S21|²·(1−|S22|²) / |1−S22²|²"
    if efficiency_mode == "overall":
        return "ηoverall = (1 - |S11|²) × |S21|²"
    if efficiency_mode == "s21_squared":
        return "|S21|²"
    raise ValueError(f"Unknown efficiency mode: {efficiency_mode}")


def calculate_efficiency_value(s11, s21, s12, s22, efficiency_mode, z0=DEFAULT_Z0):
    s11_magnitude = abs(s11)
    s21_magnitude = abs(s21)

    def _calculate_from_load(z_values, z_load):
        if z_load is None:
            return None
        z_sum = z_load + z_values["Z22"]
        d_z = (z_values["Z11"] * z_sum) - (z_values["Z12"] * z_values["Z21"])
        denominator = (d_z * np.conj(z_sum)).real
        numerator = z_load.real * (abs(z_values["Z21"]) ** 2)
        if not np.isfinite(denominator) or not np.isfinite(numerator) or denominator <= 1e-18:
            return None
        return numerator / denominator

    if efficiency_mode == "z_single":
        gamma_load = np.conj(s22)
        z_load = reflect_to_impedance_value(gamma_load.real, gamma_load.imag, z0)
        if z_load is None:
            return None

        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            return None

        return _calculate_from_load(z_values, z_load)

    if efficiency_mode == "zl_gin0":
        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            return None

        z_load = calculate_zl_gamma_in0_value(
            z_values["Z11"],
            z_values["Z12"],
            z_values["Z21"],
            z_values["Z22"],
            z0,
        )
        return _calculate_from_load(z_values, z_load)

    if efficiency_mode == "abcd_power":
        gamma_load = np.conj(s22)
        z_load = reflect_to_impedance_value(gamma_load.real, gamma_load.imag, z0)
        if z_load is None:
            return None

        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            return None

        abcd_values = z_to_abcd_parameter_values(
            z_values["Z11"],
            z_values["Z12"],
            z_values["Z21"],
            z_values["Z22"],
        )
        if abcd_values is None:
            return None

        i_load = 1.0 + 0.0j
        v2 = z_load * i_load
        v1 = (abcd_values["A"] * v2) + (abcd_values["B"] * i_load)
        i1 = (abcd_values["C"] * v2) + (abcd_values["D"] * i_load)
        if abs(i1) < 1e-18:
            return None

        z_in = v1 / i1
        if not np.isfinite(z_in.real) or not np.isfinite(z_in.imag):
            return None

        p_in = z_in.real * (abs(i1) ** 2)
        p_load = z_load.real * (abs(i_load) ** 2)
        if not np.isfinite(p_in) or not np.isfinite(p_load) or p_in <= 1e-18:
            return None

        return p_load / p_in

    if efficiency_mode == "h_squared":
        gamma_l = s22
        gamma_l_sq = abs(gamma_l) ** 2
        denom = 1.0 - s22 * gamma_l
        denom_sq = abs(denom) ** 2
        if denom_sq < 1e-18:
            return None
        return (s21_magnitude ** 2) * (1.0 - gamma_l_sq) / denom_sq

    if efficiency_mode == "overall":
        return (1.0 - (s11_magnitude ** 2)) * (s21_magnitude ** 2)

    if efficiency_mode == "s21_squared":
        return s21_magnitude ** 2

    raise ValueError(f"Unknown efficiency mode: {efficiency_mode}")


def build_efficiency_display_table(df, efficiency_mode):
    """
    Build a spreadsheet-like X-Y table showing efficiency values.
    """
    s11_r_col = "S11_r"
    s11_x_col = "S11_x"
    s21_r_col = "S21_r"
    s21_x_col = "S21_x"
    s12_r_col = "S12_r"
    s12_x_col = "S12_x"
    s22_r_col = "S22_r"
    s22_x_col = "S22_x"

    required_cols = [s11_r_col, s11_x_col, s21_r_col, s21_x_col]
    if efficiency_mode in ("z_single", "zl_gin0", "abcd_power"):
        required_cols.extend([s12_r_col, s12_x_col, s22_r_col, s22_x_col])
    elif efficiency_mode == "h_squared":
        required_cols.extend([s22_r_col, s22_x_col])

    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing columns required for efficiency calculation: {_efficiency_mode_label(efficiency_mode)}")

    x_values, y_values = extract_xy_axis_values(df)

    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]

    iter_cols = [
        "X_C1", "Y_C2",
        s11_r_col, s11_x_col,
        s21_r_col, s21_x_col,
        s12_r_col, s12_x_col,
        s22_r_col, s22_x_col,
    ]

    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11_real = row[2]
        s11_imag = row[3]
        s21_real = row[4]
        s21_imag = row[5]
        s12_real = row[6]
        s12_imag = row[7]
        s22_real = row[8]
        s22_imag = row[9]
        required_values = [s11_real, s11_imag, s21_real, s21_imag]
        if efficiency_mode in ("z_single", "zl_gin0", "abcd_power"):
            required_values.extend([s12_real, s12_imag, s22_real, s22_imag])
        elif efficiency_mode == "h_squared":
            required_values.extend([s22_real, s22_imag])
        if any(pd.isna(value) for value in required_values):
            continue
        s11 = complex(s11_real, s11_imag)
        s21 = complex(s21_real, s21_imag)
        s12 = complex(s12_real, s12_imag) if not (pd.isna(s12_real) or pd.isna(s12_imag)) else 0.0 + 0.0j
        s22 = complex(s22_real, s22_imag) if not (pd.isna(s22_real) or pd.isna(s22_imag)) else 0.0 + 0.0j
        efficiency = calculate_efficiency_value(s11, s21, s12, s22, efficiency_mode)
        if efficiency is None or not np.isfinite(efficiency):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = f"{efficiency:.4f}"

    mode_label = _efficiency_mode_label(efficiency_mode)

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Efficiency({mode_label})", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def _iout_mode_label(iout_mode):
    if iout_mode == "abcd":
        return "Formula 1: Iout = -C·V1 + A·I1"
    if iout_mode == "z_formula":
        return "Formula 2: Iout = Z21·V1 / DZ"
    if iout_mode == "z_formula3":
        return "Formula 3: Iout = (Z21 / (Z11 + Z22)) × I1"
    if iout_mode == "z_formula4":
        return "Formula 4: Iout = (Z11·I1 - V1) / Z12"
    raise ValueError(f"Unknown Iout mode: {iout_mode}")


def build_iout_display_table(df, input_power_watts, iout_mode="z_formula", z0=DEFAULT_Z0):
    """
    Build a spreadsheet-like X-Y table showing Iout from the selected formula.
    Assumes input impedance is 50 ohm and power is user-defined.
    """
    required_columns = ["S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for Iout calculation.")
    if input_power_watts <= 0:
        raise ValueError("Input power must be greater than 0 W.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    input_impedance = 50.0
    v1 = np.sqrt(input_power_watts * input_impedance)
    i1 = np.sqrt(input_power_watts / input_impedance)

    grid = [["" for _ in x_values] for _ in y_values]
    iter_cols = [
        "X_C1", "Y_C2",
        "S11_r", "S11_x",
        "S21_r", "S21_x",
        "S12_r", "S12_x",
        "S22_r", "S22_x",
    ]
    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11 = complex(row[2], row[3])
        s21 = complex(row[4], row[5])
        s12 = complex(row[6], row[7])
        s22 = complex(row[8], row[9])

        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            continue
        abcd_values = z_to_abcd_parameter_values(
            z_values["Z11"],
            z_values["Z12"],
            z_values["Z21"],
            z_values["Z22"],
        )
        if abcd_values is None:
            continue

        if iout_mode == "abcd":
            iout = (-abcd_values["C"] * v1) + (abcd_values["A"] * i1)
        elif iout_mode == "z_formula":
            gamma_load = np.conj(s22)
            z_load = reflect_to_impedance_value(gamma_load.real, gamma_load.imag, z0)
            if z_load is None:
                continue
            z_sum = z_load + z_values["Z22"]
            d_z = (z_values["Z11"] * z_sum) - (z_values["Z12"] * z_values["Z21"])
            if abs(d_z) < 1e-18:
                continue
            iout = (z_values["Z21"] * v1) / d_z
        elif iout_mode == "z_formula3":
            z_sum = z_values["Z11"] + z_values["Z22"]
            if abs(z_sum) < 1e-18:
                continue
            iout = (z_values["Z21"] / z_sum) * i1
        elif iout_mode == "z_formula4":
            if abs(z_values["Z12"]) < 1e-18:
                continue
            iout = (z_values["Z11"] * i1 - v1) / z_values["Z12"]
        else:
            raise ValueError(f"Unknown Iout mode: {iout_mode}")
        if not np.isfinite(iout.real) or not np.isfinite(iout.imag):
            continue
        iout_rms = abs(iout)
        if not np.isfinite(iout_rms):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = f"{iout_rms:.6g}"

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    mode_label = _iout_mode_label(iout_mode)
    presentation_rows.append(["", f"Iout RMS(A) ({mode_label}, Pin={input_power_watts:.4g}W, Zin=50Ω)", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_vpp_display_table(df, input_power_watts, z0=DEFAULT_Z0):
    """
    Build a spreadsheet-like X-Y table showing Vpp from:
      Vrms = ZL*Z21*V1 / DZ
      Vpp = 2*sqrt(2)*|Vrms|
    """
    required_columns = ["S11_r", "S11_x", "S21_r", "S21_x", "S12_r", "S12_x", "S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for Vpp calculation.")
    if input_power_watts <= 0:
        raise ValueError("Input power must be greater than 0 W.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    input_impedance = 50.0
    v1 = np.sqrt(input_power_watts * input_impedance)

    grid = [["" for _ in x_values] for _ in y_values]
    iter_cols = [
        "X_C1", "Y_C2",
        "S11_r", "S11_x",
        "S21_r", "S21_x",
        "S12_r", "S12_x",
        "S22_r", "S22_x",
    ]
    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11 = complex(row[2], row[3])
        s21 = complex(row[4], row[5])
        s12 = complex(row[6], row[7])
        s22 = complex(row[8], row[9])

        gamma_load = np.conj(s22)
        z_load = reflect_to_impedance_value(gamma_load.real, gamma_load.imag, z0)
        if z_load is None:
            continue

        z_values = s_to_z_parameter_values(s11, s21, s12, s22, z0)
        if z_values is None:
            continue

        z_sum = z_load + z_values["Z22"]
        d_z = (z_values["Z11"] * z_sum) - (z_values["Z12"] * z_values["Z21"])
        if abs(d_z) < 1e-18:
            continue

        v_rms = (z_load * z_values["Z21"] * v1) / d_z
        if not np.isfinite(v_rms.real) or not np.isfinite(v_rms.imag):
            continue
        vpp = 2.0 * np.sqrt(2.0) * abs(v_rms)
        if not np.isfinite(vpp):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = f"{vpp:.6g}"

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", f"Vpp(V) (Pin={input_power_watts:.4g}W, Zin=50Ω)", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def build_phi_out_display_table(df, z0=DEFAULT_Z0):
    """
    Build a spreadsheet-like X-Y table showing φ_out (phase angle of load impedance) from:
      ZL = reflect_to_impedance_value(conj(S22))
      φ_out = tan⁻¹(XL / RL)
    where XL is imaginary part and RL is real part of ZL.
    """
    required_columns = ["S22_r", "S22_x"]
    if not all(column in df.columns for column in required_columns):
        raise ValueError("Missing S-parameter columns required for φ_out calculation.")

    x_values, y_values = extract_xy_axis_values(df)
    x_lookup = {value: index for index, value in enumerate(x_values)}
    y_lookup = {value: index for index, value in enumerate(y_values)}
    x_denominator = max(x_values) if max(x_values) > 0 else 1
    y_denominator = max(y_values) if max(y_values) > 0 else 1

    grid = [["" for _ in x_values] for _ in y_values]
    iter_cols = ["X_C1", "Y_C2", "S22_r", "S22_x"]
    
    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s22 = complex(row[2], row[3])

        gamma_load = np.conj(s22)
        z_load = reflect_to_impedance_value(gamma_load.real, gamma_load.imag, z0)
        if z_load is None:
            continue

        rl = z_load.real
        xl = z_load.imag
        
        if abs(rl) < 1e-18:
            continue
        
        phi_out_rad = np.arctan(xl / rl)
        phi_out_deg = np.degrees(phi_out_rad)
        
        if not np.isfinite(phi_out_deg):
            continue
        grid[y_lookup[y_pos]][x_lookup[x_pos]] = f"{phi_out_deg:.6g}"

    presentation_rows = []
    presentation_rows.append(["", "", "c1 coarse"] + [str(x // 64) for x in x_values])
    presentation_rows.append(["", "φ_out(°) = tan⁻¹(XL/RL)", "c1 fine"] + [str(x % 64) for x in x_values])
    presentation_rows.append(["C2 coarse", "c2 fine", "percentage"] + [f"{(x / x_denominator) * 100:.2f}%" for x in x_values])

    for y_index, y_value in enumerate(y_values):
        presentation_rows.append(
            [
                str(y_value // 64),
                str(y_value % 64),
                f"{(y_value / y_denominator) * 100:.2f}%",
                *grid[y_index],
            ]
        )

    return pd.DataFrame(presentation_rows)


def extract_heatmap_data_from_table(df_display):
    """
    Extract numeric heatmap data from a display table.
    Assumes the first 3 rows are headers and first 3 columns are labels.
    Returns a 2D numpy array of floats for visualization.
    """
    if df_display is None or df_display.empty:
       return np.array([])
    
    data_rows = df_display.iloc[3:, 3:]
    numeric_data = []
    
    for _, row in data_rows.iterrows():
       numeric_row = []
       for val in row:
           try:
               if isinstance(val, str) and val.strip():
                   numeric_row.append(float(val))
               else:
                   numeric_row.append(np.nan)
           except (ValueError, TypeError):
               numeric_row.append(np.nan)
       if numeric_row:
           numeric_data.append(numeric_row)
    
    if numeric_data:
       return np.array(numeric_data, dtype=float)
    return np.array([])


def build_smith_chart_plot_data(df, parameter_name):
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    points = []
    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        real_value = row[2]
        imag_value = row[3]
        if pd.isna(real_value) or pd.isna(imag_value):
            continue
        gamma = complex(real_value, imag_value)
        impedance = reflect_to_impedance_value(real_value, imag_value) if parameter_name in IMPEDANCE_PARAMETERS else None
        points.append({
            "x_c1": int(row[0]),
            "y_c2": int(row[1]),
            "gamma": gamma,
            "impedance": impedance,
        })

    return points


def build_smith_contour_plot_data(df, parameter_name):
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_values, y_values = extract_xy_axis_values(df)
    point_lookup = {}
    for row in df[["X_C1", "Y_C2", real_col, imag_col]].itertuples(index=False):
        real_value = row[2]
        imag_value = row[3]
        if pd.isna(real_value) or pd.isna(imag_value):
            continue
        key = (int(row[0]), int(row[1]))
        point_lookup[key] = {
            "x_c1": key[0],
            "y_c2": key[1],
            "gamma": complex(real_value, imag_value),
            "impedance": reflect_to_impedance_value(real_value, imag_value) if parameter_name in IMPEDANCE_PARAMETERS else None,
        }

    x_min = x_values[0]
    x_max = x_values[-1]
    y_min = y_values[0]
    y_max = y_values[-1]
    ordered_keys = []
    ordered_keys.extend((x_min, y_value) for y_value in y_values)
    ordered_keys.extend((x_value, y_max) for x_value in x_values[1:])
    ordered_keys.extend((x_max, y_value) for y_value in reversed(y_values[:-1]))
    ordered_keys.extend((x_value, y_min) for x_value in reversed(x_values[:-1]))

    points = []
    for key in ordered_keys:
        point = point_lookup.get(key)
        if point is not None:
            points.append(point)

    if points:
        points.append(points[0])

    return points


def build_smith_dz_lookup(df, z0=DEFAULT_Z0):
    """
    Build a lookup table for Smith-chart dZ coloring.
    Value is max(horizontal |ΔZ|, vertical |ΔZ|) at each X/Y point.
    """
    horizontal, vertical, x_values, y_values = build_delta_impedance_plot_data(df, z0)
    dz_lookup = {}

    for y_index, y_value in enumerate(y_values):
        for x_index, x_value in enumerate(x_values):
            candidates = []
            h_value = horizontal[y_index, x_index]
            v_value = vertical[y_index, x_index]
            if np.isfinite(h_value):
                candidates.append(float(h_value))
            if np.isfinite(v_value):
                candidates.append(float(v_value))
            if not candidates:
                continue
            dz_lookup[(int(x_value), int(y_value))] = max(candidates)

    return dz_lookup


def build_smith_dgamma_lookup(df, parameter_name, orientation):
    """
    Build a lookup table for Smith-chart dΓ coloring using delta-Γ resolution.
    """
    horizontal, vertical, x_values, y_values = build_delta_reflection_plot_data(df, parameter_name)
    delta_matrix = horizontal if orientation == "horizontal" else vertical

    dgamma_lookup = {}
    for y_index, y_value in enumerate(y_values):
        for x_index, x_value in enumerate(x_values):
            value = delta_matrix[y_index, x_index]
            if not np.isfinite(value):
                continue
            dgamma_lookup[(int(x_value), int(y_value))] = abs(float(value))

    return dgamma_lookup


def build_smith_efficiency_lookup(df, efficiency_mode="zl_gin0"):
    """
    Build a lookup table for Smith-chart efficiency coloring.
    Supports six modes:
      'z_single' : ηZ = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}
      'zl_gin0'  : ηZL,Γin=0 = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*} (default)
      'abcd_power': ηABCD = PL / Pin
      'h_squared' : |S21|²·(1−|S22|²) / |1−S22²|²
      'overall'   : (1 - |S11|²) × |S21|²
      's21_squared': |S21|²
    """
    s11_r_col = "S11_r"
    s11_x_col = "S11_x"
    s21_r_col = "S21_r"
    s21_x_col = "S21_x"
    s12_r_col = "S12_r"
    s12_x_col = "S12_x"
    s22_r_col = "S22_r"
    s22_x_col = "S22_x"

    required_cols = [s11_r_col, s11_x_col, s21_r_col, s21_x_col]
    if efficiency_mode in ("z_single", "zl_gin0", "abcd_power"):
        required_cols.extend([s12_r_col, s12_x_col, s22_r_col, s22_x_col])
    elif efficiency_mode == "h_squared":
        required_cols.extend([s22_r_col, s22_x_col])

    if not all(col in df.columns for col in required_cols):
        return {}

    iter_cols = [
        "X_C1", "Y_C2",
        s11_r_col, s11_x_col,
        s21_r_col, s21_x_col,
        s12_r_col, s12_x_col,
        s22_r_col, s22_x_col,
    ]

    efficiency_lookup = {}
    for row in df[iter_cols].itertuples(index=False):
        x_pos = int(row[0])
        y_pos = int(row[1])
        s11_real = row[2]
        s11_imag = row[3]
        s21_real = row[4]
        s21_imag = row[5]
        s12_real = row[6]
        s12_imag = row[7]
        s22_real = row[8]
        s22_imag = row[9]
        required_values = [s11_real, s11_imag, s21_real, s21_imag]
        if efficiency_mode in ("z_single", "zl_gin0", "abcd_power"):
            required_values.extend([s12_real, s12_imag, s22_real, s22_imag])
        elif efficiency_mode == "h_squared":
            required_values.extend([s22_real, s22_imag])
        if any(pd.isna(value) for value in required_values):
            continue
        s11 = complex(s11_real, s11_imag)
        s21 = complex(s21_real, s21_imag)
        s12 = complex(s12_real, s12_imag) if not (pd.isna(s12_real) or pd.isna(s12_imag)) else 0.0 + 0.0j
        s22 = complex(s22_real, s22_imag) if not (pd.isna(s22_real) or pd.isna(s22_imag)) else 0.0 + 0.0j
        efficiency = calculate_efficiency_value(s11, s21, s12, s22, efficiency_mode)
        if efficiency is None or not np.isfinite(efficiency):
            continue
        efficiency_lookup[(x_pos, y_pos)] = float(efficiency)

    return efficiency_lookup


def draw_smith_chart_grid(ax):
    ax.clear()
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_xlabel("Real")
    ax.set_ylabel("Imaginary")
    ax.set_title("Smith Chart", fontsize=11, fontweight="bold")

    ax.axhline(0, color="#B0BEC5", linewidth=0.8)
    ax.axvline(0, color="#B0BEC5", linewidth=0.8)

    unit_circle = plt_circle = None
    try:
        from matplotlib.patches import Circle
        plt_circle = Circle((0, 0), 1.0, fill=False, edgecolor="#263238", linewidth=1.2)
        ax.add_patch(plt_circle)
    except Exception:
        pass

    resistance_values = [0.0, 0.2, 0.5, 1.0, 2.0, 5.0]
    for resistance in resistance_values:
        center = resistance / (1.0 + resistance)
        radius = 1.0 / (1.0 + resistance)
        circle = None
        try:
            from matplotlib.patches import Circle
            circle = Circle((center, 0), radius, fill=False, edgecolor="#CFD8DC", linewidth=0.8)
            ax.add_patch(circle)
        except Exception:
            pass

    reactance_values = [0.2, 0.5, 1.0, 2.0, 5.0]
    rs = np.linspace(0.0, 20.0, 700)
    for reactance in reactance_values:
        for sign in (1.0, -1.0):
            zs = rs + 1j * (sign * reactance)
            gammas = (zs - 1.0) / (zs + 1.0)
            ax.plot(gammas.real, gammas.imag, color="#CFD8DC", linewidth=0.8)

    ax.text(0.98, 0.02, "1 + j0", ha="right", va="bottom", fontsize=8, color="#607D8B")
    ax.text(-0.98, 0.02, "0 + j0", ha="left", va="bottom", fontsize=8, color="#607D8B")
    ax.grid(False)


def calculate_cap_array(coarse_step_pf: float, fine_caps_pf: list) -> np.ndarray:
    """
    Calculate the equivalent capacitance for all 448 positions.

    The cap bank has:
      - 7 coarse states  (index 0-6), each step adds coarse_step_pf
      - 64 fine states   (index 0-63), binary-weighted:
            C_fine[s] = sum(fine_caps_pf[k] * bit_k(s)  for k in 0..5)
        where fine_caps_pf = [Fine1, Fine2, Fine3, Fine4, Fine5, Fine6]
        and Fine1 is the LSB (bit 0), Fine6 is the MSB (bit 5).

    Total positions = 7 * 64 = 448.
    position index = coarse_index * 64 + fine_state
    C[pos] = coarse_index * coarse_step_pf + C_fine[fine_state]
    """
    fine_caps = np.array(fine_caps_pf, dtype=float)          # shape (6,)
    fine_states = np.arange(64, dtype=int)
    bits = ((fine_states[:, np.newaxis] >> np.arange(6)) & 1).astype(float)  # (64, 6)
    fine_values = bits @ fine_caps                            # shape (64,)

    coarse_values = np.arange(7, dtype=float) * coarse_step_pf  # shape (7,)
    cap_matrix = coarse_values[:, np.newaxis] + fine_values[np.newaxis, :]   # (7, 64)
    return cap_matrix.flatten()                               # shape (448,)


def parse_match_file(file_path):
    """
    This parser supports two possible formats:

    Format A: one full data row per line
        1.29E+07 caps hf 0 0 0 0 1.31E-01 ...

    Format B: vertical/block style
        1.29E+07
        caps hf 0 0 0 0
        1.31E-01
        ...

    Output:
        DataFrame with X_C1 and Y_C2.
    """
    header_row = find_header_row(file_path)

    if header_row is not None:
        data_line_count = count_non_empty_data_lines(file_path, header_row)
        if data_line_count in (FULL_GRID_ROWS, REDUCED_GRID_ROWS):
            print(f"Info: detected grid data lines = {data_line_count:,}.")

        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            header_line = None
            for index, line in enumerate(f):
                if index == header_row:
                    header_line = line
                    break

        delimiter = ","
        if header_line is not None and "\t" in header_line and "," not in header_line:
            delimiter = "\t"
        header_columns = []
        if header_line is not None:
            if delimiter == "\t":
                header_columns = [clean_column_name(token) for token in header_line.strip().split("\t")]
            else:
                header_columns = [clean_column_name(token) for token in header_line.strip().split(",")]
            header_columns = [token for token in header_columns if token]
        usecols = list(range(len(header_columns))) if header_columns else None

        csv_attempts = [
            {"sep": delimiter, "engine": "python" if delimiter == "\t" else "c", "usecols": usecols},
            {"sep": None, "engine": "python", "usecols": usecols},
            {"sep": delimiter, "engine": "python" if delimiter == "\t" else "c", "usecols": None},
        ]
        for attempt in csv_attempts:
            try:
                raw_df = pd.read_csv(
                    file_path,
                    skiprows=header_row,
                    encoding="utf-8-sig",
                    sep=attempt["sep"],
                    engine=attempt["engine"],
                    usecols=attempt["usecols"],
                )
                if len(raw_df.columns) > 1:
                    return build_table_from_dataframe(raw_df, expected_data_rows=data_line_count)
            except Exception as exc:
                print(
                    f"Warning: CSV parser attempt failed (sep={attempt['sep']}, engine={attempt['engine']}, usecols={'header' if attempt['usecols'] is not None else 'all'}). "
                    f"Reason: {exc}"
                )

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    rows = []
    i = 0

    header_words = {
        "Frequency", "CMD",
        "S11_r", "S11_x",
        "S21_r", "S21_x",
        "S12_r", "S12_x",
        "S22_r", "S22_x",
    }

    while i < len(raw_lines):
        line = raw_lines[i]
        tokens = line.split()

        if not tokens:
            i += 1
            continue

        if tokens[0] in header_words:
            i += 1
            continue

        try:
            # Case A: one complete data row in one line
            if len(tokens) >= 15 and is_float_text(tokens[0]) and tokens[1].lower() == "caps":
                row = parse_full_row(tokens)
                rows.append(row)
                i += 1
                continue

            # Case B: vertical block format
            if len(tokens) == 1 and is_float_text(tokens[0]):
                if i + 9 < len(raw_lines):
                    row, next_i = parse_vertical_block(raw_lines, i)
                    rows.append(row)
                    i = next_i
                    continue

            # If the line is not recognized, skip it
            i += 1

        except Exception as e:
            print(f"Warning: failed to parse near line index {i}: {line}")
            print(f"Reason: {e}")
            i += 1

    if not rows:
        raise ValueError("No valid data rows found. Please check file format.")

    df = pd.DataFrame(rows)
    return finalize_table(df)


class PandasTableModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self.df = df if df is not None else pd.DataFrame()

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return len(self.df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        value = self.df.iat[row, col]
        column_name = str(self.df.columns[col])

        if role == Qt.DisplayRole:
            if isinstance(value, float):
                return f"{value:.6g}"
            return str(value)

        if role == Qt.BackgroundRole:
            if column_name == "X_C1":
                return QBrush(QColor("#E3F2FD"))
            if column_name == "Y_C2":
                return QBrush(QColor("#E8F5E9"))
            if column_name.startswith("S11"):
                return QBrush(QColor("#FFF3E0"))
            if column_name.startswith("S22"):
                return QBrush(QColor("#FCE4EC"))

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.df.columns[section])
            return str(section + 1)

        if role == Qt.FontRole and orientation == Qt.Horizontal:
            font = QFont()
            font.setBold(True)
            return font

        if role == Qt.BackgroundRole and orientation == Qt.Horizontal:
            return QBrush(QColor("#263238"))

        if role == Qt.ForegroundRole and orientation == Qt.Horizontal:
            return QBrush(QColor("white"))

        return None


class ManualImpedanceTableModel(QAbstractTableModel):
    def __init__(self, row_count=5):
        super().__init__()
        self.df = pd.DataFrame({"R": ["" for _ in range(row_count)], "X": ["" for _ in range(row_count)]})

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:
                return str(row + 1)
            value = self.df.iat[row, col - 1]
            return "" if pd.isna(value) else str(value)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ["ID", "R", "X"][section]
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return str(section + 1)
        if role == Qt.FontRole and orientation == Qt.Horizontal:
            font = QFont()
            font.setBold(True)
            return font
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or index.column() == 0:
            return False

        text = str(value).strip()
        self.df.iat[index.row(), index.column() - 1] = text
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def add_blank_row(self):
        self.beginInsertRows(QModelIndex(), len(self.df), len(self.df))
        self.df = pd.concat([self.df, pd.DataFrame([{"R": "", "X": ""}])], ignore_index=True)
        self.endInsertRows()

    def clear_values(self):
        self.beginResetModel()
        self.df = pd.DataFrame({"R": ["" for _ in range(len(self.df))], "X": ["" for _ in range(len(self.df))]})
        self.endResetModel()

    def set_next_available_point(self, r_value, x_value):
        target_row = None
        for row_index, row in self.df.iterrows():
            if str(row["R"]).strip() == "" and str(row["X"]).strip() == "":
                target_row = row_index
                break

        if target_row is None:
            self.add_blank_row()
            target_row = len(self.df) - 1

        self.df.iat[target_row, 0] = f"{r_value:.6g}"
        self.df.iat[target_row, 1] = f"{x_value:.6g}"
        left = self.index(target_row, 1)
        right = self.index(target_row, 2)
        self.dataChanged.emit(left, right, [Qt.DisplayRole, Qt.EditRole])
        return target_row + 1

    def iter_points(self):
        for row_index, row in self.df.iterrows():
            r_text = str(row["R"]).strip()
            x_text = str(row["X"]).strip()
            if not r_text or not x_text:
                continue
            if not is_float_text(r_text) or not is_float_text(x_text):
                continue
            yield row_index + 1, float(r_text), float(x_text)


class MatchResolutionGui(QMainWindow):
    def __init__(self, startup_status_callback=None):
        super().__init__()
        self.startup_status_callback = startup_status_callback

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} - Step 1: CMD to X-Y Table")
        self.resize(1400, 850)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

        self.df_all = None
        self.df_display = None
        self.df_xy_display = None
        self.current_xy_parameter = "S22"
        self.df_phase_display = None
        self.current_phase_parameter = "S22"
        self.phase_rotation_degrees = 0
        self.df_contour_display = None
        self.current_contour_parameter = "S22"
        self.df_impedance_display = None
        self.current_impedance_parameter = "S22"
        self.df_zl_display = None
        self.df_zpar_display = None
        self.current_zpar_parameter = "Z22"
        self.df_abcd_display = None
        self.current_abcd_parameter = "A"
        self.df_dz_display = None
        self.current_dz_parameter = "S22 horizontal"
        self.df_reflection_display = None
        self.current_reflection_parameter = "S22"
        self.current_reflection_mode = "horizontal"
        self.df_efficiency_display = None
        self.current_efficiency_mode = "zl_gin0"
        self.df_iout_display = None
        self.current_iout_mode = "z_formula"
        self.input_power_watts = 100.0
        self.df_vpp_display = None
        self.vpp_power_watts = 100.0
        self.df_phi_out_display = None
        self.smith_manual_points = []
        self.smith_search_result = None
        self.manual_impedance_model = None
        self.df_smith_points = None
        self.current_smith_parameter = "S22"
        self.smith_plot_points = []
        self.smith_plot_values = np.array([], dtype=complex)
        self.smith_scatter = None
        self.smith_conjugate_enabled = False
        self.smith_zoom_selection_enabled = False
        self.smith_zoom_start = None
        self.smith_zoom_rect = None
        self.smith_zoom_windows = []
        self.current_smith_mode = "efficiency"
        self.smith_dz_lookup = {}
        self.smith_dgamma_lookup = {}
        self.smith_efficiency_lookup = {}
        self.efficiency_good_threshold = 1.0
        self.efficiency_poor_threshold = 0.1
        self.current_cable_source = "default (no cable)"

        self.init_ui()

    def _startup_status(self, message, progress=None):
        if self.startup_status_callback is not None:
            self.startup_status_callback(message, progress)

    def init_ui(self):
        self._startup_status("Building main interface...", 10)
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        title = QLabel("RF Matching Network Palantir")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: white;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1565C0,
                    stop:0.5 #00897B,
                    stop:1 #6A1B9A
                );
                padding: 18px;
                border-radius: 14px;
            }
        """)
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Feature 1: Convert CMD caps hf x1 x2 x3 x4 into X-Y table "
            "| X = C1 coarse/fine position, Y = C2 coarse/fine position"
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 15px; color: #37474F; padding: 8px;")
        main_layout.addWidget(subtitle)

        file_frame = QFrame()
        file_frame.setStyleSheet("""
            QFrame {
                background-color: #ECEFF1;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        file_layout = QVBoxLayout(file_frame)
        file_layout.setSpacing(8)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select raw network analyzer data file...")
        self.file_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #90A4AE;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)

        browse_button = QPushButton("Browse File")
        browse_button.clicked.connect(self.browse_file)

        convert_button = QPushButton("Convert")
        convert_button.clicked.connect(self.convert_file)

        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self.export_csv)

        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(lambda: QApplication.instance().quit())

        for button in [browse_button, convert_button, export_button, exit_button]:
            button.setMinimumHeight(38)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border-radius: 8px;
                    padding-left: 18px;
                    padding-right: 18px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0D47A1;
                }
                QPushButton:pressed {
                    background-color: #002171;
                }
            """)

        export_button.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border-radius: 8px;
                padding-left: 18px;
                padding-right: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
            QPushButton:pressed {
                background-color: #003300;
            }
        """)

        exit_button.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border-radius: 8px;
                padding-left: 18px;
                padding-right: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
            QPushButton:pressed {
                background-color: #7F0000;
            }
        """)

        main_file_row = QHBoxLayout()
        main_file_row.addWidget(QLabel("File:"))
        main_file_row.addWidget(self.file_path_edit, stretch=1)
        main_file_row.addWidget(browse_button)
        main_file_row.addWidget(convert_button)
        main_file_row.addWidget(export_button)
        main_file_row.addWidget(exit_button)
        file_layout.addLayout(main_file_row)

        self.cable_file_path_edit = QLineEdit()
        self.cable_file_path_edit.setPlaceholderText(
            "Optional cable file (Cable1/Cable2 S-parameters). Leave empty to use default no-cable values."
        )
        self.cable_file_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #90A4AE;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        cable_browse_button = QPushButton("Browse Cable File")
        cable_browse_button.clicked.connect(self.browse_cable_file)
        cable_browse_button.setMinimumHeight(38)
        cable_browse_button.setStyleSheet("""
            QPushButton {
                background-color: #455A64;
                color: white;
                border-radius: 8px;
                padding-left: 18px;
                padding-right: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #263238;
            }
            QPushButton:pressed {
                background-color: #1C313A;
            }
        """)
        cable_row = QHBoxLayout()
        cable_row.addWidget(QLabel("Cable:"))
        cable_row.addWidget(self.cable_file_path_edit, stretch=1)
        cable_row.addWidget(cable_browse_button)
        file_layout.addLayout(cable_row)

        main_layout.addWidget(file_frame)
        self._startup_status("Preparing analysis tabs...", 30)

        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #CFD8DC;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)

        self.total_rows_label = QLabel("Total rows: -")
        self.frequency_label = QLabel("Frequency: -")
        self.x_range_label = QLabel("X_C1 range: -")
        self.y_range_label = QLabel("Y_C2 range: -")
        self.display_label = QLabel("Display: -")

        for label in [
            self.total_rows_label,
            self.frequency_label,
            self.x_range_label,
            self.y_range_label,
            self.display_label,
        ]:
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    color: #263238;
                    padding: 6px;
                }
            """)
            stats_layout.addWidget(label)

        main_layout.addWidget(stats_frame)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #B0BEC5;
                background: white;
                border-radius: 10px;
            }
            QTabBar::tab {
                background: #CFD8DC;
                color: #37474F;
                padding: 10px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #1976D2;
                color: white;
            }
        """)

        self.display_table_view = QTableView()
        self.display_table_view.setAlternatingRowColors(True)
        self.display_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                alternate-background-color: #F5F5F5;
                gridline-color: #B0BEC5;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #263238;
                color: white;
                padding: 6px;
                border: 1px solid #455A64;
                font-weight: bold;
            }
        """)
        self.display_tab = self.create_table_page(self.display_table_view)
        self.tabs.addTab(self.display_tab, "Display")

        xy_toolbar = QFrame()
        xy_toolbar.setStyleSheet("""
            QFrame {
                background-color: #F3E5F5;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        xy_toolbar_layout = QHBoxLayout(xy_toolbar)

        xy_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.xy_parameter_combo = QComboBox()
        self.xy_parameter_combo.addItems(XY_PARAMETERS)
        self.xy_parameter_combo.setCurrentText("S22")
        self.xy_parameter_combo.currentTextChanged.connect(self.refresh_xy_table)
        xy_toolbar_layout.addWidget(self.xy_parameter_combo)

        xy_toolbar_layout.addWidget(QLabel("This tab shows the converted grid as a matrix."))
        self.xy_cell_label = QLabel("Click a cell to see the value here.")
        self.xy_cell_label.setStyleSheet("""
            QLabel {
                color: #4A148C;
                background-color: #FFF8E1;
                border: 1px solid #FFB300;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        xy_toolbar_layout.addWidget(self.xy_cell_label, stretch=1)
        xy_toolbar_layout.addStretch(1)

        self.xy_table_view = QTableView()
        self.xy_table_view.setAlternatingRowColors(False)
        self.xy_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #5E35B1;
                color: white;
                padding: 4px;
                border: 1px solid #7E57C2;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.xy_table_view)
        self.xy_tab = self.create_table_page(self.xy_table_view, xy_toolbar)
        self.tabs.addTab(self.xy_tab, "X-Y Table")

        phase_toolbar = QFrame()
        phase_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        phase_toolbar_layout = QHBoxLayout(phase_toolbar)

        phase_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.phase_parameter_combo = QComboBox()
        self.phase_parameter_combo.addItems(XY_PARAMETERS)
        self.phase_parameter_combo.setCurrentText("S22")
        self.phase_parameter_combo.currentTextChanged.connect(self.refresh_phase_table)
        phase_toolbar_layout.addWidget(self.phase_parameter_combo)
        phase_toolbar_layout.addWidget(QLabel("Rotation is controlled on the Smith Chart tab."))
        self.phase_cell_label = QLabel("Click a cell to see the value here.")
        self.phase_cell_label.setStyleSheet("""
            QLabel {
                color: #0D47A1;
                background-color: #E8F4FD;
                border: 1px solid #90CAF9;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        phase_toolbar_layout.addWidget(self.phase_cell_label, stretch=1)
        phase_toolbar_layout.addStretch(1)

        self.phase_table_view = QTableView()
        self.phase_table_view.setAlternatingRowColors(False)
        self.phase_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1565C0;
                color: white;
                padding: 4px;
                border: 1px solid #1E88E5;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.phase_table_view)
        self.phase_tab = self.create_table_page(self.phase_table_view, phase_toolbar)
        self.tabs.addTab(self.phase_tab, "Phase Magnitude")

        contour_toolbar = QFrame()
        contour_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        contour_toolbar_layout = QHBoxLayout(contour_toolbar)

        contour_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.contour_parameter_combo = QComboBox()
        self.contour_parameter_combo.addItems(XY_PARAMETERS)
        self.contour_parameter_combo.setCurrentText("S22")
        self.contour_parameter_combo.currentTextChanged.connect(self.refresh_contour_table)
        contour_toolbar_layout.addWidget(self.contour_parameter_combo)

        contour_toolbar_layout.addWidget(QLabel("This tab keeps only the contour edge data."))
        self.contour_cell_label = QLabel("Click a cell to see the value here.")
        self.contour_cell_label.setStyleSheet("""
            QLabel {
                color: #1B5E20;
                background-color: #E8F5E9;
                border: 1px solid #A5D6A7;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        contour_toolbar_layout.addWidget(self.contour_cell_label, stretch=1)
        contour_toolbar_layout.addStretch(1)

        self.contour_table_view = QTableView()
        self.contour_table_view.setAlternatingRowColors(False)
        self.contour_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2E7D32;
                color: white;
                padding: 4px;
                border: 1px solid #43A047;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.contour_table_view)
        self.contour_tab = self.create_table_page(self.contour_table_view, contour_toolbar)
        self.tabs.addTab(self.contour_tab, "Contour")

        impedance_toolbar = QFrame()
        impedance_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        impedance_toolbar_layout = QHBoxLayout(impedance_toolbar)

        impedance_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.impedance_parameter_combo = QComboBox()
        self.impedance_parameter_combo.addItems(IMPEDANCE_PARAMETERS)
        self.impedance_parameter_combo.setCurrentText("S22")
        self.impedance_parameter_combo.currentTextChanged.connect(self.refresh_impedance_table)
        impedance_toolbar_layout.addWidget(self.impedance_parameter_combo)

        impedance_toolbar_layout.addWidget(QLabel("Z*out = 50Ω × (1+Γ)/(1−Γ), Γ = reflection coefficient"))
        self.impedance_cell_label = QLabel("Click a cell to see the value here.")
        self.impedance_cell_label.setStyleSheet("""
            QLabel {
                color: #1B5E20;
                background-color: #F1F8E9;
                border: 1px solid #558B2F;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        impedance_toolbar_layout.addWidget(self.impedance_cell_label, stretch=1)
        impedance_toolbar_layout.addStretch(1)

        self.impedance_table_view = QTableView()
        self.impedance_table_view.setAlternatingRowColors(False)
        self.impedance_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2E7D32;
                color: white;
                padding: 4px;
                border: 1px solid #388E3C;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.impedance_table_view)
        self.impedance_tab = self.create_table_page(self.impedance_table_view, impedance_toolbar)
        self.tabs.addTab(self.impedance_tab, "Z*out")

        zl_toolbar = QFrame()
        zl_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        zl_toolbar_layout = QHBoxLayout(zl_toolbar)
        zl_toolbar_layout.addWidget(QLabel("ZL,Γin=0 = -Z12·Z21/(50Ω - Z11) - Z22"))
        self.zl_cell_label = QLabel("Click a cell to see the value here.")
        self.zl_cell_label.setStyleSheet("""
            QLabel {
                color: #1B5E20;
                background-color: #F1F8E9;
                border: 1px solid #558B2F;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        zl_toolbar_layout.addWidget(self.zl_cell_label, stretch=1)
        zl_toolbar_layout.addStretch(1)

        self.zl_table_view = QTableView()
        self.zl_table_view.setAlternatingRowColors(False)
        self.zl_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2E7D32;
                color: white;
                padding: 4px;
                border: 1px solid #388E3C;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.zl_table_view)
        self.zl_table_page = self.create_table_page(self.zl_table_view, zl_toolbar)
        self.tabs.addTab(self.zl_table_page, "ZL,Γin=0")

        zpar_toolbar = QFrame()
        zpar_toolbar.setStyleSheet("""
            QFrame {
                background-color: #ECEFF1;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        zpar_toolbar_layout = QHBoxLayout(zpar_toolbar)

        zpar_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.zpar_parameter_combo = QComboBox()
        self.zpar_parameter_combo.addItems(ZPAR_PARAMETERS)
        self.zpar_parameter_combo.setCurrentText("Z22")
        self.zpar_parameter_combo.currentTextChanged.connect(self.refresh_zpar_table)
        zpar_toolbar_layout.addWidget(self.zpar_parameter_combo)

        zpar_toolbar_layout.addWidget(QLabel("S-parameters are converted to Z-parameters for later efficiency work."))
        self.zpar_cell_label = QLabel("Click a cell to see the value here.")
        self.zpar_cell_label.setStyleSheet("""
            QLabel {
                color: #37474F;
                background-color: #ECEFF1;
                border: 1px solid #90A4AE;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        zpar_toolbar_layout.addWidget(self.zpar_cell_label, stretch=1)
        zpar_toolbar_layout.addStretch(1)

        self.zpar_table_view = QTableView()
        self.zpar_table_view.setAlternatingRowColors(False)
        self.zpar_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #546E7A;
                color: white;
                padding: 4px;
                border: 1px solid #78909C;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.zpar_table_view)
        self.zpar_table_page = self.create_table_page(self.zpar_table_view, zpar_toolbar)
        self.tabs.addTab(self.zpar_table_page, "Zpar")

        abcd_toolbar = QFrame()
        abcd_toolbar.setStyleSheet("""
            QFrame {
                background-color: #EDE7F6;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        abcd_toolbar_layout = QHBoxLayout(abcd_toolbar)

        abcd_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.abcd_parameter_combo = QComboBox()
        self.abcd_parameter_combo.addItems(ABCD_PARAMETERS)
        self.abcd_parameter_combo.setCurrentText("A")
        self.abcd_parameter_combo.currentTextChanged.connect(self.refresh_abcd_table)
        abcd_toolbar_layout.addWidget(self.abcd_parameter_combo)

        abcd_toolbar_layout.addWidget(QLabel("Z-parameters are converted to ABCD matrix [V1 I1]T = [A B; C D][V2 -I2]T."))
        self.abcd_cell_label = QLabel("Click a cell to see the value here.")
        self.abcd_cell_label.setStyleSheet("""
            QLabel {
                color: #4527A0;
                background-color: #EDE7F6;
                border: 1px solid #9575CD;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        abcd_toolbar_layout.addWidget(self.abcd_cell_label, stretch=1)
        abcd_toolbar_layout.addStretch(1)

        self.abcd_table_view = QTableView()
        self.abcd_table_view.setAlternatingRowColors(False)
        self.abcd_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #673AB7;
                color: white;
                padding: 4px;
                border: 1px solid #9575CD;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.abcd_table_view)
        self.abcd_table_page = self.create_table_page(self.abcd_table_view, abcd_toolbar)
        self.tabs.addTab(self.abcd_table_page, "ABCD Matrix")

        dz_toolbar = QFrame()
        dz_toolbar.setStyleSheet("""
            QFrame {
                background-color: #FFF8E1;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        dz_toolbar_layout = QHBoxLayout(dz_toolbar)

        dz_toolbar_layout.addWidget(QLabel("Mode:"))
        self.dz_parameter_combo = QComboBox()
        self.dz_parameter_combo.addItems(["S22 horizontal", "S22 vertical"])
        self.dz_parameter_combo.setCurrentText("S22 horizontal")
        self.dz_parameter_combo.currentTextChanged.connect(self.refresh_dz_table)
        dz_toolbar_layout.addWidget(self.dz_parameter_combo)

        dz_toolbar_layout.addWidget(QLabel("Delta impedance uses S22 only."))
        self.dz_cell_label = QLabel("Click a cell to see the value here.")
        self.dz_cell_label.setStyleSheet("""
            QLabel {
                color: #6D4C41;
                background-color: #FFFDE7;
                border: 1px solid #FFB300;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        dz_toolbar_layout.addWidget(self.dz_cell_label, stretch=1)
        dz_toolbar_layout.addStretch(1)

        self.dz_table_view = QTableView()
        self.dz_table_view.setAlternatingRowColors(False)
        self.dz_table_view.setMinimumHeight(240)
        self.dz_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #EF6C00;
                color: white;
                padding: 4px;
                border: 1px solid #FB8C00;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.dz_table_view)
        self.dz_table_page = self.create_table_page(self.dz_table_view, dz_toolbar)

        dz_plot_frame = QFrame()
        dz_plot_frame.setStyleSheet("""
            QFrame {
                background-color: #FFF3E0;
                border: 1px solid #FFCC80;
                border-radius: 10px;
            }
        """)
        dz_plot_layout = QVBoxLayout(dz_plot_frame)
        dz_plot_layout.setContentsMargins(12, 12, 12, 12)

        dz_plot_controls = QHBoxLayout()
        dz_plot_controls.addWidget(QLabel("Good |ΔZ| ≤"))
        self.dz_good_edit = QLineEdit("0.001")
        self.dz_good_edit.setFixedWidth(90)
        self.dz_good_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.dz_good_edit.editingFinished.connect(self._on_dz_threshold_changed)
        dz_plot_controls.addWidget(self.dz_good_edit)
        dz_plot_controls.addWidget(QLabel("Poor |ΔZ| ≥"))
        self.dz_poor_edit = QLineEdit("1")
        self.dz_poor_edit.setFixedWidth(90)
        self.dz_poor_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.dz_poor_edit.editingFinished.connect(self._on_dz_threshold_changed)
        dz_plot_controls.addWidget(self.dz_poor_edit)

        self.dz_plot_button = QPushButton("Plot")
        self.dz_plot_button.setMinimumHeight(34)
        self.dz_plot_button.setStyleSheet("""
            QPushButton {
                background-color: #EF6C00;
                color: white;
                border-radius: 8px;
                padding: 6px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E65100; }
            QPushButton:pressed { background-color: #BF360C; }
        """)
        self.dz_plot_button.clicked.connect(self.plot_dz_resolution)
        dz_plot_controls.addWidget(self.dz_plot_button)
        dz_plot_controls.addSpacing(16)
        dz_plot_controls.addWidget(QLabel("Heatmap min:"))
        self.dz_heatmap_min_edit = QLineEdit("0.001")
        self.dz_heatmap_min_edit.setFixedWidth(90)
        self.dz_heatmap_min_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        dz_plot_controls.addWidget(self.dz_heatmap_min_edit)
        dz_plot_controls.addWidget(QLabel("Heatmap max:"))
        self.dz_heatmap_max_edit = QLineEdit("1")
        self.dz_heatmap_max_edit.setFixedWidth(90)
        self.dz_heatmap_max_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        dz_plot_controls.addWidget(self.dz_heatmap_max_edit)
        dz_plot_controls.addStretch(1)
        dz_plot_layout.addLayout(dz_plot_controls)

        self.dz_status_label = QLabel("Press Plot to render horizontal and vertical delta-impedance maps.")
        self.dz_status_label.setStyleSheet("font-size: 13px; color: #6D4C41; padding: 4px;")
        dz_plot_layout.addWidget(self.dz_status_label)

        if _MATPLOTLIB_OK:
            self.dz_figure = Figure(figsize=(21, 6))
            self.dz_canvas = FigureCanvas(self.dz_figure)
            self.dz_canvas.setMinimumHeight(320)
            dz_plot_layout.addWidget(self.dz_canvas)
        else:
            dz_plot_layout.addWidget(QLabel("matplotlib is not installed.\nRun: pip install matplotlib"))

        self.dz_tab = QWidget()
        dz_layout = QVBoxLayout(self.dz_tab)
        self.dz_splitter = QSplitter(Qt.Vertical)
        self.dz_splitter.addWidget(self.dz_table_page)
        self.dz_splitter.addWidget(dz_plot_frame)
        self.dz_splitter.setSizes([520, 220])
        dz_layout.addWidget(self.dz_splitter)
        self.tabs.addTab(self.dz_tab, "dZ")

        smith_toolbar = QFrame()
        smith_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        smith_toolbar_layout = QHBoxLayout(smith_toolbar)

        parameter_label = QLabel("Parameter:")
        self.smith_parameter_combo = QComboBox()
        self.smith_parameter_combo.addItems(XY_PARAMETERS)
        self.smith_parameter_combo.setCurrentText("S22")
        self.smith_parameter_combo.currentTextChanged.connect(self.refresh_smith_chart)
        self.smith_hover_label = QLabel("Hover a point to see impedance and C1/C2 position.")
        self.smith_hover_label.setStyleSheet("""
            QLabel {
                color: #263238;
                background-color: #E8F4FD;
                border: 1px solid #90CAF9;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        parameter_layout = QVBoxLayout()
        parameter_row = QHBoxLayout()
        parameter_row.addWidget(parameter_label)
        parameter_row.addWidget(self.smith_parameter_combo)
        parameter_row.addStretch(1)
        parameter_layout.addLayout(parameter_row)
        parameter_layout.addWidget(self.smith_hover_label)
        smith_toolbar_layout.addLayout(parameter_layout)
        button_stack = QVBoxLayout()
        self.smith_conjugate_button = QPushButton("Conjugate")
        self.smith_conjugate_button.setCheckable(True)
        self.smith_conjugate_button.toggled.connect(self.toggle_smith_conjugate)
        button_stack.addWidget(self.smith_conjugate_button)
        self.smith_save_image_button = QPushButton("Save Image")
        self.smith_save_image_button.setMinimumWidth(90)
        self.smith_save_image_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.smith_save_image_button.clicked.connect(self._save_smith_chart_image)
        button_stack.addWidget(self.smith_save_image_button)
        self.smith_zoom_in_button = QPushButton("Zoom In")
        self.smith_zoom_in_button.setCheckable(True)
        self.smith_zoom_in_button.setToolTip("Enable drag-zoom selection and open a new 600x400 Smith chart window.")
        self.smith_zoom_in_button.clicked.connect(self._toggle_smith_zoom_in)
        button_stack.addWidget(self.smith_zoom_in_button)
        rotation_row = QHBoxLayout()
        rotation_row.addWidget(QLabel("Rotation:"))
        self.phase_rotation_spin = QSpinBox()
        self.phase_rotation_spin.setRange(0, 360)
        self.phase_rotation_spin.setSuffix("°")
        self.phase_rotation_spin.setValue(0)
        self.phase_rotation_spin.valueChanged.connect(self._on_phase_rotation_changed)
        rotation_row.addWidget(self.phase_rotation_spin)
        rotation_row.addStretch(1)
        button_stack.addLayout(rotation_row)
        button_stack.addStretch(1)
        smith_toolbar_layout.addLayout(button_stack)
        smith_toolbar_layout.addWidget(QLabel("Plot X-Y table values on a Smith chart."))
        self.smith_status_label = QLabel("Select data and press Convert.")
        self.smith_status_label.setStyleSheet("""
            QLabel {
                color: #0D47A1;
                background-color: #E8F4FD;
                border: 1px solid #90CAF9;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        smith_toolbar_layout.addWidget(self.smith_status_label, stretch=1)
        smith_toolbar_layout.addStretch(1)

        smith_mode_frame = QFrame()
        smith_mode_frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #CFD8DC;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        smith_mode_layout = QHBoxLayout(smith_mode_frame)
        self.smith_mode_group = QButtonGroup(self)
        self.smith_mode_xy_radio = QRadioButton("X-Y Table")
        self.smith_mode_dz_radio = QRadioButton("dZ")
        self.smith_mode_dgamma_radio = QRadioButton("dΓ")
        self.smith_mode_efficiency_radio = QRadioButton("Efficiency")
        self.smith_mode_contour_radio = QRadioButton("Contour")
        self.smith_mode_pm_radio = QRadioButton("P/M")

        for mode, radio_button in (
            ("xy", self.smith_mode_xy_radio),
            ("dz", self.smith_mode_dz_radio),
            ("dgamma", self.smith_mode_dgamma_radio),
            ("efficiency", self.smith_mode_efficiency_radio),
            ("contour", self.smith_mode_contour_radio),
            ("pm", self.smith_mode_pm_radio),
        ):
            radio_button.setStyleSheet("QRadioButton { color: #D32F2F; font-size: 14px; }")
            self.smith_mode_group.addButton(radio_button)
            radio_button.toggled.connect(lambda checked, selected_mode=mode: self._on_smith_mode_changed(selected_mode, checked))
            smith_mode_layout.addWidget(radio_button)

        self.smith_mode_efficiency_radio.setChecked(True)
        smith_mode_layout.addStretch(1)

        smith_tools_frame = QFrame()
        smith_tools_frame.setStyleSheet("""
            QFrame {
                background-color: #F7FBFF;
                border: 1px solid #C8E6FF;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        smith_tools_layout = QHBoxLayout(smith_tools_frame)

        manual_frame = QFrame()
        manual_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        manual_layout = QVBoxLayout(manual_frame)
        manual_layout.setContentsMargins(6, 4, 6, 4)
        manual_layout.setSpacing(4)
        manual_title = QLabel("Manual impedance points (R/X in ohms)")
        manual_title.setMinimumHeight(48)
        manual_title.setMaximumHeight(54)
        manual_title.setWordWrap(True)
        manual_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0D47A1;")
        manual_layout.addWidget(manual_title)
        self.manual_impedance_model = ManualImpedanceTableModel(5)
        self.manual_impedance_table_view = QTableView()
        self.manual_impedance_table_view.setModel(self.manual_impedance_model)
        self.manual_impedance_table_view.setMinimumWidth(180)
        self.manual_impedance_table_view.setMaximumWidth(240)
        self.manual_impedance_table_view.setFixedHeight(176)
        self.manual_impedance_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.manual_impedance_table_view.horizontalHeader().setMinimumHeight(34)
        self.manual_impedance_table_view.horizontalHeader().setStyleSheet("font-size: 13px; font-weight: bold;")
        self.manual_impedance_table_view.verticalHeader().setDefaultSectionSize(24)
        self.manual_impedance_table_view.setColumnWidth(0, 36)
        self.manual_impedance_table_view.setColumnWidth(1, 68)
        self.manual_impedance_table_view.setColumnWidth(2, 68)
        self.manual_impedance_table_view.verticalHeader().setVisible(False)
        self.manual_impedance_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.manual_impedance_table_view.setSelectionMode(QTableView.SingleSelection)
        manual_layout.addWidget(self.manual_impedance_table_view)

        manual_button_row = QHBoxLayout()
        self.manual_plot_button = QPushButton("Plot Points")
        self.manual_plot_button.clicked.connect(self._plot_manual_impedance_points)
        manual_button_row.addWidget(self.manual_plot_button)
        self.manual_add_row_button = QPushButton("Add Row")
        self.manual_add_row_button.clicked.connect(self._add_manual_impedance_row)
        manual_button_row.addWidget(self.manual_add_row_button)
        self.manual_clear_button = QPushButton("Clear")
        self.manual_clear_button.clicked.connect(self._clear_manual_impedance_points)
        manual_button_row.addWidget(self.manual_clear_button)
        self.manual_import_button = QPushButton("Import")
        self.manual_import_button.clicked.connect(self._import_manual_impedance_csv)
        manual_button_row.addWidget(self.manual_import_button)
        manual_button_row.addStretch(1)
        manual_layout.addLayout(manual_button_row)

        self.manual_impedance_status_label = QLabel("Enter R and X, then plot the points on the Smith chart.")
        self.manual_impedance_status_label.setWordWrap(True)
        self.manual_impedance_status_label.setStyleSheet("color: #0D47A1;")
        manual_layout.addWidget(self.manual_impedance_status_label)

        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #BBDEFB;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        search_layout = QVBoxLayout(search_frame)
        search_layout.addWidget(QLabel("Search load impedance by C1% / C2%"))
        search_grid = QGridLayout()
        search_grid.setHorizontalSpacing(10)
        search_grid.setVerticalSpacing(8)
        search_grid.addWidget(QLabel("C1%"), 0, 0)
        self.zl_search_c1_edit = QLineEdit()
        self.zl_search_c1_edit.setFixedWidth(60)
        self.zl_search_c1_edit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        search_grid.addWidget(self.zl_search_c1_edit, 0, 1)
        search_grid.addWidget(QLabel("C2%"), 0, 2)
        self.zl_search_c2_edit = QLineEdit()
        self.zl_search_c2_edit.setFixedWidth(60)
        self.zl_search_c2_edit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        search_grid.addWidget(self.zl_search_c2_edit, 0, 3)
        self.zl_search_button = QPushButton("Search ZL")
        self.zl_search_button.setMinimumWidth(90)
        self.zl_search_button.clicked.connect(self._search_load_impedance)
        search_grid.addWidget(self.zl_search_button, 1, 1, alignment=Qt.AlignLeft)
        self.zl_demo_button = QPushButton("Demo")
        self.zl_demo_button.setMinimumWidth(80)
        self.zl_demo_button.clicked.connect(self._run_smith_demo_points)
        search_grid.addWidget(self.zl_demo_button, 1, 2, alignment=Qt.AlignLeft)
        self.manual_carry_button = QPushButton("Carry Over")
        self.manual_carry_button.setMinimumWidth(90)
        self.manual_carry_button.clicked.connect(self._carry_over_search_result)
        search_grid.addWidget(self.manual_carry_button, 1, 3, alignment=Qt.AlignLeft)
        search_layout.addLayout(search_grid)
        self.zl_search_result_label = QLabel("ZL search result will appear here.")
        self.zl_search_result_label.setWordWrap(True)
        self.zl_search_result_label.setStyleSheet("""
            QLabel {
                color: #1B5E20;
                background-color: #E8F5E9;
                border: 1px solid #A5D6A7;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        search_layout.addWidget(self.zl_search_result_label)

        manual_frame.setMaximumWidth(360)
        search_frame.setMaximumWidth(340)
        smith_tools_stack = QWidget()
        smith_tools_stack_layout = QVBoxLayout(smith_tools_stack)
        smith_tools_stack_layout.setContentsMargins(0, 0, 0, 0)
        smith_tools_stack_layout.setSpacing(8)
        smith_tools_stack_layout.addWidget(manual_frame)
        smith_tools_stack_layout.addWidget(search_frame)
        smith_tools_stack_layout.addStretch(1)
        smith_tools_layout.addWidget(smith_tools_stack)

        self.smith_tab = QWidget()
        smith_layout = QVBoxLayout(self.smith_tab)

        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.addWidget(smith_toolbar)
        left_panel_layout.addWidget(smith_mode_frame)
        left_panel_layout.addWidget(smith_tools_frame)
        left_panel_layout.addStretch(1)

        self.smith_left_scroll = QScrollArea()
        self.smith_left_scroll.setWidgetResizable(True)
        self.smith_left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.smith_left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.smith_left_scroll.setWidget(left_panel)
        self.smith_left_scroll.setMaximumWidth(720)

        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)

        if _MATPLOTLIB_OK:
            self.smith_figure = Figure(figsize=(8, 8))
            self.smith_canvas = FigureCanvas(self.smith_figure)
            self.smith_canvas.setMinimumSize(780, 780)
            self.smith_canvas.mpl_connect("button_press_event", self._on_smith_mouse_press)
            self.smith_canvas.mpl_connect("motion_notify_event", self._on_smith_hover)
            self.smith_canvas.mpl_connect("button_release_event", self._on_smith_mouse_release)
            right_panel_layout.addWidget(self.smith_canvas)
        else:
            right_panel_layout.addWidget(QLabel("matplotlib is not installed.\nRun: pip install matplotlib"))
        right_panel_layout.addStretch(1)

        self.smith_chart_scroll = QScrollArea()
        self.smith_chart_scroll.setWidgetResizable(False)
        self.smith_chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.smith_chart_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.smith_chart_scroll.setWidget(right_panel)

        smith_splitter = QSplitter(Qt.Horizontal)
        smith_splitter.addWidget(self.smith_left_scroll)
        smith_splitter.addWidget(self.smith_chart_scroll)
        smith_splitter.setHandleWidth(10)
        smith_splitter.setStretchFactor(0, 0)
        smith_splitter.setStretchFactor(1, 1)
        smith_splitter.setSizes([520, 900])
        smith_splitter.setCollapsible(0, False)
        smith_splitter.setCollapsible(1, False)
        smith_layout.addWidget(smith_splitter, stretch=1)

        self.smith_conjugate_button.setChecked(True)

        self.tabs.addTab(self.smith_tab, "Smith Chart")

        self.component_tab = self._build_component_tab()

        reflection_toolbar = QFrame()
        reflection_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E0F7FA;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        reflection_toolbar_layout = QHBoxLayout(reflection_toolbar)

        reflection_toolbar_layout.addWidget(QLabel("Parameter:"))
        self.reflection_parameter_combo = QComboBox()
        self.reflection_parameter_combo.addItems(XY_PARAMETERS)
        self.reflection_parameter_combo.setCurrentText("S22")
        self.reflection_parameter_combo.currentTextChanged.connect(self.refresh_reflection_table)
        reflection_toolbar_layout.addWidget(self.reflection_parameter_combo)

        reflection_toolbar_layout.addWidget(QLabel("Reflect coefficient resolution: cell[n] = value[n] - value[n-1]. Both horizontal (ΔC1) and vertical (ΔC2) maps shown."))
        self.reflection_cell_label = QLabel("Click a cell to see the value here.")
        self.reflection_cell_label.setStyleSheet("""
            QLabel {
                color: #006064;
                background-color: #E0F2F1;
                border: 1px solid #26A69A;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        reflection_toolbar_layout.addWidget(self.reflection_cell_label, stretch=1)
        reflection_toolbar_layout.addStretch(1)

        self.reflection_table_view = QTableView()
        self.reflection_table_view.setAlternatingRowColors(False)
        self.reflection_table_view.setMinimumHeight(240)
        self.reflection_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #00838F;
                color: white;
                padding: 4px;
                border: 1px solid #0097A7;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.reflection_table_view)
        self.reflection_table_page = self.create_table_page(self.reflection_table_view, reflection_toolbar)

        reflection_plot_frame = QFrame()
        reflection_plot_frame.setStyleSheet("""
            QFrame {
                background-color: #E0F7FA;
                border: 1px solid #80DEEA;
                border-radius: 10px;
            }
        """)
        reflection_plot_layout = QVBoxLayout(reflection_plot_frame)
        reflection_plot_layout.setContentsMargins(12, 12, 12, 12)

        reflection_plot_controls = QHBoxLayout()
        reflection_plot_controls.addWidget(QLabel("Good |ΔΓ| ≤"))
        self.reflection_good_edit = QLineEdit("0")
        self.reflection_good_edit.setFixedWidth(90)
        self.reflection_good_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.reflection_good_edit.editingFinished.connect(self._on_reflection_threshold_changed)
        reflection_plot_controls.addWidget(self.reflection_good_edit)
        reflection_plot_controls.addWidget(QLabel("Poor |ΔΓ| ≥"))
        self.reflection_poor_edit = QLineEdit("0.03")
        self.reflection_poor_edit.setFixedWidth(90)
        self.reflection_poor_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.reflection_poor_edit.editingFinished.connect(self._on_reflection_threshold_changed)
        reflection_plot_controls.addWidget(self.reflection_poor_edit)

        self.reflection_plot_button = QPushButton("Plot")
        self.reflection_plot_button.setMinimumHeight(34)
        self.reflection_plot_button.setStyleSheet("""
            QPushButton {
                background-color: #00838F;
                color: white;
                border-radius: 8px;
                padding: 6px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #006064; }
            QPushButton:pressed { background-color: #004D40; }
        """)
        self.reflection_plot_button.clicked.connect(self.plot_reflection_resolution)
        reflection_plot_controls.addWidget(self.reflection_plot_button)
        reflection_plot_controls.addSpacing(16)
        reflection_plot_controls.addWidget(QLabel("Heatmap min:"))
        self.reflection_heatmap_min_edit = QLineEdit("0")
        self.reflection_heatmap_min_edit.setFixedWidth(90)
        self.reflection_heatmap_min_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        reflection_plot_controls.addWidget(self.reflection_heatmap_min_edit)
        reflection_plot_controls.addWidget(QLabel("Heatmap max:"))
        self.reflection_heatmap_max_edit = QLineEdit("0.03")
        self.reflection_heatmap_max_edit.setFixedWidth(90)
        self.reflection_heatmap_max_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        reflection_plot_controls.addWidget(self.reflection_heatmap_max_edit)
        reflection_plot_controls.addStretch(1)
        reflection_plot_layout.addLayout(reflection_plot_controls)

        self.reflection_status_label = QLabel("Press Plot to render delta reflect-coefficient map.")
        self.reflection_status_label.setStyleSheet("font-size: 13px; color: #006064; padding: 4px;")
        reflection_plot_layout.addWidget(self.reflection_status_label)

        if _MATPLOTLIB_OK:
            self.reflection_figure = Figure(figsize=(21, 6))
            self.reflection_canvas = FigureCanvas(self.reflection_figure)
            self.reflection_canvas.setMinimumHeight(320)
            reflection_plot_layout.addWidget(self.reflection_canvas)
        else:
            reflection_plot_layout.addWidget(QLabel("matplotlib is not installed.\nRun: pip install matplotlib"))

        self.reflection_tab = QWidget()
        reflection_layout = QVBoxLayout(self.reflection_tab)
        self.reflection_splitter = QSplitter(Qt.Vertical)
        self.reflection_splitter.addWidget(self.reflection_table_page)
        self.reflection_splitter.addWidget(reflection_plot_frame)
        self.reflection_splitter.setSizes([520, 220])
        reflection_layout.addWidget(self.reflection_splitter)

        efficiency_toolbar = QFrame()
        efficiency_toolbar.setStyleSheet("""
            QFrame {
                background-color: #FCE4EC;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        efficiency_toolbar_layout = QHBoxLayout(efficiency_toolbar)

        efficiency_toolbar_layout.addWidget(QLabel("Formula:"))
        self.efficiency_mode_combo = QComboBox()
        self.efficiency_mode_combo.addItem("ηZ = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}", "z_single")
        self.efficiency_mode_combo.addItem("ηZL,Γin=0 = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}", "zl_gin0")
        self.efficiency_mode_combo.addItem("ηABCD = PL / Pin", "abcd_power")
        self.efficiency_mode_combo.addItem("|S21|²·(1−|S22|²) / |1−S22²|²", "h_squared")
        self.efficiency_mode_combo.addItem("|S21|²", "s21_squared")
        self.efficiency_mode_combo.addItem("ηoverall = (1 - |S11|²) × |S21|²", "overall")
        self.efficiency_mode_combo.setCurrentIndex(1)
        self.efficiency_mode_combo.currentTextChanged.connect(lambda *_: self.refresh_efficiency_table())
        efficiency_toolbar_layout.addWidget(self.efficiency_mode_combo)
        efficiency_toolbar_layout.addWidget(QLabel("Power transmission efficiency table"))
        self.efficiency_cell_label = QLabel("Click a cell to see the value here.")
        self.efficiency_cell_label.setStyleSheet("""
            QLabel {
                color: #880E4F;
                background-color: #F8BBD0;
                border: 1px solid #E91E63;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        efficiency_toolbar_layout.addWidget(self.efficiency_cell_label, stretch=1)
        efficiency_toolbar_layout.addStretch(1)

        self.efficiency_table_view = QTableView()
        self.efficiency_table_view.setAlternatingRowColors(False)
        self.efficiency_table_view.setMinimumHeight(240)
        self.efficiency_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #90A4AE;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #C2185B;
                color: white;
                padding: 4px;
                border: 1px solid #E91E63;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.efficiency_table_view)
        self.efficiency_table_page = self.create_table_page(self.efficiency_table_view, efficiency_toolbar)

        efficiency_plot_frame = QFrame()
        efficiency_plot_frame.setStyleSheet("""
            QFrame {
                background-color: #FCE4EC;
                border: 1px solid #F8BBD0;
                border-radius: 10px;
            }
        """)
        efficiency_plot_layout = QVBoxLayout(efficiency_plot_frame)
        efficiency_plot_layout.setContentsMargins(12, 12, 12, 12)

        efficiency_plot_controls = QHBoxLayout()
        efficiency_plot_controls.addWidget(QLabel("Good η ≥"))
        self.efficiency_good_edit = QLineEdit("100")
        self.efficiency_good_edit.setFixedWidth(80)
        self.efficiency_good_edit.setValidator(QDoubleValidator(0.0, 100.0, 1))
        self.efficiency_good_edit.editingFinished.connect(self._on_efficiency_threshold_changed)
        efficiency_plot_controls.addWidget(self.efficiency_good_edit)
        efficiency_plot_controls.addWidget(QLabel("%"))
        
        efficiency_plot_controls.addWidget(QLabel("  Poor η ≤"))
        self.efficiency_poor_edit = QLineEdit("10")
        self.efficiency_poor_edit.setFixedWidth(80)
        self.efficiency_poor_edit.setValidator(QDoubleValidator(0.0, 100.0, 1))
        self.efficiency_poor_edit.editingFinished.connect(self._on_efficiency_threshold_changed)
        efficiency_plot_controls.addWidget(self.efficiency_poor_edit)
        efficiency_plot_controls.addWidget(QLabel("%"))
        
        efficiency_plot_controls.addStretch(1)
        efficiency_plot_layout.addLayout(efficiency_plot_controls)

        self.efficiency_status_label = QLabel("Set efficiency thresholds for Smith Chart coloring.")
        self.efficiency_status_label.setStyleSheet("font-size: 13px; color: #880E4F; padding: 4px;")
        efficiency_plot_layout.addWidget(self.efficiency_status_label)

        self.efficiency_tab = QWidget()
        efficiency_layout = QVBoxLayout(self.efficiency_tab)
        self.efficiency_splitter = QSplitter(Qt.Vertical)
        self.efficiency_splitter.addWidget(self.efficiency_table_page)
        self.efficiency_splitter.addWidget(efficiency_plot_frame)
        self.efficiency_splitter.setSizes([520, 220])
        efficiency_layout.addWidget(self.efficiency_splitter)

        iout_toolbar = QFrame()
        iout_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E8EAF6;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        iout_toolbar_layout = QHBoxLayout(iout_toolbar)
        iout_toolbar_layout.addWidget(QLabel("Iout formula:"))
        self.iout_formula_combo = QComboBox()
        self.iout_formula_combo.addItem("Formula 1: Iout = -C·V1 + A·I1", "abcd")
        self.iout_formula_combo.addItem("Formula 2: Iout = Z21·V1 / DZ", "z_formula")
        self.iout_formula_combo.addItem("Formula 3: Iout = (Z21 / (Z11 + Z22)) × I1", "z_formula3")
        self.iout_formula_combo.addItem("Formula 4: Iout = (Z11·I1 - V1) / Z12", "z_formula4")
        self.iout_formula_combo.setCurrentIndex(1)
        self.iout_formula_combo.currentTextChanged.connect(self.refresh_iout_table)
        iout_toolbar_layout.addWidget(self.iout_formula_combo)
        iout_toolbar_layout.addSpacing(16)
        iout_toolbar_layout.addWidget(QLabel("Input power (W):"))
        self.iout_power_edit = QLineEdit("100")
        self.iout_power_edit.setFixedWidth(90)
        self.iout_power_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.iout_power_edit.editingFinished.connect(self.refresh_iout_table)
        iout_toolbar_layout.addWidget(self.iout_power_edit)
        iout_toolbar_layout.addWidget(QLabel("Input impedance: 50Ω"))
        self.iout_cell_label = QLabel("Click a cell to see the value here.")
        self.iout_cell_label.setStyleSheet("""
            QLabel {
                color: #1A237E;
                background-color: #C5CAE9;
                border: 1px solid #5C6BC0;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        iout_toolbar_layout.addWidget(self.iout_cell_label, stretch=1)
        iout_toolbar_layout.addStretch(1)

        self.iout_table_view = QTableView()
        self.iout_table_view.setAlternatingRowColors(False)
        self.iout_table_view.setMinimumHeight(240)
        self.iout_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #9FA8DA;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #3949AB;
                color: white;
                padding: 4px;
                border: 1px solid #5C6BC0;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.iout_table_view)
        self.iout_table_page = self.create_table_page(self.iout_table_view, iout_toolbar)
        self.iout_tab = QWidget()
        iout_layout = QVBoxLayout(self.iout_tab)
        
        if _MATPLOTLIB_OK:
           iout_splitter = QSplitter(Qt.Horizontal)
           iout_splitter.addWidget(self.iout_table_page)
           iout_splitter.addWidget(self.iout_heatmap_canvas)
           iout_splitter.setSizes([800, 200])
           iout_layout.addWidget(iout_splitter)
        else:
           iout_layout.addWidget(self.iout_table_page)

        vpp_toolbar = QFrame()
        vpp_toolbar.setStyleSheet("""
            QFrame {
                background-color: #E0F2F1;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        vpp_toolbar_layout = QHBoxLayout(vpp_toolbar)
        vpp_toolbar_layout.addWidget(QLabel("Vpp formula: Vpp = 2√2·Vrms, Vrms = ZL·Z21·V1 / DZ"))
        vpp_toolbar_layout.addSpacing(16)
        vpp_toolbar_layout.addWidget(QLabel("Input power (W):"))
        self.vpp_power_edit = QLineEdit("100")
        self.vpp_power_edit.setFixedWidth(90)
        self.vpp_power_edit.setValidator(QDoubleValidator(0.0, 1e12, 6))
        self.vpp_power_edit.editingFinished.connect(self.refresh_vpp_table)
        vpp_toolbar_layout.addWidget(self.vpp_power_edit)
        vpp_toolbar_layout.addWidget(QLabel("Input impedance: 50Ω"))
        self.vpp_cell_label = QLabel("Click a cell to see the value here.")
        self.vpp_cell_label.setStyleSheet("""
            QLabel {
                color: #004D40;
                background-color: #B2DFDB;
                border: 1px solid #26A69A;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: bold;
            }
        """)
        vpp_toolbar_layout.addWidget(self.vpp_cell_label, stretch=1)
        vpp_toolbar_layout.addStretch(1)

        self.vpp_table_view = QTableView()
        self.vpp_table_view.setAlternatingRowColors(False)
        self.vpp_table_view.setMinimumHeight(240)
        self.vpp_table_view.setStyleSheet("""
            QTableView {
                background-color: white;
                gridline-color: #80CBC4;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #00897B;
                color: white;
                padding: 4px;
                border: 1px solid #26A69A;
                font-weight: bold;
            }
        """)
        self._enable_table_hover_highlight(self.vpp_table_view)
        self.vpp_table_page = self.create_table_page(self.vpp_table_view, vpp_toolbar)
        self.vpp_tab = QWidget()
        vpp_layout = QVBoxLayout(self.vpp_tab)
        
        if _MATPLOTLIB_OK:
           vpp_splitter = QSplitter(Qt.Horizontal)
           vpp_splitter.addWidget(self.vpp_table_page)
           vpp_splitter.addWidget(self.vpp_heatmap_canvas)
           vpp_splitter.setSizes([800, 200])
           vpp_layout.addWidget(vpp_splitter)
        else:
           vpp_layout.addWidget(self.vpp_table_page)
        
        phi_out_toolbar = QFrame()
        phi_out_toolbar.setStyleSheet("""
           QFrame {
               background-color: #F3E5F5;
               border-radius: 10px;
               padding: 8px;
           }
        """)
        phi_out_toolbar_layout = QHBoxLayout(phi_out_toolbar)
        phi_out_toolbar_layout.addWidget(QLabel("φ_out formula: φ_out = tan⁻¹(XL/RL)"))
        self.phi_out_cell_label = QLabel("Click a cell to see the value here.")
        self.phi_out_cell_label.setStyleSheet("""
           QLabel {
               color: #4A148C;
               background-color: #E1BEE7;
               border: 1px solid #CE93D8;
               border-radius: 8px;
               padding: 6px 10px;
               font-weight: bold;
           }
        """)
        phi_out_toolbar_layout.addWidget(self.phi_out_cell_label, stretch=1)
        phi_out_toolbar_layout.addStretch(1)

        self.phi_out_table_view = QTableView()
        self.phi_out_table_view.setAlternatingRowColors(False)
        self.phi_out_table_view.setMinimumHeight(240)
        self.phi_out_table_view.setStyleSheet("""
           QTableView {
               background-color: white;
               gridline-color: #F5E1FF;
               font-size: 12px;
           }
           QHeaderView::section {
               background-color: #7B1FA2;
               color: white;
               padding: 4px;
               border: 1px solid #CE93D8;
               font-weight: bold;
           }
        """)
        self._enable_table_hover_highlight(self.phi_out_table_view)
        self.phi_out_table_page = self.create_table_page(self.phi_out_table_view, phi_out_toolbar)
        self.phi_out_tab = QWidget()
        phi_out_layout = QVBoxLayout(self.phi_out_tab)
        
        if _MATPLOTLIB_OK:
           phi_out_splitter = QSplitter(Qt.Horizontal)
           phi_out_splitter.addWidget(self.phi_out_table_page)
           phi_out_splitter.addWidget(self.phi_out_heatmap_canvas)
           phi_out_splitter.setSizes([800, 200])
           phi_out_layout.addWidget(phi_out_splitter)
        else:
           phi_out_layout.addWidget(self.phi_out_table_page)
        
        self.derive_eta_formula_tab = self._build_derive_eta_formula_tab()

        self.tabs.addTab(self.component_tab, "Component")
        self.tabs.addTab(self.reflection_tab, "Reflect Coefficient")
        self.tabs.addTab(self.efficiency_tab, "Efficiency")
        self.tabs.addTab(self.iout_tab, "Iout")
        self.tabs.addTab(self.vpp_tab, "Vpp")
        self.tabs.addTab(self.phi_out_tab, "φ_out")
        self.tabs.addTab(self.derive_eta_formula_tab, "Derive η formula")
        self.tabs.setCurrentWidget(self.smith_tab)
        self._startup_status("Preparing Smith chart and plots...", 75)

        main_layout.addWidget(self.tabs, stretch=1)

        note = QLabel(
           "Note: Display tab shows the converted row table. X-Y Table shows the grid view for the selected S-parameter. Z*out shows the reflection-coefficient impedance Z = 50Ω × (1+Γ)/(1−Γ). ZL,Γin=0 shows ZL = -Z12·Z21/(50Ω - Z11) - Z22. Zpar shows the converted Z-parameters. ABCD Matrix shows the converted ABCD terms. dZ shows delta impedance for S22. Reflect Coefficient tab shows delta-Γ resolution from X-Y data. Efficiency tab provides six formulas with default ηZL,Γin=0 = Re{ZL}|Z21|² / Re{[Z11(ZL+Z22)-Z12Z21](ZL+Z22)*}. Iout tab provides Formulas 1-4 with user-set Pin (default 100W) and Zin = 50Ω. Vpp tab computes Vpp = 2√2·Vrms where Vrms = ZL·Z21·V1 / DZ. φ_out tab shows the phase angle φ_out = tan⁻¹(XL/RL) of the load impedance. Smith Chart defaults to Efficiency mode and supports X-Y Table, dZ, dΓ, Efficiency coloring, Contour, P/M, manual R/X points, ZL search by C1/C2, and one-click demo plotting."
        )
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("font-size: 13px; color: #607D8B; padding: 6px;")
        main_layout.addWidget(note)

        self.setCentralWidget(main_widget)
        self._startup_status("Finalizing window...", 95)

    def build_tab_page(self, title_text, body_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel(title_text)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: white;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5E35B1,
                    stop:1 #039BE5
                );
                padding: 12px;
                border-radius: 12px;
            }
        """)

        body = QLabel(body_text)
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #455A64;
                background-color: white;
                border: 1px dashed #90A4AE;
                border-radius: 12px;
                padding: 18px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(body, stretch=1)
        return page

    # ------------------------------------------------------------------
    # Component tab
    # ------------------------------------------------------------------
    def _build_component_tab(self):
        # Outer page holds only the scroll area so the tab itself never clips content.
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer_layout.addWidget(scroll)

        # Inner widget carries all real content.
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)
        scroll.setWidget(page)

        # ── title ─────────────────────────────────────────────────────
        title = QLabel("Component Analysis — Cap Array Resolution")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 20px; font-weight: bold; color: white;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E7D32, stop:1 #1565C0);
                padding: 10px; border-radius: 10px;
            }
        """)
        root.addWidget(title)

        # ── input form ────────────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FBE7;
                border: 1px solid #C5CAE9;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        form_grid = QGridLayout(form_frame)
        form_grid.setSpacing(6)
        form_grid.setContentsMargins(14, 10, 14, 10)

        label_style = "font-size: 13px;"
        edit_style = """
            QLineEdit {
                background-color: white;
                border: 1px solid #90A4AE;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 13px;
            }
        """

        def _lbl(text):
            w = QLabel(text)
            w.setStyleSheet(label_style)
            return w

        def _edit(default="0"):
            e = QLineEdit(default)
            e.setFixedWidth(90)
            e.setStyleSheet(edit_style)
            v = QDoubleValidator()
            v.setBottom(0.0)
            e.setValidator(v)
            return e

        # Row 0: Frequency
        form_grid.addWidget(_lbl("Frequency"), 0, 0)
        self.comp_freq_edit = _edit("27.12")
        form_grid.addWidget(self.comp_freq_edit, 0, 1)
        form_grid.addWidget(_lbl("MHz"), 0, 2)

        # Row 1: blank spacer row
        form_grid.setRowMinimumHeight(1, 6)

        # Row 2: C1 / C2 section headers
        c1_hdr = QLabel("C1")
        c1_hdr.setStyleSheet("font-weight: bold; font-size: 14px; color: #1565C0;")
        form_grid.addWidget(c1_hdr, 2, 0, 1, 3)

        c2_hdr = QLabel("C2")
        c2_hdr.setStyleSheet("font-weight: bold; font-size: 14px; color: #C62828;")
        form_grid.addWidget(c2_hdr, 2, 4, 1, 3)

        # Spacer column between C1 and C2 blocks
        form_grid.setColumnMinimumWidth(3, 30)

        # Rows 3-9: parameter rows
        # Order: [0]=Coarse, [1]=Fine6, [2]=Fine5, [3]=Fine4, [4]=Fine3, [5]=Fine2, [6]=Fine1
        row_labels   = ["Coarse 1 to 6", "Fine 6", "Fine 5", "Fine 4", "Fine 3", "Fine 2", "Fine 1"]
        c1_defaults  = ["75",  "43",  "34",  "15",  "0.1", "4.7", "2.2"]
        c2_defaults  = ["75",  "75",  "43",  "21",  "15",  "0.1", "4.7"]
        self.c1_edits = []
        self.c2_edits = []
        for idx, lbl_text in enumerate(row_labels):
            r = 3 + idx
            # C1
            form_grid.addWidget(_lbl(lbl_text), r, 0)
            e1 = _edit(c1_defaults[idx])
            form_grid.addWidget(e1, r, 1)
            form_grid.addWidget(_lbl("pF"), r, 2)
            self.c1_edits.append(e1)
            # C2
            form_grid.addWidget(_lbl(lbl_text), r, 4)
            e2 = _edit(c2_defaults[idx])
            form_grid.addWidget(e2, r, 5)
            form_grid.addWidget(_lbl("pF"), r, 6)
            self.c2_edits.append(e2)

        # Row 10: Calculate button
        calc_btn = QPushButton("Calculate")
        calc_btn.setMinimumHeight(36)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32; color: white;
                border-radius: 8px; padding: 6px 28px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover  { background-color: #1B5E20; }
            QPushButton:pressed { background-color: #003300; }
        """)
        calc_btn.clicked.connect(self._on_calculate_component)
        form_grid.addWidget(calc_btn, 10, 0, 1, 7, Qt.AlignCenter)

        root.addWidget(form_frame)

        # ── status label ──────────────────────────────────────────────
        self.comp_status_label = QLabel("Enter cap values and press Calculate.")
        self.comp_status_label.setAlignment(Qt.AlignCenter)
        self.comp_status_label.setStyleSheet(
            "font-size: 13px; color: #37474F; padding: 4px;"
        )
        root.addWidget(self.comp_status_label)

        # ── plot canvas ───────────────────────────────────────────────
        if _MATPLOTLIB_OK:
            self.comp_figure = Figure(figsize=(14, 7))
            self.comp_canvas = FigureCanvas(self.comp_figure)
            self.comp_canvas.setMinimumHeight(500)
            root.addWidget(self.comp_canvas)
        else:
            warn = QLabel(
                "matplotlib is not installed.\n"
                "Run: pip install matplotlib"
            )
            warn.setAlignment(Qt.AlignCenter)
            warn.setStyleSheet("color: red; font-size: 14px;")
            root.addWidget(warn)

        if _MATPLOTLIB_OK:
           self.iout_heatmap_figure = Figure(figsize=(5, 6))
           self.iout_heatmap_canvas = FigureCanvas(self.iout_heatmap_figure)
           self.iout_heatmap_canvas.setMinimumWidth(200)
            
           self.vpp_heatmap_figure = Figure(figsize=(5, 6))
           self.vpp_heatmap_canvas = FigureCanvas(self.vpp_heatmap_figure)
           self.vpp_heatmap_canvas.setMinimumWidth(200)
            
           self.phi_out_heatmap_figure = Figure(figsize=(5, 6))
           self.phi_out_heatmap_canvas = FigureCanvas(self.phi_out_heatmap_figure)
           self.phi_out_heatmap_canvas.setMinimumWidth(200)

        root.addStretch(1)
        return outer

    def _on_calculate_component(self):
        if not _MATPLOTLIB_OK:
            QMessageBox.warning(
                self, "Missing Library",
                "matplotlib is required.\nInstall with:  pip install matplotlib"
            )
            return

        try:
            # c1_edits / c2_edits order: [0]=Coarse, [1]=Fine6, [2]=Fine5, ..., [6]=Fine1
            def _read(edits):
                coarse = float(edits[0].text() or "0")
                # fine_caps for calculate_cap_array: [Fine1..Fine6] = indices [6,5,4,3,2,1]
                fine_caps = [float(edits[6 - k].text() or "0") for k in range(6)]
                return coarse, fine_caps

            c1_coarse, c1_fine = _read(self.c1_edits)
            c2_coarse, c2_fine = _read(self.c2_edits)

            C1 = calculate_cap_array(c1_coarse, c1_fine)
            C2 = calculate_cap_array(c2_coarse, c2_fine)

            # Use absolute diff: negative values only appear at coarse-block
            # boundaries (overlapping ranges) and don't represent useful resolution.
            dC1 = np.abs(np.diff(C1))   # 447 values
            dC2 = np.abs(np.diff(C2))

            # Pad to 448 by repeating the last delta
            dC1p = np.append(dC1, dC1[-1] if len(dC1) else 0.0)
            dC2p = np.append(dC2, dC2[-1] if len(dC2) else 0.0)

            positions = np.arange(448)
            all_dc = np.concatenate([dC1, dC2])
            min_dc, avg_dc, max_dc = all_dc.min(), all_dc.mean(), all_dc.max()

            self.comp_status_label.setText(
                f"C1: {C1.min():.4g} ~ {C1.max():.4g} pF  │  "
                f"C2: {C2.min():.4g} ~ {C2.max():.4g} pF  │  "
                f"ΔC → min = {min_dc:.4g} pF,  avg = {avg_dc:.4g} pF,  max = {max_dc:.4g} pF"
            )

            self._draw_component_plots(
                C1, C2, dC1, dC2, dC1p, dC2p,
                positions, min_dc, avg_dc, max_dc
            )

        except Exception as exc:
            QMessageBox.critical(self, "Calculation Error", str(exc))

    def _draw_component_plots(self, C1, C2, dC1, dC2, dC1p, dC2p,
                               positions, min_dc, avg_dc, max_dc):
        self.comp_figure.clear()

        cmap_rygr = _get_cmap("RdYlGn_r")   # green=small ΔC (good), red=large (bad)

        gs = self.comp_figure.add_gridspec(
            2, 2,
            hspace=0.42, wspace=0.32,
            left=0.07, right=0.97, top=0.93, bottom=0.08
        )
        ax1 = self.comp_figure.add_subplot(gs[0, 0])
        ax2 = self.comp_figure.add_subplot(gs[0, 1])
        ax3 = self.comp_figure.add_subplot(gs[1, :])

        # ── Plot 1: Equivalent Capacitance vs Position ────────────────
        ax1.plot(positions, C1, color="#1565C0", linewidth=0.9, label="C1")
        ax1.plot(positions, C2, color="#039BE5", linewidth=0.9,
                 linestyle="--", label="C2")
        ax1.set_xlabel("Position (0 – 447)", fontsize=9)
        ax1.set_ylabel("Capacitance (pF)", fontsize=9)
        ax1.set_title("Equivalent Capacitance vs Position", fontsize=10, fontweight="bold")
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(labelsize=8)

        # ── Plot 2: ΔC vs Position (Green→Yellow→Red) ─────────────────
        dc_pos = np.arange(len(dC1))
        norm = Normalize(vmin=min_dc, vmax=max_dc)
        colors1 = cmap_rygr(norm(dC1))
        colors2 = cmap_rygr(norm(dC2))

        ax2.scatter(dc_pos, dC1, c=colors1, s=5, label="C1", zorder=3)
        ax2.scatter(dc_pos, dC2, c=colors2, s=5, marker="s", label="C2",
                    alpha=0.7, zorder=2)

        mappable = _mpl_cm.ScalarMappable(norm=norm, cmap=cmap_rygr)
        mappable.set_array([])
        self.comp_figure.colorbar(mappable, ax=ax2, label="|ΔC| (pF)", pad=0.02)

        ax2.axhline(min_dc, color="green",  linewidth=0.8, linestyle="--",
                    label=f"min {min_dc:.3g}")
        ax2.axhline(avg_dc, color="orange", linewidth=0.8, linestyle="--",
                    label=f"avg {avg_dc:.3g}")
        ax2.axhline(max_dc, color="red",    linewidth=0.8, linestyle="--",
                    label=f"max {max_dc:.3g}")

        ax2.set_xlabel("Position (0 – 447)", fontsize=9)
        ax2.set_ylabel("ΔC (pF)", fontsize=9)
        ax2.set_title("ΔC vs Position  (resolution)", fontsize=10, fontweight="bold")
        ax2.legend(fontsize=7, ncol=2)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(labelsize=8)

        # ── Plot 3: Heatmap — x=C1 pos, y=C2 pos, color=min(ΔC1,ΔC2) ─
        # At operating point (c1, c2), best achievable ΔC = min of individual deltas
        heatmap = np.minimum(
            dC1p[np.newaxis, :],   # broadcast over C2 axis  → shape (448, 448)
            dC2p[:, np.newaxis]    # broadcast over C1 axis
        )
        im = ax3.imshow(
            heatmap,
            aspect="auto",
            cmap=cmap_rygr,
            origin="lower",
            extent=[0, 448, 0, 448],
            interpolation="nearest",
        )
        self.comp_figure.colorbar(im, ax=ax3, label="min(ΔC1, ΔC2)  (pF)", pad=0.01)
        ax3.set_xlabel("C1 Position (0 – 447)", fontsize=9)
        ax3.set_ylabel("C2 Position (0 – 447)", fontsize=9)
        ax3.set_title(
            "Resolution Heatmap: min(ΔC1, ΔC2) at each operating point  "
            "[green = fine resolution, red = coarse]",
            fontsize=10, fontweight="bold"
        )
        ax3.tick_params(labelsize=8)

        # Coarse-boundary grid lines every 64 positions
        for boundary in range(64, 448, 64):
            ax3.axvline(boundary, color="white", linewidth=0.4, alpha=0.5)
            ax3.axhline(boundary, color="white", linewidth=0.4, alpha=0.5)

        self.comp_canvas.draw()

    def create_table_page(self, table_view, toolbar_widget=None):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        if toolbar_widget is not None:
            layout.addWidget(toolbar_widget)

        layout.addWidget(table_view, stretch=1)
        return page

    def _enable_table_hover_highlight(self, table_view: QTableView):
        table_view.setMouseTracking(True)
        table_view.viewport().setMouseTracking(True)
        hover_rule = "QTableView::item:hover { background-color: #BBDEFB; color: #0D47A1; }"
        style = table_view.styleSheet()
        if hover_rule not in style:
            table_view.setStyleSheet(f"{style}\n{hover_rule}")

    def _build_derive_eta_formula_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Derive η formula")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #37474F;")
        layout.addWidget(title)

        content = QLabel(
            "How to derive simple term of η formula?\n\n"
            "Single Z-Parameter Formula for Match Efficiency\n\n"
            "1. Starting definitions\n"
            "[V1 V2]^T = [[Z11 Z12][Z21 Z22]] [I1 I2]^T\n"
            "Both I1 and I2 flow into the two-port network.\n"
            "Define IL flowing out of Match into load:\n"
            "I2 = -IL,  V2 = ZL*IL\n\n"
            "2. ABCD-based efficiency equation\n"
            "[V1 I1]^T = [[A B][C D]] [V2 IL]^T\n"
            "With V2 = ZL*IL:\n"
            "V1 = (A*ZL + B)*IL\n"
            "I1 = (C*ZL + D)*IL\n"
            "Pin = Re{V1*conj(I1)} = Re{(A*ZL + B)*(C*ZL + D)*}|IL|^2\n"
            "PL = Re{ZL}|IL|^2\n"
            "ηMatch = Re{ZL} / Re{(A*ZL + B)*(C*ZL + D)*}\n\n"
            "3. Substitute Z-parameters into ABCD equation\n"
            "A = Z11/Z21\n"
            "B = (Z11*Z22 - Z12*Z21)/Z21\n"
            "C = 1/Z21\n"
            "D = Z22/Z21\n"
            "Let ΔZ = Z11*Z22 - Z12*Z21\n"
            "Then:\n"
            "A*ZL + B = (Z11*ZL + ΔZ)/Z21\n"
            "C*ZL + D = (ZL + Z22)/Z21\n\n"
            "4. Final single formula\n"
            "ηMatch = Re{ZL}|Z21|^2 / Re{(Z11*ZL + Z11*Z22 - Z12*Z21)*(ZL + Z22)*}\n"
            "Recommended implementation form:\n"
            "ηMatch = Re{ZL}|Z21|^2 / Re{[Z11*(ZL + Z22) - Z12*Z21]*(ZL + Z22)*}\n"
            "ηMatch(%) = 100 * Re{ZL}|Z21|^2 / Re{[Z11*(ZL + Z22) - Z12*Z21]*(ZL + Z22)*}\n\n"
            "5. Physical meaning behind the formula\n"
            "From V2 = Z21*I1 + Z22*I2, with I2 = -IL and V2 = ZL*IL:\n"
            "I1 = (ZL + Z22)/Z21 * IL\n"
            "V1 = Z11*I1 - Z12*IL\n"
            "V1 = [Z11*(ZL + Z22) - Z12*Z21]/Z21 * IL\n"
            "Efficiency follows from ηMatch = Re{V2*conj(IL)} / Re{V1*conj(I1)}."
        )
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setStyleSheet(
            "QLabel { background-color: #FAFAFA; border: 1px solid #CFD8DC; "
            "border-radius: 8px; padding: 12px; font-size: 13px; color: #263238; }"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        return tab

    def _create_frozen_overlay_view(self, parent_view: QTableView) -> QTableView:
        overlay_view = QTableView(parent_view)
        overlay_view.setAlternatingRowColors(False)
        overlay_view.setStyleSheet(parent_view.styleSheet())
        overlay_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        overlay_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        overlay_view.setFocusPolicy(Qt.NoFocus)
        overlay_view.setFrameShape(QFrame.NoFrame)
        overlay_view.horizontalHeader().setVisible(False)
        overlay_view.verticalHeader().setVisible(False)
        overlay_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        overlay_view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        overlay_view.setSelectionBehavior(QTableView.SelectItems)
        overlay_view.setSelectionMode(QTableView.SingleSelection)
        return overlay_view

    def _update_frozen_pane_geometry(self, table_view: QTableView):
        pane = getattr(self, "_freeze_panes", {}).get(table_view)
        if pane is None:
            return

        model = table_view.model()
        if model is None:
            table_view.setViewportMargins(0, 0, 0, 0)
            pane["corner"].hide()
            pane["top"].hide()
            pane["left"].hide()
            return

        freeze_rows = min(pane["freeze_rows"], model.rowCount())
        freeze_cols = min(pane["freeze_cols"], model.columnCount())
        if freeze_rows <= 0 or freeze_cols <= 0:
            table_view.setViewportMargins(0, 0, 0, 0)
            pane["corner"].hide()
            pane["top"].hide()
            pane["left"].hide()
            return

        frozen_width = sum(table_view.columnWidth(col) for col in range(freeze_cols))
        frozen_height = sum(table_view.rowHeight(row) for row in range(freeze_rows))
        table_view.setViewportMargins(frozen_width, frozen_height, 0, 0)

        frame = table_view.frameWidth()
        viewport_width = table_view.viewport().width()
        viewport_height = table_view.viewport().height()

        pane["corner"].setGeometry(frame, frame, frozen_width, frozen_height)
        pane["top"].setGeometry(frame + frozen_width, frame, max(0, viewport_width), frozen_height)
        pane["left"].setGeometry(frame, frame + frozen_height, frozen_width, max(0, viewport_height))

        pane["corner"].show()
        pane["top"].show()
        pane["left"].show()

    def _sync_frozen_pane_sections(self, table_view: QTableView):
        pane = getattr(self, "_freeze_panes", {}).get(table_view)
        if pane is None:
            return
        model = table_view.model()
        if model is None:
            return

        for col in range(model.columnCount()):
            width = table_view.columnWidth(col)
            pane["corner"].setColumnWidth(col, width)
            pane["top"].setColumnWidth(col, width)
            pane["left"].setColumnWidth(col, width)

        for row in range(model.rowCount()):
            height = table_view.rowHeight(row)
            pane["corner"].setRowHeight(row, height)
            pane["top"].setRowHeight(row, height)
            pane["left"].setRowHeight(row, height)

    def _apply_freeze_panes(self, table_view: QTableView, freeze_rows: int = 3, freeze_cols: int = 3):
        if not hasattr(self, "_freeze_panes"):
            self._freeze_panes = {}

        pane = self._freeze_panes.get(table_view)
        if pane is None:
            corner = self._create_frozen_overlay_view(table_view)
            top = self._create_frozen_overlay_view(table_view)
            left = self._create_frozen_overlay_view(table_view)
            pane = {
                "corner": corner,
                "top": top,
                "left": left,
                "freeze_rows": freeze_rows,
                "freeze_cols": freeze_cols,
            }
            self._freeze_panes[table_view] = pane

            table_view.installEventFilter(self)
            table_view.horizontalScrollBar().valueChanged.connect(top.horizontalScrollBar().setValue)
            top.horizontalScrollBar().valueChanged.connect(table_view.horizontalScrollBar().setValue)
            table_view.verticalScrollBar().valueChanged.connect(left.verticalScrollBar().setValue)
            left.verticalScrollBar().valueChanged.connect(table_view.verticalScrollBar().setValue)
            table_view.horizontalHeader().sectionResized.connect(
                lambda *_args, tv=table_view: (self._sync_frozen_pane_sections(tv), self._update_frozen_pane_geometry(tv))
            )
            table_view.verticalHeader().sectionResized.connect(
                lambda *_args, tv=table_view: (self._sync_frozen_pane_sections(tv), self._update_frozen_pane_geometry(tv))
            )

        pane["freeze_rows"] = freeze_rows
        pane["freeze_cols"] = freeze_cols

        model = table_view.model()
        if model is None:
            self._update_frozen_pane_geometry(table_view)
            return

        selection_model = table_view.selectionModel()
        for overlay in (pane["corner"], pane["top"], pane["left"]):
            overlay.setModel(model)
            if selection_model is not None:
                overlay.setSelectionModel(selection_model)

        row_count = model.rowCount()
        col_count = model.columnCount()
        frozen_rows = min(freeze_rows, row_count)
        frozen_cols = min(freeze_cols, col_count)

        for row in range(row_count):
            is_frozen_row = row < frozen_rows
            pane["corner"].setRowHidden(row, not is_frozen_row)
            pane["top"].setRowHidden(row, not is_frozen_row)
            pane["left"].setRowHidden(row, is_frozen_row)

        for col in range(col_count):
            is_frozen_col = col < frozen_cols
            pane["corner"].setColumnHidden(col, not is_frozen_col)
            pane["top"].setColumnHidden(col, is_frozen_col)
            pane["left"].setColumnHidden(col, not is_frozen_col)

        self._sync_frozen_pane_sections(table_view)
        self._update_frozen_pane_geometry(table_view)

    def eventFilter(self, watched, event):
        freeze_panes = getattr(self, "_freeze_panes", {})
        if watched in freeze_panes and event.type() in (QEvent.Resize, QEvent.Show, QEvent.LayoutRequest):
            self._sync_frozen_pane_sections(watched)
            self._update_frozen_pane_geometry(watched)
        return super().eventFilter(watched, event)

    def refresh_display_table(self):
        if self.df_display is None:
            return

        self.display_table_model = PandasTableModel(self.df_display)
        self.display_table_view.setModel(self.display_table_model)
        self.display_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.display_table_view.verticalHeader().setVisible(False)

    def refresh_xy_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_xy_parameter = self.xy_parameter_combo.currentText().strip()
        self.df_xy_display = build_xy_display_table(self.df_all, self.current_xy_parameter)

        self.xy_table_model = PandasTableModel(self.df_xy_display)
        self.xy_table_view.setModel(self.xy_table_model)
        self.xy_table_view.horizontalHeader().setVisible(False)
        self.xy_table_view.verticalHeader().setVisible(False)
        self.xy_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.xy_table_view.horizontalHeader().setDefaultSectionSize(72)
        self.xy_table_view.verticalHeader().setDefaultSectionSize(24)
        self.xy_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.xy_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.xy_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_xy_cell_label)
        self.xy_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.xy_table_view, freeze_rows=3, freeze_cols=3)

    def update_xy_cell_label(self, current, previous):
        if not current.isValid() or self.df_xy_display is None:
            self.xy_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_xy_display.index) or column >= len(self.df_xy_display.columns):
            self.xy_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_xy_display.iat[row, column]
        if value == "":
            self.xy_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.xy_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_phase_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_phase_parameter = self.phase_parameter_combo.currentText().strip()
        self.phase_rotation_degrees = int(self.phase_rotation_spin.value())
        self.df_phase_display = build_phase_magnitude_display_table(
            self.df_all,
            self.current_phase_parameter,
            rotation_degrees=self.phase_rotation_degrees,
        )

        self.phase_table_model = PandasTableModel(self.df_phase_display)
        self.phase_table_view.setModel(self.phase_table_model)
        self.phase_table_view.horizontalHeader().setVisible(False)
        self.phase_table_view.verticalHeader().setVisible(False)
        self.phase_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.phase_table_view.horizontalHeader().setDefaultSectionSize(88)
        self.phase_table_view.verticalHeader().setDefaultSectionSize(24)
        self.phase_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.phase_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.phase_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_phase_cell_label)
        self.phase_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.phase_table_view, freeze_rows=3, freeze_cols=3)

    def update_phase_cell_label(self, current, previous):
        if not current.isValid() or self.df_phase_display is None:
            self.phase_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_phase_display.index) or column >= len(self.df_phase_display.columns):
            self.phase_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_phase_display.iat[row, column]
        if value == "":
            self.phase_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.phase_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def _on_phase_rotation_changed(self, value):
        self.refresh_phase_table()
        if self.df_all is not None and not self.df_all.empty and self.current_smith_mode == "pm":
            self.refresh_smith_chart()

    def refresh_contour_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_contour_parameter = self.contour_parameter_combo.currentText().strip()
        self.df_contour_display = build_contour_display_table(self.df_all, self.current_contour_parameter)

        self.contour_table_model = PandasTableModel(self.df_contour_display)
        self.contour_table_view.setModel(self.contour_table_model)
        self.contour_table_view.horizontalHeader().setVisible(False)
        self.contour_table_view.verticalHeader().setVisible(False)
        self.contour_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.contour_table_view.horizontalHeader().setDefaultSectionSize(72)
        self.contour_table_view.verticalHeader().setDefaultSectionSize(24)
        self.contour_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.contour_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.contour_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_contour_cell_label)
        self.contour_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.contour_table_view, freeze_rows=3, freeze_cols=3)

    def update_contour_cell_label(self, current, previous):
        if not current.isValid() or self.df_contour_display is None:
            self.contour_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_contour_display.index) or column >= len(self.df_contour_display.columns):
            self.contour_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_contour_display.iat[row, column]
        if value == "":
            self.contour_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.contour_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_dz_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_dz_parameter = self.dz_parameter_combo.currentText().strip()
        self.df_dz_display = build_delta_impedance_display_table(self.df_all, self.current_dz_parameter)

        self.dz_table_model = PandasTableModel(self.df_dz_display)
        self.dz_table_view.setModel(self.dz_table_model)
        self.dz_table_view.horizontalHeader().setVisible(False)
        self.dz_table_view.verticalHeader().setVisible(False)
        self.dz_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.dz_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.dz_table_view.verticalHeader().setDefaultSectionSize(24)
        self.dz_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.dz_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.dz_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_dz_cell_label)
        self.dz_cell_label.setText("Click a cell to see the value here.")

    def update_dz_cell_label(self, current, previous):
        if not current.isValid() or self.df_dz_display is None:
            self.dz_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_dz_display.index) or column >= len(self.df_dz_display.columns):
            self.dz_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_dz_display.iat[row, column]
        if value == "":
            self.dz_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.dz_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_impedance_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_impedance_parameter = self.impedance_parameter_combo.currentText().strip()
        self.df_impedance_display = build_impedance_display_table(self.df_all, self.current_impedance_parameter)

        self.impedance_table_model = PandasTableModel(self.df_impedance_display)
        self.impedance_table_view.setModel(self.impedance_table_model)
        self.impedance_table_view.horizontalHeader().setVisible(False)
        self.impedance_table_view.verticalHeader().setVisible(False)
        self.impedance_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.impedance_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.impedance_table_view.verticalHeader().setDefaultSectionSize(24)
        self.impedance_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.impedance_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.impedance_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_impedance_cell_label)
        self.impedance_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.impedance_table_view, freeze_rows=3, freeze_cols=3)

    def refresh_zpar_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_zpar_parameter = self.zpar_parameter_combo.currentText().strip()
        self.df_zpar_display = build_zpar_display_table(self.df_all, self.current_zpar_parameter)

        self.zpar_table_model = PandasTableModel(self.df_zpar_display)
        self.zpar_table_view.setModel(self.zpar_table_model)
        self.zpar_table_view.horizontalHeader().setVisible(False)
        self.zpar_table_view.verticalHeader().setVisible(False)
        self.zpar_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.zpar_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.zpar_table_view.verticalHeader().setDefaultSectionSize(24)
        self.zpar_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.zpar_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.zpar_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_zpar_cell_label)
        self.zpar_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.zpar_table_view, freeze_rows=4, freeze_cols=4)

    def update_zpar_cell_label(self, current, previous):
        if not current.isValid() or self.df_zpar_display is None:
            self.zpar_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_zpar_display.index) or column >= len(self.df_zpar_display.columns):
            self.zpar_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_zpar_display.iat[row, column]
        if value == "":
            self.zpar_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.zpar_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_abcd_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_abcd_parameter = self.abcd_parameter_combo.currentText().strip()
        self.df_abcd_display = build_abcd_display_table(self.df_all, self.current_abcd_parameter)

        self.abcd_table_model = PandasTableModel(self.df_abcd_display)
        self.abcd_table_view.setModel(self.abcd_table_model)
        self.abcd_table_view.horizontalHeader().setVisible(False)
        self.abcd_table_view.verticalHeader().setVisible(False)
        self.abcd_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.abcd_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.abcd_table_view.verticalHeader().setDefaultSectionSize(24)
        self.abcd_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.abcd_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.abcd_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_abcd_cell_label)
        self.abcd_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.abcd_table_view, freeze_rows=4, freeze_cols=4)

    def update_abcd_cell_label(self, current, previous):
        if not current.isValid() or self.df_abcd_display is None:
            self.abcd_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_abcd_display.index) or column >= len(self.df_abcd_display.columns):
            self.abcd_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_abcd_display.iat[row, column]
        if value == "":
            self.abcd_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.abcd_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def update_impedance_cell_label(self, current, previous):
        if not current.isValid() or self.df_impedance_display is None:
            self.impedance_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_impedance_display.index) or column >= len(self.df_impedance_display.columns):
            self.impedance_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_impedance_display.iat[row, column]
        if value == "":
            self.impedance_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.impedance_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_zl_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.df_zl_display = build_zl_gin0_display_table(self.df_all)

        self.zl_table_model = PandasTableModel(self.df_zl_display)
        self.zl_table_view.setModel(self.zl_table_model)
        self.zl_table_view.horizontalHeader().setVisible(False)
        self.zl_table_view.verticalHeader().setVisible(False)
        self.zl_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.zl_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.zl_table_view.verticalHeader().setDefaultSectionSize(24)
        self.zl_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.zl_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.zl_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_zl_cell_label)
        self.zl_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.zl_table_view, freeze_rows=3, freeze_cols=3)

    def update_zl_cell_label(self, current, previous):
        if not current.isValid() or self.df_zl_display is None:
            self.zl_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_zl_display.index) or column >= len(self.df_zl_display.columns):
            self.zl_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_zl_display.iat[row, column]
        if value == "":
            self.zl_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.zl_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_reflection_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_reflection_parameter = self.reflection_parameter_combo.currentText().strip()
        # Table always shows horizontal mode; heatmap shows both maps simultaneously
        self.df_reflection_display = build_reflection_display_table(
            self.df_all,
            self.current_reflection_parameter,
            "horizontal",
        )

        self.reflection_table_model = PandasTableModel(self.df_reflection_display)
        self.reflection_table_view.setModel(self.reflection_table_model)
        self.reflection_table_view.horizontalHeader().setVisible(False)
        self.reflection_table_view.verticalHeader().setVisible(False)
        self.reflection_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.reflection_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.reflection_table_view.verticalHeader().setDefaultSectionSize(24)
        self.reflection_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.reflection_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.reflection_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_reflection_cell_label)
        self.reflection_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.reflection_table_view, freeze_rows=3, freeze_cols=3)
        if _MATPLOTLIB_OK:
            self.plot_reflection_resolution(show_message_on_error=False)
        if self.current_smith_mode == "dgamma" and self.df_all is not None and not self.df_all.empty:
            self.refresh_smith_chart()

    def update_reflection_cell_label(self, current, previous):
        if not current.isValid() or self.df_reflection_display is None:
            self.reflection_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_reflection_display.index) or column >= len(self.df_reflection_display.columns):
            self.reflection_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_reflection_display.iat[row, column]
        if value == "":
            self.reflection_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.reflection_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_efficiency_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        self.current_efficiency_mode = self.efficiency_mode_combo.currentData()
        self.df_efficiency_display = build_efficiency_display_table(self.df_all, self.current_efficiency_mode)

        # Rebuild Smith chart efficiency lookup to match the current formula
        self.smith_efficiency_lookup = build_smith_efficiency_lookup(self.df_all, self.current_efficiency_mode)
        if self.current_smith_mode == "efficiency":
            self._draw_smith_chart(self.smith_plot_points, self.current_smith_parameter)

        self.efficiency_table_model = PandasTableModel(self.df_efficiency_display)
        self.efficiency_table_view.setModel(self.efficiency_table_model)
        self.efficiency_table_view.horizontalHeader().setVisible(False)
        self.efficiency_table_view.verticalHeader().setVisible(False)
        self.efficiency_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.efficiency_table_view.horizontalHeader().setDefaultSectionSize(80)
        self.efficiency_table_view.verticalHeader().setDefaultSectionSize(24)
        self.efficiency_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.efficiency_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.efficiency_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_efficiency_cell_label)
        self.efficiency_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.efficiency_table_view, freeze_rows=3, freeze_cols=3)

    def refresh_iout_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        try:
            input_power = float(self.iout_power_edit.text().strip() or "100")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a numeric input power in watts.")
            return
        if input_power <= 0:
            QMessageBox.warning(self, "Input Error", "Input power must be greater than 0 W.")
            return

        self.current_iout_mode = self.iout_formula_combo.currentData()
        self.input_power_watts = input_power
        self.df_iout_display = build_iout_display_table(
            self.df_all,
            self.input_power_watts,
            self.current_iout_mode,
        )

        self.iout_table_model = PandasTableModel(self.df_iout_display)
        self.iout_table_view.setModel(self.iout_table_model)
        self.iout_table_view.horizontalHeader().setVisible(False)
        self.iout_table_view.verticalHeader().setVisible(False)
        self.iout_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.iout_table_view.horizontalHeader().setDefaultSectionSize(96)
        self.iout_table_view.verticalHeader().setDefaultSectionSize(24)
        self.iout_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.iout_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.iout_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_iout_cell_label)
        self.iout_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.iout_table_view, freeze_rows=3, freeze_cols=3)
        self.draw_iout_heatmap()

    def refresh_vpp_table(self):
        if self.df_all is None or self.df_all.empty:
            return

        try:
            input_power = float(self.vpp_power_edit.text().strip() or "100")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a numeric input power in watts.")
            return
        if input_power <= 0:
            QMessageBox.warning(self, "Input Error", "Input power must be greater than 0 W.")
            return

        self.vpp_power_watts = input_power
        self.df_vpp_display = build_vpp_display_table(self.df_all, self.vpp_power_watts)

        self.vpp_table_model = PandasTableModel(self.df_vpp_display)
        self.vpp_table_view.setModel(self.vpp_table_model)
        self.vpp_table_view.horizontalHeader().setVisible(False)
        self.vpp_table_view.verticalHeader().setVisible(False)
        self.vpp_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.vpp_table_view.horizontalHeader().setDefaultSectionSize(96)
        self.vpp_table_view.verticalHeader().setDefaultSectionSize(24)
        self.vpp_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.vpp_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.vpp_table_view.selectionModel()
        if selection_model is not None:
            selection_model.currentChanged.connect(self.update_vpp_cell_label)
        self.vpp_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.vpp_table_view, freeze_rows=3, freeze_cols=3)
        self.draw_vpp_heatmap()

    def update_efficiency_cell_label(self, current, previous):
        if not current.isValid() or self.df_efficiency_display is None:
            self.efficiency_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_efficiency_display.index) or column >= len(self.df_efficiency_display.columns):
            self.efficiency_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_efficiency_display.iat[row, column]
        if value == "":
            self.efficiency_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.efficiency_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def update_iout_cell_label(self, current, previous):
        if not current.isValid() or self.df_iout_display is None:
            self.iout_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_iout_display.index) or column >= len(self.df_iout_display.columns):
            self.iout_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_iout_display.iat[row, column]
        if value == "":
            self.iout_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.iout_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def update_vpp_cell_label(self, current, previous):
        if not current.isValid() or self.df_vpp_display is None:
            self.vpp_cell_label.setText("Click a cell to see the value here.")
            return

        row = current.row()
        column = current.column()
        if row >= len(self.df_vpp_display.index) or column >= len(self.df_vpp_display.columns):
            self.vpp_cell_label.setText("Click a cell to see the value here.")
            return

        value = self.df_vpp_display.iat[row, column]
        if value == "":
            self.vpp_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
            self.vpp_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def refresh_phi_out_table(self):
        if self.df_all is None or self.df_all.empty:
           return

        self.df_phi_out_display = build_phi_out_display_table(self.df_all)

        self.phi_out_table_model = PandasTableModel(self.df_phi_out_display)
        self.phi_out_table_view.setModel(self.phi_out_table_model)
        self.phi_out_table_view.horizontalHeader().setVisible(False)
        self.phi_out_table_view.verticalHeader().setVisible(False)
        self.phi_out_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.phi_out_table_view.horizontalHeader().setDefaultSectionSize(96)
        self.phi_out_table_view.verticalHeader().setDefaultSectionSize(24)
        self.phi_out_table_view.setSelectionBehavior(QTableView.SelectItems)
        self.phi_out_table_view.setSelectionMode(QTableView.SingleSelection)
        selection_model = self.phi_out_table_view.selectionModel()
        if selection_model is not None:
           selection_model.currentChanged.connect(self.update_phi_out_cell_label)
        self.phi_out_cell_label.setText("Click a cell to see the value here.")
        self._apply_freeze_panes(self.phi_out_table_view, freeze_rows=3, freeze_cols=3)
        self.draw_phi_out_heatmap()

    def update_phi_out_cell_label(self, current, previous):
        if not current.isValid() or self.df_phi_out_display is None:
           self.phi_out_cell_label.setText("Click a cell to see the value here.")
           return

        row = current.row()
        column = current.column()
        if row >= len(self.df_phi_out_display.index) or column >= len(self.df_phi_out_display.columns):
           self.phi_out_cell_label.setText("Click a cell to see the value here.")
           return

        value = self.df_phi_out_display.iat[row, column]
        if value == "":
           self.phi_out_cell_label.setText(f"Row {row + 1}, Col {column + 1}: empty")
        else:
           self.phi_out_cell_label.setText(f"Row {row + 1}, Col {column + 1}: {value}")

    def draw_iout_heatmap(self):
        if not _MATPLOTLIB_OK or self.df_iout_display is None or self.df_iout_display.empty:
           return
        
        heatmap_data = extract_heatmap_data_from_table(self.df_iout_display)
        if heatmap_data.size == 0:
           return
        
        self.iout_heatmap_figure.clear()
        ax = self.iout_heatmap_figure.add_subplot(111)
        
        vmin = np.nanmin(heatmap_data)
        vmax = np.nanmax(heatmap_data)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
           return
        
        im = ax.imshow(heatmap_data, aspect="auto", origin="lower", cmap="viridis", 
                     vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title("Iout Heatmap", fontsize=11, fontweight="bold")
        ax.set_xlabel("C1", fontsize=9)
        ax.set_ylabel("C2", fontsize=9)
        ax.tick_params(labelsize=7)
        self.iout_heatmap_figure.colorbar(im, ax=ax, pad=0.02)
        self.iout_heatmap_figure.tight_layout()
        self.iout_heatmap_canvas.draw()

    def draw_vpp_heatmap(self):
        if not _MATPLOTLIB_OK or self.df_vpp_display is None or self.df_vpp_display.empty:
           return
        
        heatmap_data = extract_heatmap_data_from_table(self.df_vpp_display)
        if heatmap_data.size == 0:
           return
        
        self.vpp_heatmap_figure.clear()
        ax = self.vpp_heatmap_figure.add_subplot(111)
        
        vmin = np.nanmin(heatmap_data)
        vmax = np.nanmax(heatmap_data)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
           return
        
        im = ax.imshow(heatmap_data, aspect="auto", origin="lower", cmap="plasma", 
                     vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title("Vpp Heatmap", fontsize=11, fontweight="bold")
        ax.set_xlabel("C1", fontsize=9)
        ax.set_ylabel("C2", fontsize=9)
        ax.tick_params(labelsize=7)
        self.vpp_heatmap_figure.colorbar(im, ax=ax, pad=0.02)
        self.vpp_heatmap_figure.tight_layout()
        self.vpp_heatmap_canvas.draw()

    def draw_phi_out_heatmap(self):
        if not _MATPLOTLIB_OK or self.df_phi_out_display is None or self.df_phi_out_display.empty:
           return
        
        heatmap_data = extract_heatmap_data_from_table(self.df_phi_out_display)
        if heatmap_data.size == 0:
           return
        
        self.phi_out_heatmap_figure.clear()
        ax = self.phi_out_heatmap_figure.add_subplot(111)
        
        vmin = np.nanmin(heatmap_data)
        vmax = np.nanmax(heatmap_data)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
           return
        
        im = ax.imshow(heatmap_data, aspect="auto", origin="lower", cmap="coolwarm", 
                     vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title("φ_out Heatmap", fontsize=11, fontweight="bold")
        ax.set_xlabel("C1", fontsize=9)
        ax.set_ylabel("C2", fontsize=9)
        ax.tick_params(labelsize=7)
        self.phi_out_heatmap_figure.colorbar(im, ax=ax, pad=0.02)
        self.phi_out_heatmap_figure.tight_layout()
        self.phi_out_heatmap_canvas.draw()

    def _on_efficiency_threshold_changed(self):
        if self.df_all is not None and not self.df_all.empty:
            thresholds = self._get_efficiency_thresholds(show_message=False)
            if thresholds is not None:
                self.efficiency_good_threshold, self.efficiency_poor_threshold = thresholds
            if self.current_smith_mode == "efficiency":
                self.refresh_smith_chart()

    def _get_efficiency_thresholds(self, show_message=False):
        try:
            good_threshold = float(self.efficiency_good_edit.text().strip() or "100") / 100.0
            poor_threshold = float(self.efficiency_poor_edit.text().strip() or "10") / 100.0
        except ValueError:
            if show_message:
                QMessageBox.warning(self, "Input Error", "Please enter numeric good and poor efficiency percentages.")
            return None

        if good_threshold < 0 or good_threshold > 1 or poor_threshold < 0 or poor_threshold > 1:
            if show_message:
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Efficiency values must be between 0 and 100%."
                )
            return None

        if good_threshold <= poor_threshold:
            if show_message:
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Good efficiency must be greater than poor efficiency."
                )
            return None

        return good_threshold, poor_threshold

    def _on_reflection_threshold_changed(self):
        if self.df_all is not None and not self.df_all.empty:
            self.plot_reflection_resolution(show_message_on_error=False)
            if self.current_smith_mode == "dgamma":
                self.refresh_smith_chart()

    def _get_reflection_thresholds(self, show_message=False):
        try:
            good_threshold = float(self.reflection_good_edit.text().strip() or "0")
            poor_threshold = float(self.reflection_poor_edit.text().strip() or "0")
        except ValueError:
            if show_message:
                QMessageBox.warning(self, "Input Error", "Please enter numeric good and poor reflection values.")
            return None

        if good_threshold < 0 or poor_threshold <= 0 or good_threshold >= poor_threshold:
            if show_message:
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Good resolution must be >= 0 and smaller than poor resolution."
                )
            return None

        return good_threshold, poor_threshold

    def plot_reflection_resolution(self, show_message_on_error=True):
        if not _MATPLOTLIB_OK:
            QMessageBox.warning(
                self, "Missing Library",
                "matplotlib is required.\nInstall with:  pip install matplotlib"
            )
            return

        if self.df_all is None or self.df_all.empty:
            if show_message_on_error:
                QMessageBox.warning(self, "No Data", "Please convert data before plotting.")
            return

        thresholds = self._get_reflection_thresholds(show_message=show_message_on_error)
        if thresholds is None:
            return
        good_threshold, poor_threshold = thresholds

        heatmap_range = self._get_reflection_heatmap_range()

        horizontal, vertical, x_values, y_values = build_delta_reflection_plot_data(
            self.df_all, self.current_reflection_parameter
        )
        h_mag = np.abs(horizontal)
        v_mag = np.abs(vertical)
        all_finite = np.concatenate([
            h_mag[np.isfinite(h_mag)],
            v_mag[np.isfinite(v_mag)],
        ])
        if all_finite.size == 0:
            if show_message_on_error:
                QMessageBox.warning(self, "No Data", "No reflection-coefficient values were available to plot.")
            return

        v_min = float(all_finite.min())
        v_avg = float(all_finite.mean())
        v_max = float(all_finite.max())

        heatmap_data = np.minimum(h_mag, v_mag)
        heat_finite = heatmap_data[np.isfinite(heatmap_data)]
        heat_min = float(heat_finite.min()) if heat_finite.size else 0.0
        heat_avg = float(heat_finite.mean()) if heat_finite.size else 0.0
        heat_max = float(heat_finite.max()) if heat_finite.size else 0.0

        self.reflection_status_label.setText(
            f"{self.current_reflection_parameter} |ΔΓ| (both maps): min {v_min:.4g}, avg {v_avg:.4g}, max {v_max:.4g} | "
            f"green≤{good_threshold:g}, red≥{poor_threshold:g} | "
            f"Heatmap min(H,V): min {heat_min:.4g}, avg {heat_avg:.4g}, max {heat_max:.4g}"
        )
        self._draw_reflection_plot(h_mag, v_mag, heatmap_data, x_values, y_values,
                                   good_threshold, poor_threshold, heatmap_range)

    def _get_reflection_heatmap_range(self):
        """Return (vmin, vmax) for the reflection heatmap colour scale, or None if invalid."""
        try:
            vmin = float(self.reflection_heatmap_min_edit.text().strip() or "0")
            vmax = float(self.reflection_heatmap_max_edit.text().strip() or "0")
        except ValueError:
            return None
        if vmin < 0 or vmax <= 0 or vmin >= vmax:
            return None
        return vmin, vmax

    def _draw_reflection_plot(self, h_mag, v_mag, heatmap_data, x_values, y_values,
                               good_threshold, poor_threshold, heatmap_range=None):
        self.reflection_figure.clear()
        cmap = _get_cmap("RdYlGn_r")
        norm = Normalize(vmin=good_threshold, vmax=poor_threshold, clip=True)

        gs = self.reflection_figure.add_gridspec(1, 3, wspace=0.35, left=0.04, right=0.97, top=0.92, bottom=0.08)

        for subplot_idx, (matrix, direction) in enumerate((
            (h_mag, "Horizontal (ΔC1)"),
            (v_mag, "Vertical (ΔC2)"),
        )):
            ax = self.reflection_figure.add_subplot(gs[0, subplot_idx])
            im = ax.imshow(
                matrix,
                aspect="auto",
                origin="lower",
                cmap=cmap,
                norm=norm,
                interpolation="nearest",
                extent=[0, len(x_values), 0, len(y_values)],
            )
            ax.set_xlabel("C1 Position", fontsize=9)
            ax.set_ylabel("C2 Position", fontsize=9)
            ax.set_title(
                f"|ΔΓ| {direction} — {self.current_reflection_parameter}",
                fontsize=10,
                fontweight="bold",
            )
            ax.tick_params(labelsize=8)
            for boundary in range(64, max(len(x_values), len(y_values)), 64):
                ax.axvline(boundary, color="white", linewidth=0.35, alpha=0.5)
                ax.axhline(boundary, color="white", linewidth=0.35, alpha=0.5)
            self.reflection_figure.colorbar(im, ax=ax, pad=0.02).set_label(
                f"|ΔΓ|  green≤{good_threshold:g}  red≥{poor_threshold:g}", fontsize=8
            )

        # Heatmap: min(horizontal, vertical) — best achievable resolution at each point
        ax_heat = self.reflection_figure.add_subplot(gs[0, 2])
        if heatmap_range is not None:
            heat_vmin, heat_vmax = heatmap_range
        else:
            heat_vmin, heat_vmax = good_threshold, poor_threshold
        heat_norm = Normalize(vmin=heat_vmin, vmax=heat_vmax, clip=True)
        heat_im = ax_heat.imshow(
            heatmap_data,
            aspect="auto",
            origin="lower",
            cmap=cmap,
            norm=heat_norm,
            interpolation="nearest",
            extent=[0, len(x_values), 0, len(y_values)],
        )
        ax_heat.set_title(
            f"Heatmap: min(H, V) |ΔΓ| — {self.current_reflection_parameter}",
            fontsize=10,
            fontweight="bold",
        )
        ax_heat.set_xlabel("C1 Position", fontsize=9)
        ax_heat.set_ylabel("C2 Position", fontsize=9)
        ax_heat.tick_params(labelsize=8)
        for boundary in range(64, max(len(x_values), len(y_values)), 64):
            ax_heat.axvline(boundary, color="white", linewidth=0.35, alpha=0.5)
            ax_heat.axhline(boundary, color="white", linewidth=0.35, alpha=0.5)
        heat_cb = self.reflection_figure.colorbar(heat_im, ax=ax_heat, pad=0.02)
        heat_cb.set_label(f"|ΔΓ|  [{heat_vmin:g} – {heat_vmax:g}]", fontsize=8)

        self.reflection_canvas.draw()

    def refresh_smith_chart(self):
        if self.df_all is None or self.df_all.empty:
            self.df_smith_points = []
            self.smith_plot_points = []
            self.smith_plot_values = np.array([], dtype=complex)
            if _MATPLOTLIB_OK:
                self._draw_smith_chart([], self.current_smith_parameter)
            return

        self.current_smith_parameter = self.smith_parameter_combo.currentText().strip()
        if self.current_smith_mode == "contour":
            self.df_smith_points = build_smith_contour_plot_data(self.df_all, self.current_smith_parameter)
            self.smith_dz_lookup = {}
            self.smith_dgamma_lookup = {}
            self.smith_efficiency_lookup = {}
        else:
            self.df_smith_points = build_smith_chart_plot_data(self.df_all, self.current_smith_parameter)
            if {"S22_r", "S22_x"}.issubset(set(self.df_all.columns)):
                self.smith_dz_lookup = build_smith_dz_lookup(self.df_all)
            else:
                self.smith_dz_lookup = {}
            if {f"{self.current_smith_parameter}_r", f"{self.current_smith_parameter}_x"}.issubset(set(self.df_all.columns)):
                self.smith_dgamma_lookup = build_smith_dgamma_lookup(
                    self.df_all,
                    self.current_smith_parameter,
                    self.current_reflection_mode,
                )
            else:
                self.smith_dgamma_lookup = {}
            self.smith_efficiency_lookup = build_smith_efficiency_lookup(self.df_all, self.current_efficiency_mode)

        if self.current_smith_mode == "contour":
            contour_count = max(len(self.df_smith_points) - 1, 0)
            self.smith_status_label.setText(
                f"{self.current_smith_parameter}: contour edge with {contour_count:,} points"
            )
        elif self.current_smith_mode == "pm":
            self.smith_status_label.setText(
                f"{self.current_smith_parameter}: phase/magnitude points | rotation {self.phase_rotation_spin.value()}°"
            )
        elif self.current_smith_mode == "dz":
            thresholds = self._get_dz_thresholds(show_message=False)
            if thresholds is None:
                good_threshold, poor_threshold = 0.001, 1.0
            else:
                good_threshold, poor_threshold = thresholds
            dz_count = sum(
                1 for point in self.df_smith_points
                if (point["x_c1"], point["y_c2"]) in self.smith_dz_lookup
            )
            self.smith_status_label.setText(
                f"{self.current_smith_parameter}: {len(self.df_smith_points):,} points | dZ colors on {dz_count:,} points | green≤{good_threshold:g}, red≥{poor_threshold:g}"
            )
        elif self.current_smith_mode == "dgamma":
            thresholds = self._get_reflection_thresholds(show_message=False)
            if thresholds is None:
                good_threshold, poor_threshold = 0.0, 0.03
            else:
                good_threshold, poor_threshold = thresholds
            dgamma_count = sum(
                1 for point in self.df_smith_points
                if (point["x_c1"], point["y_c2"]) in self.smith_dgamma_lookup
            )
            self.smith_status_label.setText(
                f"{self.current_smith_parameter}: {len(self.df_smith_points):,} points | dΓ({self.current_reflection_mode}) colors on {dgamma_count:,} points | green≤{good_threshold:g}, red≥{poor_threshold:g}"
            )
        elif self.current_smith_mode == "efficiency":
            efficiency_count = sum(
                1 for point in self.df_smith_points
                if (point["x_c1"], point["y_c2"]) in self.smith_efficiency_lookup
            )
            good_pct = self.efficiency_good_threshold * 100
            poor_pct = self.efficiency_poor_threshold * 100
            self.smith_status_label.setText(
                f"S11/S21: {len(self.df_smith_points):,} points | Efficiency colors on {efficiency_count:,} points | green≥{good_pct:.1f}%, red≤{poor_pct:.1f}%"
            )
        else:
            self.smith_status_label.setText(
                f"{self.current_smith_parameter}: {len(self.df_smith_points):,} points"
            )

        self._draw_smith_chart(self.df_smith_points, self.current_smith_parameter)

    def _on_smith_mode_changed(self, mode_name, checked):
        if not checked:
            return
        self.current_smith_mode = mode_name
        if self.df_all is not None and not self.df_all.empty:
            self.refresh_smith_chart()

    def _add_manual_impedance_row(self):
        if self.manual_impedance_model is None:
            return
        self.manual_impedance_model.add_blank_row()

    def _clear_manual_impedance_points(self):
        if self.manual_impedance_model is None:
            return
        self.manual_impedance_model.clear_values()
        self.smith_manual_points = []
        self.manual_impedance_status_label.setText("Manual impedance points cleared.")
        if _MATPLOTLIB_OK:
            self._draw_smith_chart(self.df_smith_points or [], self.current_smith_parameter)

    def _import_manual_impedance_csv(self):
        if self.manual_impedance_model is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Impedance Data",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", f"Failed to read CSV file:\n{exc}")
            return

        # Normalise column names: key = stripped+lowercased, value = original (for row indexing)
        col_map = {c.strip().lower(): c for c in df.columns}
        r_col = col_map.get("r")
        x_col = col_map.get("jx") or col_map.get("x")

        if r_col is None or x_col is None:
            QMessageBox.critical(
                self,
                "Import Error",
                "CSV must contain columns 'R' and 'jX' (or 'X').\n"
                f"Found columns: {list(df.columns)}"
            )
            return

        imported = 0
        skipped = 0
        for _, row in df.iterrows():
            r_val = str(row[r_col]).strip()
            x_val = str(row[x_col]).strip()
            if not r_val or not x_val:
                skipped += 1
                continue
            if not is_float_text(r_val) or not is_float_text(x_val):
                skipped += 1
                continue
            self.manual_impedance_model.set_next_available_point(float(r_val), float(x_val))
            imported += 1

        msg = f"Imported {imported} impedance point(s) from CSV."
        if skipped:
            msg += f" ({skipped} row(s) skipped due to invalid or empty values.)"
        self.manual_impedance_status_label.setText(msg)

    def _carry_over_search_result(self):
        if self.manual_impedance_model is None:
            return

        if self.smith_search_result is None:
            QMessageBox.warning(self, "No Search Result", "Run Search ZL first before carrying over a value.")
            return

        impedance = self.smith_search_result.get("impedance")
        if impedance is None:
            QMessageBox.warning(self, "No Search Result", "The current search result does not have a valid impedance.")
            return

        row_number = self.manual_impedance_model.set_next_available_point(impedance.real, impedance.imag)
        self.manual_impedance_status_label.setText(
            f"Carried ZL = {format_impedance_text(impedance)} into manual row {row_number}."
        )

    def _run_smith_demo_points(self):
        if self.df_all is None or self.df_all.empty:
            QMessageBox.warning(self, "No Data", "Please convert data before running demo.")
            return
        if self.manual_impedance_model is None:
            return

        self._clear_manual_impedance_points()
        self.smith_search_result = None

        demo_percentages = list(range(0, 101, 10))
        for pct in demo_percentages:
            pct_text = str(pct)
            self.zl_search_c1_edit.setText(pct_text)
            self.zl_search_c2_edit.setText(pct_text)
            self._search_load_impedance()
            if self.smith_search_result is None:
                return
            self._carry_over_search_result()
            self._plot_manual_impedance_points()

        self.manual_impedance_status_label.setText(
            "Demo complete: plotted points for C1/C2 = 0%, 10%, ..., 100%."
        )

    def _plot_manual_impedance_points(self):
        if self.manual_impedance_model is None:
            return
        if not _MATPLOTLIB_OK:
            QMessageBox.warning(
                self, "Missing Library",
                "matplotlib is required.\nInstall with:  pip install matplotlib"
            )
            return

        plotted_points = []
        for point_id, r_value, x_value in self.manual_impedance_model.iter_points():
            gamma = impedance_to_reflection_value(r_value, x_value)
            if gamma is None:
                continue
            plotted_points.append({
                "id": point_id,
                "r": r_value,
                "x": x_value,
                "gamma": gamma,
            })

        self.smith_manual_points = plotted_points
        if not plotted_points:
            self.manual_impedance_status_label.setText("No valid R/X values were found to plot.")
            self._draw_smith_chart(self.df_smith_points or [], self.current_smith_parameter)
            return

        labels = [f"#{point['id']} ZL={format_impedance_text(complex(point['r'], point['x']))}" for point in plotted_points]
        self.manual_impedance_status_label.setText(f"Plotted {len(plotted_points)} impedance point(s) on the Smith chart.")
        self._draw_smith_chart(self.df_smith_points or [], self.current_smith_parameter)

    def _search_load_impedance(self):
        if self.df_all is None or self.df_all.empty:
            QMessageBox.warning(self, "No Data", "Please convert data before searching.")
            return

        try:
            c1_pct = float(self.zl_search_c1_edit.text().strip())
            c2_pct = float(self.zl_search_c2_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter numeric C1% and C2% values.")
            return

        if c1_pct < 0 or c1_pct > 100 or c2_pct < 0 or c2_pct > 100:
            QMessageBox.warning(self, "Input Error", "Please enter C1% and C2% between 0 and 100.")
            return

        try:
            result = find_nearest_load_impedance(
                self.df_all,
                c1_pct,
                c2_pct,
                "S22",
                conjugate=self.smith_conjugate_button.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.critical(self, "Search Failed", str(exc))
            return

        self.smith_search_result = result
        impedance_text = format_impedance_text(result["impedance"])
        match_text = "exact" if result["exact_match"] else f"nearest (distance {result['distance']:.3g})"
        conjugate_text = "conjugate on" if self.smith_conjugate_button.isChecked() else "conjugate off"
        self.zl_search_result_label.setText(
            f"Requested C1 {result['requested_c1_pct']:.2f}%, C2 {result['requested_c2_pct']:.2f}% -> "
            f"{match_text}: C1 {result['x_c1_pct']:.2f}%, C2 {result['y_c2_pct']:.2f}% | ZL = {impedance_text} ohms | {conjugate_text}"
        )

        if _MATPLOTLIB_OK:
            self._draw_smith_chart(self.df_smith_points or [], self.current_smith_parameter)

    def _on_dz_threshold_changed(self):
        if self.current_smith_mode == "dz" and self.df_all is not None and not self.df_all.empty:
            self.refresh_smith_chart()

    def _get_dz_thresholds(self, show_message=False):
        try:
            good_threshold = float(self.dz_good_edit.text().strip() or "0")
            poor_threshold = float(self.dz_poor_edit.text().strip() or "0")
        except ValueError:
            if show_message:
                QMessageBox.warning(self, "Input Error", "Please enter numeric good and poor resolution values.")
            return None

        if good_threshold <= 0 or poor_threshold <= 0 or good_threshold >= poor_threshold:
            if show_message:
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Good resolution must be positive and smaller than poor resolution."
                )
            return None

        return good_threshold, poor_threshold

    def _draw_smith_chart(self, points, parameter_name):
        if not _MATPLOTLIB_OK:
            return

        self.smith_figure.clear()
        ax = self.smith_figure.add_subplot(111)
        draw_smith_chart_grid(ax)

        if points:
            values = np.array([point["gamma"] for point in points], dtype=complex)
            if self.smith_conjugate_button.isChecked():
                values = np.conjugate(values)
            self.smith_plot_values = values
            self.smith_plot_points = points
            if self.current_smith_mode == "dz":
                thresholds = self._get_dz_thresholds(show_message=False)
                dz_values = np.array(
                    [
                        self.smith_dz_lookup.get((point["x_c1"], point["y_c2"]), np.nan)
                        for point in points
                    ],
                    dtype=float,
                )
                finite_mask = np.isfinite(dz_values)
                if np.any(finite_mask):
                    if thresholds is not None:
                        good_threshold, poor_threshold = thresholds
                    else:
                        good_threshold, poor_threshold = 0.001, 1.0
                    plotted_values = np.where(finite_mask, dz_values, good_threshold)
                    self.smith_scatter = ax.scatter(
                        values.real,
                        values.imag,
                        c=plotted_values,
                        cmap="RdYlGn_r",
                        vmin=good_threshold,
                        vmax=poor_threshold,
                        s=14,
                        alpha=0.9,
                        edgecolors="none",
                        picker=True,
                    )
                    colorbar = self.smith_figure.colorbar(self.smith_scatter, ax=ax, pad=0.02, shrink=0.85)
                    colorbar.set_label(
                        f"|ΔZ| (ohms)  green≤{good_threshold:g}, red≥{poor_threshold:g}",
                        fontsize=9,
                    )
                else:
                    colors = np.arange(len(values))
                    self.smith_scatter = ax.scatter(
                        values.real,
                        values.imag,
                        c=colors,
                        cmap="viridis",
                        s=14,
                        alpha=0.8,
                        edgecolors="none",
                        picker=True,
                    )
            elif self.current_smith_mode == "dgamma":
                thresholds = self._get_reflection_thresholds(show_message=False)
                dgamma_values = np.array(
                    [
                        self.smith_dgamma_lookup.get((point["x_c1"], point["y_c2"]), np.nan)
                        for point in points
                    ],
                    dtype=float,
                )
                finite_mask = np.isfinite(dgamma_values)
                if np.any(finite_mask):
                    if thresholds is not None:
                        good_threshold, poor_threshold = thresholds
                    else:
                        good_threshold, poor_threshold = 0.0, 0.03
                    plotted_values = np.where(finite_mask, dgamma_values, good_threshold)
                    self.smith_scatter = ax.scatter(
                        values.real,
                        values.imag,
                        c=plotted_values,
                        cmap="RdYlGn_r",
                        vmin=good_threshold,
                        vmax=poor_threshold,
                        s=14,
                        alpha=0.9,
                        edgecolors="none",
                        picker=True,
                    )
                    colorbar = self.smith_figure.colorbar(self.smith_scatter, ax=ax, pad=0.02, shrink=0.85)
                    colorbar.set_label(
                        f"|ΔΓ| ({self.current_reflection_mode})  green≤{good_threshold:g}, red≥{poor_threshold:g}",
                        fontsize=9,
                    )
                else:
                    colors = np.arange(len(values))
                    self.smith_scatter = ax.scatter(
                        values.real,
                        values.imag,
                        c=colors,
                        cmap="viridis",
                        s=14,
                        alpha=0.8,
                        edgecolors="none",
                        picker=True,
                    )
            elif self.current_smith_mode == "efficiency":
               efficiency_values = np.array(
                   [
                       self.smith_efficiency_lookup.get((point["x_c1"], point["y_c2"]), np.nan)
                       for point in points
                   ],
                   dtype=float,
               )
               finite_mask = np.isfinite(efficiency_values)
               if np.any(finite_mask):
                   good_threshold = self.efficiency_good_threshold
                   poor_threshold = self.efficiency_poor_threshold
                   plotted_values = np.where(finite_mask, efficiency_values, poor_threshold)
                   self.smith_scatter = ax.scatter(
                       values.real,
                       values.imag,
                       c=plotted_values,
                       cmap="RdYlGn",
                       vmin=poor_threshold,
                       vmax=good_threshold,
                       s=14,
                       alpha=0.9,
                       edgecolors="none",
                       picker=True,
                   )
                   colorbar = self.smith_figure.colorbar(self.smith_scatter, ax=ax, pad=0.02, shrink=0.85)
                   good_pct = good_threshold * 100
                   poor_pct = poor_threshold * 100
                   colorbar.set_label(
                       f"Efficiency (S11/S21)  green≥{good_pct:.1f}%, red≤{poor_pct:.1f}%",
                       fontsize=9,
                   )
               else:
                   colors = np.arange(len(values))
                   self.smith_scatter = ax.scatter(
                       values.real,
                       values.imag,
                       c=colors,
                       cmap="viridis",
                       s=14,
                       alpha=0.8,
                       edgecolors="none",
                       picker=True,
                   )
            elif self.current_smith_mode == "pm":
                rotation_radians = np.deg2rad(self.phase_rotation_spin.value())
                rotated_values = values * np.exp(1j * rotation_radians)
                self.smith_plot_values = rotated_values
                phase_angles = (np.degrees(np.angle(rotated_values)) + 360.0) % 360.0
                point_sizes = 18 + (32 * np.clip(np.abs(rotated_values), 0.0, 1.0))
                self.smith_scatter = ax.scatter(
                   rotated_values.real,
                   rotated_values.imag,
                   c=phase_angles,
                   cmap="twilight",
                   s=point_sizes,
                   alpha=0.9,
                   edgecolors="none",
                   picker=True,
                )
                colorbar = self.smith_figure.colorbar(self.smith_scatter, ax=ax, pad=0.02, shrink=0.85)
                colorbar.set_label("Phase (degrees)", fontsize=9)
            elif self.current_smith_mode == "contour":
               self.smith_scatter = ax.scatter(
                   values.real,
                   values.imag,
                   c="#F57C00",
                   s=18,
                   alpha=0.9,
                   edgecolors="none",
                   picker=True,
               )
               ax.plot(
                   values.real,
                   values.imag,
                   color="#F57C00",
                   linewidth=1.4,
                   alpha=0.9,
                   zorder=4,
               )
            else:
               colors = np.arange(len(values))
               self.smith_scatter = ax.scatter(
                   values.real,
                   values.imag,
                   c=colors,
                   cmap="viridis",
                   s=14,
                    alpha=0.8,
                    edgecolors="none",
                    picker=True,
                )
        else:
            self.smith_plot_values = np.array([], dtype=complex)
            self.smith_plot_points = []
            self.smith_scatter = None

        manual_points = self.smith_manual_points or []
        if manual_points:
            manual_values = np.array([point["gamma"] for point in manual_points], dtype=complex)
            ax.scatter(
                manual_values.real,
                manual_values.imag,
                marker="*",
                s=120,
                c="#D32F2F",
                edgecolors="white",
                linewidths=0.8,
                zorder=5,
            )
            for point, gamma_value in zip(manual_points, manual_values):
                ax.annotate(
                   f"#{point['id']}",
                   (gamma_value.real, gamma_value.imag),
                   textcoords="offset points",
                   xytext=(5, 5),
                   fontsize=8,
                   color="#B71C1C",
                )

        if self.smith_search_result is not None:
            search_gamma = self.smith_search_result["gamma"]
            ax.scatter(
                [search_gamma.real],
                [search_gamma.imag],
                marker="D",
                s=80,
                c="#000000",
                edgecolors="white",
                linewidths=0.8,
                zorder=6,
            )
            ax.annotate(
                "ZL",
                (search_gamma.real, search_gamma.imag),
                textcoords="offset points",
                xytext=(5, -10),
                fontsize=8,
                color="#000000",
            )

        mode_label = {
            "xy": "X-Y Table",
            "dz": "dZ",
            "dgamma": f"dΓ ({self.current_reflection_mode})",
            "dvswr": "dVSWR (Under construction)",
            "contour": "Contour",
            "pm": "P/M",
        }.get(self.current_smith_mode, "X-Y Table")
        ax.set_title(f"Smith Chart - {parameter_name} [{mode_label}]", fontsize=11, fontweight="bold")
        self.smith_canvas.draw()

    def toggle_smith_conjugate(self, checked):
        self.smith_conjugate_enabled = checked
        self.smith_conjugate_button.setText("Conjugate On" if checked else "Conjugate")
        if self.df_smith_points is not None:
            self._draw_smith_chart(self.df_smith_points, self.current_smith_parameter)

    def _save_smith_chart_image(self):
        if not _MATPLOTLIB_OK or not hasattr(self, "smith_figure"):
            QMessageBox.warning(
                self,
                "Missing Library",
                "matplotlib is required.\nInstall with:  pip install matplotlib"
            )
            return

        input_path = self.file_path_edit.text().strip()
        base_name = os.path.splitext(os.path.basename(input_path))[0] if input_path else "smith_chart"
        parameter_name = self.smith_parameter_combo.currentText().strip() or "smith"
        default_name = f"{base_name}_{parameter_name.lower()}_smith_chart.png"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Smith Chart Image",
            default_name,
            "PNG Files (*.png);;All Files (*)"
        )

        if not save_path:
            return

        if not os.path.splitext(save_path)[1]:
            save_path += ".png"

        try:
            self.smith_figure.savefig(save_path, dpi=300, bbox_inches="tight")
            QMessageBox.information(self, "Save Finished", f"Smith chart image saved successfully:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    def _toggle_smith_zoom_in(self, checked):
        if not _MATPLOTLIB_OK or not hasattr(self, "smith_canvas"):
            return

        if not checked:
            self._exit_smith_zoom_mode(reset_button=False)
            return

        if self.smith_plot_values.size == 0:
            QMessageBox.warning(self, "No Plot Data", "Please generate Smith chart points before using Zoom In.")
            self.smith_zoom_in_button.blockSignals(True)
            self.smith_zoom_in_button.setChecked(False)
            self.smith_zoom_in_button.blockSignals(False)
            return

        self.smith_zoom_selection_enabled = True
        self.smith_zoom_start = None
        self.smith_hover_label.setText("Zoom In enabled: drag a rectangle on the Smith chart.")
        self.smith_canvas.setCursor(Qt.CrossCursor)

    def _exit_smith_zoom_mode(self, reset_button=True):
        self.smith_zoom_selection_enabled = False
        self.smith_zoom_start = None
        if self.smith_zoom_rect is not None:
            try:
                self.smith_zoom_rect.remove()
            except Exception:
                pass
            self.smith_zoom_rect = None
            self.smith_canvas.draw_idle()
        if hasattr(self, "smith_canvas"):
            self.smith_canvas.unsetCursor()
        if reset_button and hasattr(self, "smith_zoom_in_button"):
            self.smith_zoom_in_button.blockSignals(True)
            self.smith_zoom_in_button.setChecked(False)
            self.smith_zoom_in_button.blockSignals(False)

    def _on_smith_mouse_press(self, event):
        if not self.smith_zoom_selection_enabled:
            return
        if event.button != 1 or event.inaxes is None or event.xdata is None or event.ydata is None:
            return

        self.smith_zoom_start = (float(event.xdata), float(event.ydata))
        if self.smith_zoom_rect is not None:
            try:
                self.smith_zoom_rect.remove()
            except Exception:
                pass
            self.smith_zoom_rect = None

        from matplotlib.patches import Rectangle
        self.smith_zoom_rect = Rectangle(
            (self.smith_zoom_start[0], self.smith_zoom_start[1]),
            0.0,
            0.0,
            fill=False,
            edgecolor="#D32F2F",
            linewidth=1.2,
            linestyle="--",
            zorder=10,
        )
        event.inaxes.add_patch(self.smith_zoom_rect)
        self.smith_canvas.draw_idle()

    def _on_smith_mouse_release(self, event):
        if not self.smith_zoom_selection_enabled or self.smith_zoom_start is None:
            return

        if event.button != 1 or event.xdata is None or event.ydata is None:
            self._exit_smith_zoom_mode()
            return

        x0, y0 = self.smith_zoom_start
        x1, y1 = float(event.xdata), float(event.ydata)
        x_min, x_max = sorted((x0, x1))
        y_min, y_max = sorted((y0, y1))

        if abs(x_max - x_min) < 1e-6 or abs(y_max - y_min) < 1e-6:
            self._exit_smith_zoom_mode()
            return

        self._open_smith_zoom_window(x_min, x_max, y_min, y_max)
        self._exit_smith_zoom_mode()

    def _open_smith_zoom_window(self, x_min, x_max, y_min, y_max):
        if self.smith_plot_values.size == 0:
            return

        values = self.smith_plot_values
        mask = (
            (values.real >= x_min) & (values.real <= x_max)
            & (values.imag >= y_min) & (values.imag <= y_max)
        )
        selected_values = values[mask]

        manual_values = np.array([], dtype=complex)
        if self.smith_manual_points:
            all_manual_values = np.array([point["gamma"] for point in self.smith_manual_points], dtype=complex)
            manual_mask = (
                (all_manual_values.real >= x_min) & (all_manual_values.real <= x_max)
                & (all_manual_values.imag >= y_min) & (all_manual_values.imag <= y_max)
            )
            manual_values = all_manual_values[manual_mask]

        search_value = None
        if self.smith_search_result is not None:
            current_search = self.smith_search_result.get("gamma")
            if current_search is not None:
                if (x_min <= current_search.real <= x_max) and (y_min <= current_search.imag <= y_max):
                    search_value = current_search

        zoom_window = SmithZoomWindow("Smith Chart Zoom In")
        zoom_window.draw_zoom_chart(
            selected_values,
            manual_values,
            search_value,
            x_min,
            x_max,
            y_min,
            y_max,
            self.current_smith_parameter,
        )
        self.smith_zoom_windows.append(zoom_window)
        zoom_window.show()

    def _format_smith_impedance_text(self, gamma_value):
        z_value = reflect_to_impedance_value(gamma_value.real, gamma_value.imag)
        if z_value is None:
            return "Z=unavailable"

        sign = "+" if z_value.imag >= 0 else "-"
        return f"Z={z_value.real:.6g}{sign}{abs(z_value.imag):.6g}j"

    def _format_smith_hover_text(self, point, gamma_value):
        if point is None:
            return "Hover a point to see impedance and C1/C2 position."

        c1_text = position_label(point["x_c1"])
        c2_text = position_label(point["y_c2"])
        gamma_text = f"Γ={gamma_value.real:.6g}{'+' if gamma_value.imag >= 0 else '-'}{abs(gamma_value.imag):.6g}j"

        if self.current_smith_parameter in IMPEDANCE_PARAMETERS:
            impedance_text = self._format_smith_impedance_text(gamma_value)
        else:
            impedance_text = "Z=not available for this parameter"

        if self.current_smith_mode == "pm":
            pm_text = f" | |Γ|={abs(gamma_value):.6g} | ∠={((np.degrees(np.angle(gamma_value)) + 360.0) % 360.0):.1f}°"
        else:
            pm_text = ""

        return f"C1 {c1_text} | C2 {c2_text} | {gamma_text}{pm_text} | {impedance_text}"

    def _on_smith_hover(self, event):
        if self.smith_zoom_selection_enabled and self.smith_zoom_start is not None and self.smith_zoom_rect is not None:
            if event.inaxes is None or event.xdata is None or event.ydata is None:
                return
            x0, y0 = self.smith_zoom_start
            x1, y1 = float(event.xdata), float(event.ydata)
            self.smith_zoom_rect.set_x(min(x0, x1))
            self.smith_zoom_rect.set_y(min(y0, y1))
            self.smith_zoom_rect.set_width(abs(x1 - x0))
            self.smith_zoom_rect.set_height(abs(y1 - y0))
            self.smith_canvas.draw_idle()
            return

        if not _MATPLOTLIB_OK or self.smith_scatter is None or event.inaxes is None:
            return

        contains, info = self.smith_scatter.contains(event)
        indices = info.get("ind") if contains else []
        if indices is None or len(indices) == 0:
            self.smith_hover_label.setText("Hover a point to see impedance and C1/C2 position.")
            return

        index = int(indices[0])
        if index < 0 or index >= len(self.smith_plot_points):
            self.smith_hover_label.setText("Hover a point to see impedance and C1/C2 position.")
            return

        point = self.smith_plot_points[index]
        gamma_value = self.smith_plot_values[index]
        self.smith_hover_label.setText(self._format_smith_hover_text(point, gamma_value))

    def plot_dz_resolution(self):
        if not _MATPLOTLIB_OK:
            QMessageBox.warning(
                self, "Missing Library",
                "matplotlib is required.\nInstall with:  pip install matplotlib"
            )
            return

        if self.df_all is None or self.df_all.empty:
            QMessageBox.warning(self, "No Data", "Please convert data before plotting.")
            return

        thresholds = self._get_dz_thresholds(show_message=True)
        if thresholds is None:
            return
        good_threshold, poor_threshold = thresholds

        heatmap_range = self._get_dz_heatmap_range()

        horizontal, vertical, x_values, y_values = build_delta_impedance_plot_data(self.df_all)
        horizontal_finite = horizontal[np.isfinite(horizontal)]
        vertical_finite = vertical[np.isfinite(vertical)]

        if horizontal_finite.size == 0 and vertical_finite.size == 0:
            QMessageBox.warning(self, "No Data", "No delta-impedance values were available to plot.")
            return

        h_min = horizontal_finite.min() if horizontal_finite.size else 0.0
        h_avg = horizontal_finite.mean() if horizontal_finite.size else 0.0
        h_max = horizontal_finite.max() if horizontal_finite.size else 0.0
        v_min = vertical_finite.min() if vertical_finite.size else 0.0
        v_avg = vertical_finite.mean() if vertical_finite.size else 0.0
        v_max = vertical_finite.max() if vertical_finite.size else 0.0

        heatmap_data = np.minimum(horizontal, vertical)
        heat_finite = heatmap_data[np.isfinite(heatmap_data)]
        heat_min = heat_finite.min() if heat_finite.size else 0.0
        heat_avg = heat_finite.mean() if heat_finite.size else 0.0
        heat_max = heat_finite.max() if heat_finite.size else 0.0

        self.dz_status_label.setText(
            f"Horizontal |ΔZ|: min {h_min:.4g} Ω, avg {h_avg:.4g} Ω, max {h_max:.4g} Ω | "
            f"Vertical |ΔZ|: min {v_min:.4g} Ω, avg {v_avg:.4g} Ω, max {v_max:.4g} Ω | "
            f"Heatmap min(H,V): min {heat_min:.4g} Ω, avg {heat_avg:.4g} Ω, max {heat_max:.4g} Ω"
        )

        self._draw_dz_plots(horizontal, vertical, heatmap_data, x_values, y_values,
                            good_threshold, poor_threshold, heatmap_range)

    def _get_dz_heatmap_range(self):
        """Return (vmin, vmax) for the heatmap colour scale, or None if inputs are invalid."""
        try:
            vmin = float(self.dz_heatmap_min_edit.text().strip() or "0")
            vmax = float(self.dz_heatmap_max_edit.text().strip() or "0")
        except ValueError:
            return None
        if vmin < 0 or vmax <= 0 or vmin >= vmax:
            return None
        return vmin, vmax

    def _draw_dz_plots(self, horizontal, vertical, heatmap_data, x_values, y_values,
                       good_threshold, poor_threshold, heatmap_range=None):
        self.dz_figure.clear()

        cmap = _get_cmap("RdYlGn_r")
        norm = Normalize(vmin=good_threshold, vmax=poor_threshold, clip=True)

        gs = self.dz_figure.add_gridspec(1, 3, wspace=0.28, left=0.04, right=0.97, top=0.9, bottom=0.08)
        ax_left = self.dz_figure.add_subplot(gs[0, 0])
        ax_right = self.dz_figure.add_subplot(gs[0, 1])
        ax_heat = self.dz_figure.add_subplot(gs[0, 2])

        left_im = ax_left.imshow(
            horizontal,
            aspect="auto",
            origin="lower",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
            extent=[0, len(x_values), 0, len(y_values)],
        )
        ax_right.imshow(
            vertical,
            aspect="auto",
            origin="lower",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
            extent=[0, len(x_values), 0, len(y_values)],
        )

        ax_left.set_title("Horizontal |ΔZ|", fontsize=11, fontweight="bold")
        ax_right.set_title("Vertical |ΔZ|", fontsize=11, fontweight="bold")
        for axis in (ax_left, ax_right):
            axis.set_xlabel("C1 Position (0 - 447)", fontsize=9)
            axis.set_ylabel("C2 Position (0 - 447)", fontsize=9)
            axis.tick_params(labelsize=8)
            for boundary in range(64, max(len(x_values), len(y_values)), 64):
                axis.axvline(boundary, color="white", linewidth=0.35, alpha=0.5)
                axis.axhline(boundary, color="white", linewidth=0.35, alpha=0.5)

        colorbar = self.dz_figure.colorbar(left_im, ax=[ax_left, ax_right], pad=0.02)
        colorbar.set_label("|ΔZ| (ohms)", fontsize=9)

        # Heatmap: min(horizontal, vertical) — best achievable resolution at each point
        if heatmap_range is not None:
            heat_vmin, heat_vmax = heatmap_range
        else:
            heat_vmin, heat_vmax = good_threshold, poor_threshold
        heat_norm = Normalize(vmin=heat_vmin, vmax=heat_vmax, clip=True)
        heat_im = ax_heat.imshow(
            heatmap_data,
            aspect="auto",
            origin="lower",
            cmap=cmap,
            norm=heat_norm,
            interpolation="nearest",
            extent=[0, len(x_values), 0, len(y_values)],
        )
        ax_heat.set_title("Heatmap: min(H, V) |ΔZ|", fontsize=11, fontweight="bold")
        ax_heat.set_xlabel("C1 Position (0 - 447)", fontsize=9)
        ax_heat.set_ylabel("C2 Position (0 - 447)", fontsize=9)
        ax_heat.tick_params(labelsize=8)
        for boundary in range(64, max(len(x_values), len(y_values)), 64):
            ax_heat.axvline(boundary, color="white", linewidth=0.35, alpha=0.5)
            ax_heat.axhline(boundary, color="white", linewidth=0.35, alpha=0.5)
        heat_cb = self.dz_figure.colorbar(heat_im, ax=ax_heat, pad=0.02)
        heat_cb.set_label(f"|ΔZ| (ohms)  [{heat_vmin:g} – {heat_vmax:g}]", fontsize=9)

        self.dz_figure.suptitle(
            f"Delta impedance resolution map  (green <= {good_threshold:g}, red >= {poor_threshold:g})",
            fontsize=12,
            fontweight="bold",
        )
        self.dz_canvas.draw()

    def placeholder_text(self, name):
        return (
            f"{name} will be added in step 2.\n\n"
            "For now, feature 1 provides the display table and X-Y table."
        )

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select raw data file",
            "",
            "Data Files (*.txt *.csv *.dat *.s2p *.log);;All Files (*)"
        )

        if file_path:
            self.file_path_edit.setText(file_path)

    def browse_cable_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select cable S-parameter file",
            "",
            "Data Files (*.csv *.txt *.dat *.s2p *.log);;All Files (*)"
        )
        if file_path:
            self.cable_file_path_edit.setText(file_path)

    def convert_file(self):
        file_path = self.file_path_edit.text().strip()
        cable_file_path = self.cable_file_path_edit.text().strip()

        if not file_path:
            QMessageBox.warning(self, "No File", "Please select a raw data file first.")
            return

        if not os.path.exists(file_path):
            QMessageBox.critical(self, "File Error", "The selected file does not exist.")
            return

        if cable_file_path and not os.path.exists(cable_file_path):
            QMessageBox.critical(self, "Cable File Error", "The selected cable file does not exist.")
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.df_all = parse_match_file(file_path)
            cable_s_parameters, cable_source = load_cable_s_parameters(cable_file_path)
            self.df_all = deembed_s_parameters(self.df_all, cable_s_parameters)
            self.current_cable_source = cable_source
            self.df_display = self.df_all.head(5000).copy()
            self.refresh_display_table()
            self.refresh_xy_table()
            self.refresh_phase_table()
            self.refresh_contour_table()
            self.refresh_impedance_table()
            self.refresh_zl_table()
            self.refresh_zpar_table()
            self.refresh_abcd_table()
            self.refresh_dz_table()
            self.refresh_reflection_table()
            self.refresh_efficiency_table()
            self.refresh_iout_table()
            self.refresh_vpp_table()
            self.refresh_phi_out_table()
            self.smith_search_result = None
            self.zl_search_result_label.setText("ZL search result will appear here.")
            self.refresh_smith_chart()

            total_rows = len(self.df_all)
            frequency_min = self.df_all["Frequency"].min()
            frequency_max = self.df_all["Frequency"].max()

            x_min = self.df_all["X_C1"].min()
            x_max = self.df_all["X_C1"].max()
            y_min = self.df_all["Y_C2"].min()
            y_max = self.df_all["Y_C2"].max()

            self.total_rows_label.setText(f"Total rows: {total_rows:,}")

            if frequency_min == frequency_max:
                self.frequency_label.setText(f"Frequency: {frequency_min:.6g} Hz")
            else:
                self.frequency_label.setText(
                    f"Frequency: {frequency_min:.6g} ~ {frequency_max:.6g} Hz"
                )

            self.x_range_label.setText(f"X_C1 range: {x_min} ~ {x_max}")
            self.y_range_label.setText(f"Y_C2 range: {y_min} ~ {y_max}")
            self.display_label.setText(
                f"Display: {len(self.df_display):,} / {total_rows:,} rows"
            )

            QApplication.restoreOverrideCursor()

            QMessageBox.information(
                self,
                "Convert Finished",
                f"Successfully converted {total_rows:,} rows.\n\n"
                f"Cable de-embed source: {self.current_cable_source}\n"
                f"X-Y tab uses {self.current_xy_parameter}.\n"
                f"Phase tab uses {self.current_phase_parameter} at {self.phase_rotation_degrees}°.\n"
                f"Z*out tab uses {self.current_impedance_parameter}.\n"
                f"ZL,Γin=0 tab uses ZL = -Z12·Z21/(50Ω - Z11) - Z22.\n"
                f"dZ tab uses {self.current_dz_parameter}.\n"
                f"Reflect Coefficient tab uses {self.current_reflection_parameter} {self.current_reflection_mode}.\n"
                f"Efficiency tab uses {self.efficiency_mode_combo.currentText()}.\n"
                f"Iout tab uses {self.iout_formula_combo.currentText()}, Pin = {self.input_power_watts:.4g} W, Zin = 50Ω.\n"
                f"Vpp tab uses Pin = {self.vpp_power_watts:.4g} W, Zin = 50Ω.\n"
                f"Contour tab uses {self.current_contour_parameter}.\n"
                f"Zpar tab uses {self.current_zpar_parameter}.\n"
                f"ABCD Matrix tab uses {self.current_abcd_parameter}.\n"
                f"Smith Chart uses {self.current_smith_parameter}."
            )

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Convert Failed", str(e))

    def export_csv(self):
        if self.df_all is None or self.df_all.empty:
            QMessageBox.warning(self, "No Data", "Please convert data before exporting.")
            return

        input_path = self.file_path_edit.text().strip()
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        current_tab = self.tabs.tabText(self.tabs.currentIndex())

        if current_tab == "Z*out" and self.df_impedance_display is not None:
            default_name = base_name + f"_{self.current_impedance_parameter.lower()}_zout_table.csv"
        elif current_tab == "ZL,Γin=0" and self.df_zl_display is not None:
            default_name = base_name + "_zl_gin0_table.csv"
        elif current_tab == "Zpar" and self.df_zpar_display is not None:
            default_name = base_name + f"_{self.current_zpar_parameter.lower()}_zpar_table.csv"
        elif current_tab == "ABCD Matrix" and self.df_abcd_display is not None:
            default_name = base_name + f"_{self.current_abcd_parameter.lower()}_abcd_matrix_table.csv"
        elif current_tab == "dZ" and self.df_dz_display is not None:
            default_name = base_name + f"_{self.current_dz_parameter.lower().replace(' ', '_')}_dz_table.csv"
        elif current_tab == "Reflect Coefficient" and self.df_reflection_display is not None:
            default_name = (
                base_name
                + f"_{self.current_reflection_parameter.lower()}_{self.current_reflection_mode}_reflect_coefficient_table.csv"
            )
        elif current_tab == "Efficiency" and self.df_efficiency_display is not None:
            efficiency_suffix = self.current_efficiency_mode
            default_name = base_name + f"_{efficiency_suffix}_efficiency_table.csv"
        elif current_tab == "Iout" and self.df_iout_display is not None:
            default_name = base_name + f"_pin_{self.input_power_watts:.4g}w_iout_table.csv"
        elif current_tab == "Vpp" and self.df_vpp_display is not None:
            default_name = base_name + f"_pin_{self.vpp_power_watts:.4g}w_vpp_table.csv"
        elif current_tab == "Phase Magnitude" and self.df_phase_display is not None:
            default_name = base_name + f"_{self.current_phase_parameter.lower()}_{self.phase_rotation_degrees}deg_phase_table.csv"
        elif current_tab == "Contour" and self.df_contour_display is not None:
            default_name = base_name + f"_{self.current_contour_parameter.lower()}_contour_table.csv"
        else:
            default_name = base_name + f"_{self.current_xy_parameter.lower()}_xy_table.csv"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {current_tab} Table",
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not save_path:
            return

        try:
            if current_tab == "Z*out" and self.df_impedance_display is not None:
                self.df_impedance_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "ZL,Γin=0" and self.df_zl_display is not None:
                self.df_zl_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Zpar" and self.df_zpar_display is not None:
                self.df_zpar_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "ABCD Matrix" and self.df_abcd_display is not None:
                self.df_abcd_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "dZ" and self.df_dz_display is not None:
                self.df_dz_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Reflect Coefficient" and self.df_reflection_display is not None:
                self.df_reflection_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Efficiency" and self.df_efficiency_display is not None:
                self.df_efficiency_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Iout" and self.df_iout_display is not None:
                self.df_iout_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Vpp" and self.df_vpp_display is not None:
                self.df_vpp_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Phase Magnitude" and self.df_phase_display is not None:
                self.df_phase_display.to_csv(save_path, index=False, header=False)
            elif current_tab == "Contour" and self.df_contour_display is not None:
                self.df_contour_display.to_csv(save_path, index=False, header=False)
            elif self.df_xy_display is not None:
                self.df_xy_display.to_csv(save_path, index=False, header=False)
            else:
                self.df_all.to_csv(save_path, index=False)
            QMessageBox.information(
                self,
                "Export Finished",
                f"CSV exported successfully:\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ASM.Palantir")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app_icon = load_app_icon()
    app.setWindowIcon(app_icon)

    app.setStyleSheet("""
        QMainWindow {
            background-color: #ECEFF1;
        }
        QMessageBox {
            font-size: 14px;
        }
    """)

    def startup_status(message, progress=None):
        startup_splash.set_status(message, progress)
        app.processEvents()

    startup_splash = StartupSplash()
    startup_splash.setWindowIcon(app_icon)
    startup_splash.show()
    app.processEvents()

    startup_timer = QElapsedTimer()
    startup_timer.start()
    startup_status("Loading numerical libraries...", 5)
    load_runtime_libraries()
    startup_status("Building main window...", 35)
    window = MatchResolutionGui(startup_status_callback=startup_status)
    window.setWindowIcon(app_icon)

    remaining_ms = 10000 - int(startup_timer.elapsed())
    if remaining_ms > 0:
        wait_loop = QEventLoop()
        QTimer.singleShot(remaining_ms, wait_loop.quit)
        wait_loop.exec()

    startup_status("Opening main window...", 100)
    startup_splash.close()
    window.show()

    sys.exit(app.exec())