# MatchResolution.py 完整程式碼說明（繁體中文）

---

## 一、整體架構概覽

```
程式啟動
   │
   ├── 全域常數與延遲載入變數
   ├── 工具函式（純計算，無 UI）
   │     ├── 檔案解析
   │     ├── 矩陣轉換（S ↔ T）
   │     ├── Cable 去嵌入
   │     └── 各分頁數據建表
   ├── Qt 資料模型（PandasTableModel、ManualImpedanceTableModel）
   ├── MatchResolutionGui（主視窗，所有 UI 與互動邏輯）
   └── if __name__ == "__main__"（啟動進入點）
```

---

## 二、第 1 區段：匯入與全域常數（行 1–73）

```python
from PySide6.QtWidgets import ...   # Qt 視窗元件
EXPECTED_S_COLUMNS = [...]          # S 參數欄位名稱
REQUIRED_TABLE_COLUMNS = [...]      # CSV 必要欄位
FULL_GRID_ROWS = 7 * 64 * 7 * 64   # 完整格點數 = 200,704
REDUCED_GRID_ROWS = 7 * 8 * 7 * 8  # 縮減格點數 = 3,136
DEFAULT_Z0 = 50.0                   # 標準阻抗 50 Ω
```

**重點說明：**
- C1、C2 各有 **7 個粗調（coarse）× 64 個細調（fine）= 448 個位置**
- 位置索引公式：`X_C1 = C1_coarse × 64 + C1_fine`（0 到 447）
- S 參數以實部 `_r` 和虛部 `_x` 分開儲存

---

## 三、第 2 區段：延遲載入函式（行 75–116）

```python
np = None  # numpy，啟動時先不載入
pd = None  # pandas

def load_runtime_libraries():
    # 在 splash 畫面顯示後才載入，避免啟動卡頓
    import numpy, pandas, matplotlib ...
    _MATPLOTLIB_OK = True  # 若 matplotlib 不存在則 False

def app_base_path():
    # EXE 模式回傳 sys._MEIPASS（PyInstaller 解壓縮目錄）
    # Python 模式回傳腳本所在目錄

def load_app_icon():
    # 載入 smithchart.ico 作為應用程式圖示
```

**除錯提示：** 若圖表無法顯示，檢查 `_MATPLOTLIB_OK` 是否為 `True`。

---

## 四、第 3 區段：S ↔ T 矩陣轉換與 Cable 去嵌入（行 260–374）

### S → T 轉換

```python
def _complex_to_t_matrix(s11, s21, s12, s22, context):
    # T 矩陣用來串接兩段網路
    # 公式：T = [[-det/S21, S11/S21], [-S22/S21, 1/S21]]
    # 若 S21 ≈ 0 會拋出例外（除以零保護）
```

### T → S 轉換

```python
def _t_matrix_to_s_parameters(t_matrix, context):
    # 反向轉換，若 T22 ≈ 0 拋出例外
```

### Cable 去嵌入流程

```python
def deembed_s_parameters(df, cable_s_parameters):
    # 對每一筆資料列：
    # 1. 測量值 S → T_measured
    # 2. 計算 T_cable1_inv、T_cable2_inv
    # 3. T_final = inv(T_cable1) × T_measured × inv(T_cable2)
    # 4. T_final → S，存回 DataFrame
```

**除錯提示：** 若去嵌入後 S 參數異常（例如 |S11| > 1），先確認 cable 檔案的 S21 不為零，且矩陣可逆。

---

## 五、第 4 區段：CMD 指令解析（行 377–421）

```python
def parse_cmd_line(cmd_line):
    # 輸入範例："caps hf 3 15 2 8"
    # 解析：C1_coarse=3, C1_fine=15, C2_coarse=2, C2_fine=8
    # 計算：X_C1 = 3×64 + 15 = 207
    #        Y_C2 = 2×64 + 8  = 136
    # 支援含 "ps1" 的舊格式（從最後 4 個 token 取值）
```

