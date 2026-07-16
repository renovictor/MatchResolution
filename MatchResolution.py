import os
import re
import sys

import pandas as pd

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QMainWindow,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTableView,
    QMessageBox,
    QFrame,
    QHeaderView,
    QTabWidget,
)


EXPECTED_S_COLUMNS = [
    "S11_r", "S11_x",
    "S21_r", "S21_x",
    "S12_r", "S12_x",
    "S22_r", "S22_x",
]

REQUIRED_TABLE_COLUMNS = ["Frequency", "CMD", *EXPECTED_S_COLUMNS]
XY_PARAMETERS = ["S11", "S21", "S12", "S22"]


def is_float_text(text: str) -> bool:
    try:
        float(text)
        return True
    except Exception:
        return False


def clean_column_name(name: str) -> str:
    return str(name).replace("\ufeff", "").strip()


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


def parse_full_row(tokens):
    """
    Support row format like:

    1.29E+07 caps hf 0 0 0 0 1.31E-01 -2.52E-01 ...

    Total tokens:
        Frequency + caps + hf + 4 position values + 8 S-parameter values
        1 + 2 + 4 + 8 = 15 tokens
    """
    if len(tokens) < 15:
        raise ValueError("Not enough columns for one full row.")

    frequency = float(tokens[0])

    cmd_line = " ".join(tokens[1:7])
    cmd_info = parse_cmd_line(cmd_line)

    s_values = [float(v) for v in tokens[7:15]]

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


def build_table_from_dataframe(raw_df):
    """
    Convert a CSV/TSV-style dataframe into the normalized X-Y table.
    """
    raw_df = raw_df.copy()
    raw_df.columns = [clean_column_name(column) for column in raw_df.columns]

    missing_columns = [column for column in REQUIRED_TABLE_COLUMNS if column not in raw_df.columns]
    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    rows = []
    for record in raw_df.itertuples(index=False):
        frequency = float(getattr(record, "Frequency"))
        cmd_info = parse_cmd_line(str(getattr(record, "CMD")))

        row = {
            "Frequency": frequency,
            **cmd_info,
        }

        for column in EXPECTED_S_COLUMNS:
            row[column] = float(getattr(record, column))

        rows.append(row)

    if not rows:
        raise ValueError("No valid data rows found. Please check file format.")

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


def build_xy_display_table(df, parameter_name):
    """
    Build a spreadsheet-like X-Y table with header rows and headers inside the grid.
    """
    real_col = f"{parameter_name}_r"
    imag_col = f"{parameter_name}_x"

    if real_col not in df.columns or imag_col not in df.columns:
        raise ValueError(f"Missing columns for {parameter_name}.")

    x_max = int(df["X_C1"].max())
    y_max = int(df["Y_C2"].max())
    x_values = list(range(x_max + 1))
    y_values = list(range(y_max + 1))

    if not x_values or not y_values:
        raise ValueError("X-Y table is empty.")

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
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            header_line = None
            for index, line in enumerate(f):
                if index == header_row:
                    header_line = line
                    break

        delimiter = ","
        if header_line is not None and "\t" in header_line and "," not in header_line:
            delimiter = "\t"

        try:
            raw_df = pd.read_csv(
                file_path,
                skiprows=header_row,
                encoding="utf-8-sig",
                sep=delimiter,
                engine="python" if delimiter == "\t" else "c",
            )
            if len(raw_df.columns) > 1:
                return build_table_from_dataframe(raw_df)
        except Exception as exc:
            print(f"Warning: CSV parser failed, falling back to legacy parser. Reason: {exc}")

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


class MatchResolutionGui(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RF Matching Resolution Tool - Step 1: CMD to X-Y Table")
        self.resize(1400, 850)

        self.df_all = None
        self.df_display = None
        self.df_xy_display = None
        self.current_xy_parameter = "S22"

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        title = QLabel("RF Matching Resolution Tool")
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
        file_layout = QHBoxLayout(file_frame)

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

        file_layout.addWidget(QLabel("File:"))
        file_layout.addWidget(self.file_path_edit, stretch=1)
        file_layout.addWidget(browse_button)
        file_layout.addWidget(convert_button)
        file_layout.addWidget(export_button)
        file_layout.addWidget(exit_button)

        main_layout.addWidget(file_frame)

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
        self.xy_tab = self.create_table_page(self.xy_table_view, xy_toolbar)
        self.tabs.addTab(self.xy_tab, "X-Y Table")

        self.component_tab = self.build_tab_page("Component", self.placeholder_text("Component"))
        self.impedance_tab = self.build_tab_page("Impedance", self.placeholder_text("Impedance"))
        self.reflection_tab = self.build_tab_page("Reflect Coefficient", self.placeholder_text("Reflect Coefficient"))
        self.vswr_tab = self.build_tab_page("VSWR", self.placeholder_text("VSWR"))

        self.tabs.addTab(self.component_tab, "Component")
        self.tabs.addTab(self.impedance_tab, "Impedance")
        self.tabs.addTab(self.reflection_tab, "Reflect Coefficient")
        self.tabs.addTab(self.vswr_tab, "VSWR")

        main_layout.addWidget(self.tabs, stretch=1)

        note = QLabel(
            "Note: Display tab shows the converted row table. X-Y Table shows the grid view for the selected S-parameter."
        )
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("font-size: 13px; color: #607D8B; padding: 6px;")
        main_layout.addWidget(note)

        self.setCentralWidget(main_widget)

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

    def create_table_page(self, table_view, toolbar_widget=None):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)

        if toolbar_widget is not None:
            layout.addWidget(toolbar_widget)

        layout.addWidget(table_view, stretch=1)
        return page

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

    def convert_file(self):
        file_path = self.file_path_edit.text().strip()

        if not file_path:
            QMessageBox.warning(self, "No File", "Please select a raw data file first.")
            return

        if not os.path.exists(file_path):
            QMessageBox.critical(self, "File Error", "The selected file does not exist.")
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.df_all = parse_match_file(file_path)
            self.df_display = self.df_all.head(5000).copy()
            self.refresh_display_table()
            self.refresh_xy_table()

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
                f"X-Y tab uses {self.current_xy_parameter}."
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
        if current_tab == "X-Y Table" and self.df_xy_display is not None:
            default_name = base_name + f"_{self.current_xy_parameter.lower()}_xy_table.csv"
        else:
            default_name = base_name + "_display_table.csv"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export X-Y Table",
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not save_path:
            return

        try:
            if current_tab == "X-Y Table" and self.df_xy_display is not None:
                self.df_xy_display.to_csv(save_path, index=False, header=False)
            elif self.df_display is not None:
                self.df_display.to_csv(save_path, index=False)
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
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QMainWindow {
            background-color: #ECEFF1;
        }
        QMessageBox {
            font-size: 14px;
        }
    """)

    window = MatchResolutionGui()
    window.show()

    sys.exit(app.exec())