**除錯提示：** 若解析失敗，確認 CMD 欄位格式為 `caps hf x1 x2 x3 x4` 或 `caps hf ps1 x1 x2 x3 x4`。

---

## 六、第 5 區段：檔案解析（行 445–550、1708–1828）

```python
def parse_full_row(tokens):
    # 格式 A：單行，例如
    # "1.29E+07 caps hf 0 0 0 0 0.13 -0.25 ..."
    # 前面是頻率+CMD，最後 8 個 token 是 S11r S11x ... S22x

def parse_vertical_block(lines, start_index):
    # 格式 B：直式區塊，每個值各佔一行
    # 行0: 頻率, 行1: CMD, 行2~9: S 參數

def find_header_row(file_path):
    # 掃描找出含 "Frequency CMD S11_r" 的標題行

def parse_match_file(file_path):
    # 主解析器，依序嘗試：
    # 1. CSV/TSV 格式（pandas 讀取）
    # 2. 格式 A（單行）
    # 3. 格式 B（直式區塊）
```

---

## 七、第 6 區段：數據表建構函式（行 553–964）

```python
def build_table_from_dataframe(raw_df):
    # 將原始 DataFrame 轉換為標準化格式
    # 計算 X_C1、Y_C2，排序後加入 X_Label、Y_Label

def finalize_table(df):
    # 強制欄位順序，依 X_C1、Y_C2 排序

def build_xy_display_table(df, parameter_name):
    # 建立 X-Y 展示表格
    # 列標題：C2 coarse / C2 fine / 百分比
    # 行標題：C1 coarse / C1 fine / 百分比
    # 格內容：S 參數複數值（例如 "0.13-0.25i"）

def build_zpar_display_table(df, parameter_name):
    # 由 S 參數轉成 Z11 / Z21 / Z12 / Z22，建立 Zpar 分頁資料

def build_abcd_display_table(df, parameter_name):
    # 先 S → Z，再 Z → ABCD，建立 A / B / C / D 分頁資料
```

**表格結構示意：**

```
         C1:  0%    10%   20%  ...
C2:  0%  [S值] [S值] [S值] ...
C2: 10%  [S值] [S值] [S值] ...
```

---

## 八、第 7 區段：阻抗與 ΔZ 計算（行 965–1211）

```python
def reflect_to_impedance_value(s_r, s_x, z0=50):
    # Γ → Z 轉換公式：Z = Z0 × (1+Γ)/(1-Γ)
    # 若分母 ≈ 0（Γ = 1，開路）回傳 None

def build_impedance_matrix(df, parameter_name):
    # 建立複數阻抗矩陣 shape=(ny, nx)

def build_delta_impedance_plot_data(df):
    # 計算 |ΔZ|：
    # horizontal[row, col] = |Z[row,col] - Z[row,col-1]|  (沿 C1 方向)
    # vertical[row, col]   = |Z[row,col] - Z[row-1,col]|  (沿 C2 方向)
```

---

## 九、第 8 區段：反射係數 ΔΓ 計算（行 1214–1302）

```python
def build_reflection_coefficient_matrix(df, parameter_name):
    # 建立 |Γ| 純量矩陣，abs(complex(S_r, S_x))

def build_delta_reflection_plot_data(df, parameter_name):
    # 計算兩個方向的差值矩陣：
    # horizontal[row, col] = |Γ|[row,col] - |Γ|[row,col-1]  (ΔC1)
    # vertical[row, col]   = |Γ|[row,col] - |Γ|[row-1,col]  (ΔC2)
    # 兩個矩陣同時回傳，供 heatmap 使用

def build_reflection_display_table(df, parameter_name, orientation):
    # 依選擇的方向（horizontal/vertical）建立展示表格
```

---

## 十、第 9 區段：效率計算（行 1303–1458）

```python
def calculate_efficiency_value(s11, s21, s12, s22, efficiency_mode):
    # mode = "abcd_power"：
    #   1. 用 conjugate(S22) 當負載反射係數
    #   2. 轉成 ZL
    #   3. S → Z → ABCD
    #   4. 假設 IL = 1 Arms，算 V2、V1、I1、Zin、PL、Pin
    #   5. 效率 = PL / Pin
    #
    # mode = "h_squared"：|S21|²·(1−|S22|²) / |1−S22²|²
    # mode = "s21_squared"：效率 = |S21|²
    # mode = "overall"：效率 = (1 - |S11|²) × |S21|²

def build_efficiency_display_table(df, efficiency_mode):
    # 依所選公式建立 Efficiency 分頁表格
    # 格內容：效率數值（0 到 1）
```

---

## 十一、第 10 區段：Smith 圖相關函式（行 1461–1707）

```python
def build_smith_chart_plot_data(df, parameter_name):
    # 每個格點的 Γ 複數值 → 準備繪圖散點

def draw_smith_chart_grid(ax):
    # 繪製 Smith 圖背景：
    # - 等阻抗圓（R = 0, 0.2, 0.5, 1, 2, 5）
    # - 等電抗弧（X = ±0.2, ±0.5, ±1, ±2, ±5）
    # - 單位圓邊框

def build_smith_dz_lookup(df):
    # 建立 (X_C1, Y_C2) → max(|ΔZ_H|, |ΔZ_V|) 查找表
    # Smith 圖 dZ 模式著色用

def build_smith_dgamma_lookup(df, parameter_name, orientation):
    # 建立 (X_C1, Y_C2) → |ΔΓ| 查找表
    # Smith 圖 dΓ 模式著色用

def build_smith_efficiency_lookup(df):
    # 建立 (X_C1, Y_C2) → efficiency 查找表
    # Smith 圖 Efficiency 模式著色用

def calculate_cap_array(coarse_step_pf, fine_caps_pf):
    # 計算 448 個位置的等效電容值（pF）
    # 粗調：coarse_index × coarse_step
    # 細調：6 位元二進位加權（Fine1=LSB, Fine6=MSB）
```

---

## 十二、第 11 區段：Qt 資料模型（行 1830–1984）

### PandasTableModel

```python
# 將 pandas DataFrame 橋接到 Qt QTableView
def data(index, role):
    # DisplayRole   → 顯示格內文字
    # BackgroundRole → 欄位顏色：
    #   X_C1 → 淺藍 #E3F2FD
    #   Y_C2 → 淺綠 #E8F5E9
    #   S11* → 淺橙 #FFF3E0
    #   S22* → 淺粉 #FCE4EC
    # TextAlignmentRole → 置中
```

### ManualImpedanceTableModel

```python
# Smith 圖手動輸入點（R, X）的可編輯表格模型
# 支援新增列、清空、以及 iter_points() 遍歷有效點
```

**除錯提示：** 若表格顯示空白，確認傳入的 DataFrame 不是空的，且欄位名稱正確。

---

## 十三、第 12 區段：主視窗 MatchResolutionGui（行 1985–5274）

這是整個程式最大的類別，負責 **所有 UI 佈局與用戶互動**。

### 初始化（`__init__`）

```python
# 建立所有狀態變數（df_all, df_xy_display, current_xy_parameter...）
# 呼叫各子區段建構 UI
# 將信號（signal）連接到槽（slot）
```

### UI 佈局結構

```
QMainWindow
  └── 主 Widget
        ├── 頂部標題列（漸層紫色）
        ├── 檔案輸入列（File / Cable Browse）
        ├── 統計資訊列（Total rows / Frequency / X_C1 / Y_C2 / Display）
        └── QTabWidget（各分頁）
              ├── Display（原始轉換資料表）
              ├── X-Y Table（參數矩陣網格）
              ├── Phase Magnitude（幅度/相位）
              ├── Contour（邊緣格點）
              ├── Impedance（阻抗 Z）
              ├── Zpar（Z11 / Z21 / Z12 / Z22）
              ├── ABCD Matrix（A / B / C / D）
              ├── dZ（阻抗差分）
              ├── Smith Chart（Smith 圖）
              ├── Component（電容計算）
              ├── Reflect Coefficient（ΔΓ）
              └── Efficiency（效率）
```

### 核心流程：Convert 按鈕

```python
def on_convert_clicked():
    # 1. parse_match_file()        → 解析原始檔案
    # 2. load_cable_s_parameters() → 載入 cable
    # 3. deembed_s_parameters()    → 去嵌入
    # 4. 呼叫所有 refresh_*()       → 更新各分頁
    # 5. 更新統計資訊列
```

### 各分頁的 refresh 函式

| 函式 | 作用 |
|------|------|
| `refresh_display_table()` | 更新 Display 原始表格 |
| `refresh_xy_table()` | 重建 X-Y 矩陣，連接格點點擊事件 |
| `refresh_phase_table()` | 重建相位/幅度表格 |
| `refresh_contour_table()` | 重建邊緣格點表格 |
| `refresh_impedance_table()` | 重建阻抗表格 |
| `refresh_zpar_table()` | 重建 Zpar 表格 |
| `refresh_abcd_table()` | 重建 ABCD Matrix 表格 |
| `refresh_dz_table()` | 重建 ΔZ 表格，自動觸發繪圖 |
| `refresh_reflection_table()` | 重建 ΔΓ 表格，自動觸發 heatmap |
| `refresh_efficiency_table()` | 重建效率表格 |
| `refresh_smith_chart()` | 重繪 Smith 圖 |

### Smith 圖繪製邏輯

```python
def _draw_smith_chart(points, parameter_name):
    # 1. draw_smith_chart_grid() 畫背景格線
    # 2. 依 current_smith_mode 決定著色方式：
    #    "xy"        → 依 C1/C2 位置顏色漸層
    #    "dz"        → 依 dz_lookup 值著色（RdYlGn_r）
    #    "dgamma"    → 依 dgamma_lookup 值著色
    #    "efficiency"→ 依 efficiency_lookup 值著色（YlGn）
    #    "contour"   → 只畫邊緣格點
    #    "pm"        → P/M 模式（粉/藍 兩色）
    # 3. hover 事件顯示阻抗/位置資訊
```

### Reflect Coefficient Heatmap（雙圖並排）

```python
def _draw_reflection_plot(h_mag, v_mag, x_values, y_values, ...):
    # add_subplot(1,2,1) → 左圖：Horizontal |ΔΓ|（ΔC1 方向）
    # add_subplot(1,2,2) → 右圖：Vertical   |ΔΓ|（ΔC2 方向）
    # 顏色：RdYlGn_r（綠=小差異好，紅=大差異差）
    # tight_layout() 自動調整間距
```

---

## 十四、第 13 區段：程式啟動進入點（行 5276–5321）

```python
if __name__ == "__main__":
    # 1. Windows：設定 AppUserModelID（讓工作列顯示正確圖示）
    # 2. QApplication 建立，設定全域圖示（smithchart.ico）
    # 3. 顯示 StartupSplash（進度條啟動畫面）
    # 4. load_runtime_libraries()（載入 numpy/pandas/matplotlib）
    # 5. MatchResolutionGui() 建立主視窗
    # 6. 等待總啟動時間達 10 秒（確保 splash 至少顯示夠久）
    # 7. 關閉 splash，顯示主視窗
    # 8. sys.exit(app.exec())（進入 Qt 事件迴圈）
```

---

## 十五、除錯速查表

| 問題 | 要檢查的位置 |
|------|-------------|
| 檔案解析失敗 | `parse_match_file()` → 確認 CMD 格式與欄位名稱 |
| 去嵌入後數值異常 | `deembed_s_parameters()` → 確認 cable S21 ≠ 0 |
| 表格空白 | `refresh_*()` → 確認 `df_all` 不為空，欄位存在 |
| Smith 圖不顯示 | `_MATPLOTLIB_OK` 是否為 `True` |
| Heatmap 無色差 | 確認 good/poor 閾值範圍合理（good < poor） |
| 圖示不顯示 | 確認 `smithchart.ico` 存在於 `app_base_path()` 目錄 |
| EXE 找不到 VERSION | PyInstaller 需含 `--add-data "VERSION;."` |
