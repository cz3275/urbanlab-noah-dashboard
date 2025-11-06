# NYC Housing Data Explorer - 项目完整理解文档

## 目录
1. [项目概述](#项目概述)
2. [整体架构](#整体架构)
3. [数据库设计](#数据库设计)
4. [核心模块详解](#核心模块详解)
5. [业务逻辑流程](#业务逻辑流程)
6. [数据同步机制](#数据同步机制)
7. [前端交互设计](#前端交互设计)
8. [最新功能：ZIP Code联动](#最新功能zip-code联动)

---

## 项目概述

### 项目简介
这是一个基于Streamlit开发的纽约市房屋数据可视化分析平台，提供交互式地图、统计分析和高级数据洞察功能。

### 核心功能
1. 交互式地图展示：支持多种图层和样式
2. 数据统计分析：包括租金、收入、空置率等指标
3. 建筑信息展示：PLUTO数据库建筑详情
4. 自动数据同步：定时从API获取最新数据
5. ZIP Code联动：点击地图自动更新图表数据

### 数据来源
- **Census ACS 2022**: 美国人口普查局社区调查数据
- **NYC PLUTO**: 纽约市土地使用税务数据
- **NYC Open Data**: 纽约市开放数据平台

### 技术栈
- **后端框架**: Streamlit 1.31.0
- **地图可视化**: Folium 0.14.0
- **图表可视化**: Plotly 5.18.0
- **数据库**: SQLAlchemy 2.0.25 + SQLite/PostgreSQL
- **数据处理**: Pandas 2.1.4
- **任务调度**: Schedule 1.2.1

---

## 整体架构

### 项目结构
```
NewNycHouseApp/
├── app.py                      # 主应用入口，定义页面布局和逻辑
├── init_db.py                  # 数据库初始化脚本
├── requirements.txt            # 项目依赖
├── README.md                   # 项目说明
├── DATABASE_SETUP.md          # 数据库设置指南
├── components/                 # UI组件模块
│   ├── __init__.py
│   ├── map_layers.py          # 地图图层管理（标记、热力图、标签）
│   ├── sidebar.py             # 侧边栏控制面板
│   └── statistics.py          # 统计图表面板
├── services/                   # 业务逻辑服务层
│   ├── __init__.py
│   ├── data_service.py        # 数据查询服务
│   ├── data_sync.py           # 数据同步服务（API）
│   └── auto_sync.py           # 自动同步管理器
├── models/                     # 数据模型层
│   ├── __init__.py
│   └── housing_data.py        # SQLAlchemy ORM模型定义
├── config/                     # 配置模块
│   ├── __init__.py
│   └── database.py            # 数据库配置和连接
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── map_utils.py           # 地图工具函数（已废弃）
│   └── zip_coords.py          # ZIP坐标数据
└── data/                       # 数据目录
    ├── nyc_housing.db         # SQLite数据库文件
    ├── auto_sync_config.json  # 自动同步配置
    ├── update_data.py         # 数据更新脚本
    ├── fetch_pluto_residential.py  # PLUTO数据获取
    └── *.csv                  # 原始CSV数据文件
```

### 架构分层

```
┌─────────────────────────────────────────────────┐
│           用户界面层 (Streamlit UI)              │
│  app.py + components (sidebar, map, stats)     │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              业务逻辑层 (Services)               │
│  data_service, data_sync, auto_sync            │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           数据访问层 (ORM Models)                │
│  SQLAlchemy Models (HousingMetrics, etc.)      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│            数据存储层 (Database)                 │
│       SQLite / PostgreSQL                       │
└─────────────────────────────────────────────────┘
```

---

## 数据库设计

### 数据库配置
位置：`config/database.py`

支持两种数据库：
1. **SQLite** (默认)：`data/nyc_housing.db`
2. **PostgreSQL**：通过环境变量配置

```python
# 数据库类型选择
DB_TYPE = os.getenv("DB_TYPE", " ")  # 空格表示使用SQLite

# SQLite配置
DB_PATH = BASE_DIR / "data" / "nyc_housing.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# PostgreSQL配置（需设置环境变量）
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
```

### 数据库表结构

#### 1. zip_codes（ZIP代码表）
存储纽约市所有有效的ZIP代码列表。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 主键 | Primary Key, Auto Increment |
| zip | String(5) | ZIP代码 | Unique, Index, Not Null |
| created_at | DateTime | 创建时间 | 自动生成 |
| updated_at | DateTime | 更新时间 | 自动更新 |

**数据来源**: NYC Open Data Modified ZCTA Boundaries API

#### 2. housing_metrics（房屋指标表）
存储每个ZIP区域的房屋统计数据（来自Census ACS）。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 主键 | Primary Key |
| zip | String(5) | ZIP代码 | Index, Not Null |
| name | String(100) | 区域名称 | - |
| median_rent | Float | 中位数租金（美元/月） | - |
| median_income | Float | 中位数收入（美元/年） | - |
| rent_burden | Float | 租金负担（百分比） | - |
| housing_units | Integer | 房屋单元总数 | - |
| total_units | Integer | 总单元数（包括商业） | - |
| occupied_units | Integer | 已占用单元数 | - |
| vacant_units | Integer | 空置单元数 | - |
| vacancy_rate | Float | 空置率（小数） | - |
| created_at | DateTime | 创建时间 | 自动生成 |
| updated_at | DateTime | 更新时间 | 自动更新 |

**数据来源**: Census Bureau ACS 5-Year 2022
**关键指标计算**:
- `vacancy_rate = vacant_units / total_units`
- `rent_burden`: 租金占收入的百分比

#### 3. building_info（建筑信息表）
存储每栋建筑的详细信息（来自NYC PLUTO）。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 主键 | Primary Key |
| bbl | String(20) | 建筑块批次编号 | Unique, Index, Not Null |
| landuse | String(10) | 土地使用代码 | - |
| yearbuilt | Integer | 建造年份 | - |
| numfloors | Integer | 楼层数 | - |
| unitsres | Integer | 住宅单元数 | - |
| address | String(200) | 地址 | - |
| zipcode | String(5) | ZIP代码 | Index |
| borough | String(50) | 行政区 | - |
| created_at | DateTime | 创建时间 | 自动生成 |
| updated_at | DateTime | 更新时间 | 自动更新 |

**数据来源**: NYC PLUTO (Primary Land Use Tax Lot Output)
**landuse代码**: 01=单户, 02=双户, 03=多户住宅

#### 4. building_stats（建筑统计表）
每个ZIP区域的建筑聚合统计数据（从building_info计算得出）。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 主键 | Primary Key |
| zip | String(5) | ZIP代码 | Unique, Index, Not Null |
| total_buildings | Integer | 建筑总数 | - |
| avg_floors | Float | 平均楼层数 | - |
| avg_year_built | Integer | 平均建造年份 | - |
| total_residential_units | Integer | 住宅单元总数 | - |
| buildings_pre_1950 | Integer | 1950年前建筑数 | - |
| buildings_1950_2000 | Integer | 1950-2000年建筑数 | - |
| buildings_post_2000 | Integer | 2000年后建筑数 | - |
| created_at | DateTime | 创建时间 | 自动生成 |
| updated_at | DateTime | 更新时间 | 自动更新 |

**计算逻辑**: 在`data_sync.py`的`calculate_building_stats()`方法中自动计算

#### 5. sync_logs（同步日志表）
记录所有数据同步操作的历史。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 主键 | Primary Key |
| sync_type | String(50) | 同步类型 | Not Null |
| status | String(20) | 同步状态 | Not Null |
| records_processed | Integer | 处理记录数 | Default 0 |
| error_message | Text | 错误信息 | - |
| sync_time | DateTime | 同步时间 | 自动生成 |

**sync_type类型**:
- `nyc_zip_list`: ZIP列表同步
- `full_sync`: 完整Census数据同步
- `pluto_sync`: PLUTO数据同步
- `csv_load`: CSV文件加载
- `pluto_csv_load`: PLUTO CSV加载

**status状态**: `success`, `failed`

### 数据库关系图

```
┌──────────────┐
│  zip_codes   │
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────────┐         ┌──────────────────┐
│ housing_metrics  │         │ building_stats   │
│ (Census ACS)     │         │ (Aggregated)     │
└──────────────────┘         └──────────────────┘
                                      ▲
                                      │ Calculated From
                                      │
                             ┌────────┴─────────┐
                             │  building_info   │
                             │  (PLUTO Data)    │
                             └──────────────────┘

                ┌──────────────┐
                │  sync_logs   │
                │ (Audit Trail)│
                └──────────────┘
```

### 索引策略
- `zip_codes.zip`: Unique Index（确保唯一性）
- `housing_metrics.zip`: Index（加速ZIP查询）
- `building_info.bbl`: Unique Index（建筑唯一标识）
- `building_info.zipcode`: Index（加速按ZIP筛选）
- `building_stats.zip`: Unique Index（每个ZIP一条记录）

---

## 核心模块详解

### 1. 主应用模块 (app.py)

#### 主要功能
- 定义Streamlit页面配置和布局
- 协调各组件之间的交互
- 处理用户操作和状态管理
- 实现ZIP Code联动功能

#### 核心代码结构

```python
# 页面配置
st.set_page_config(
    page_title="NYC Housing Data Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化
@st.cache_resource
def initialize_database():
    init_db()

@st.cache_resource
def get_auto_sync_manager():
    return AutoSyncManager()

# 数据过滤
def apply_filters(df, filters):
    # 应用ZIP搜索、值范围等过滤条件
    pass

# 主函数
def main():
    # 1. 初始化服务
    data_service = DataService()
    sidebar = SidebarManager()
    map_manager = MapLayerManager()
    stats_panel = StatisticsPanel()
    
    # 2. 渲染侧边栏控件
    layer_config = sidebar.render_layer_controls()
    appearance_config = sidebar.render_map_appearance()
    filter_config = sidebar.render_data_filters()
    
    # 3. 处理数据同步
    action = sidebar.render_sync_controls()
    if action == "sync_all":
        # 执行同步逻辑
    
    # 4. 获取和过滤数据
    df = data_service.get_all_metrics()
    filtered_df = apply_filters(df, filter_config)
    
    # 5. 初始化选中的ZIP Code
    if "selected_zip" not in st.session_state:
        st.session_state["selected_zip"] = filtered_df.iloc[0]["zip"]
    
    # 6. 渲染三个Tab页
    tab1, tab2, tab3 = st.tabs(["Map View", "Analytics", "Advanced Analysis"])
    
    # Tab1: 地图视图（捕获点击事件）
    # Tab2: 统计分析（基于选中ZIP）
    # Tab3: 高级分析（基于选中ZIP）
```

#### Session State管理
- `selected_zip`: 当前选中的ZIP Code
- `primary_metric`: 主要显示指标
- `year_filter_min/max`: 建筑年份过滤范围
- 其他控件状态由Streamlit自动管理

### 2. 数据服务模块 (services/data_service.py)

#### 类: DataService
负责所有数据库查询操作。

**核心方法**:

```python
class DataService:
    def __init__(self):
        self.db = SessionLocal()  # 创建数据库会话
    
    def get_all_metrics(self) -> pd.DataFrame:
        """获取所有ZIP的房屋指标"""
        # 查询housing_metrics表
        # 返回DataFrame格式
    
    def get_metrics_by_zip(self, zip_code: str) -> dict:
        """获取指定ZIP的房屋指标"""
        # 单个ZIP查询
    
    def get_all_building_stats(self) -> pd.DataFrame:
        """获取所有ZIP的建筑统计"""
        # 查询building_stats表
    
    def get_buildings_by_zip(self, zip_code: str, limit: int = 100) -> pd.DataFrame:
        """获取指定ZIP的建筑列表"""
        # 查询building_info表
    
    def get_buildings_by_zip_filtered(self, zip_code: str, 
                                     year_min: int, 
                                     year_max: int, 
                                     limit: int = 100) -> pd.DataFrame:
        """获取指定ZIP和年份范围的建筑列表"""
        # 带年份过滤的建筑查询
    
    def get_combined_metrics(self, zip_code: str) -> dict:
        """获取指定ZIP的综合数据（房屋+建筑）"""
        # 合并多表数据
```

**数据处理**:
- 自动将numpy类型转换为Python原生类型
- 处理None/NaN值
- 统一ZIP代码格式（5位数字，前导零）

### 3. 数据同步模块 (services/data_sync.py)

#### 类: DataSyncService
负责从外部API获取数据并同步到数据库。

**核心方法**:

```python
class DataSyncService:
    def fetch_nyc_zip_list(self):
        """从NYC Open Data获取ZIP列表"""
        # API: https://data.cityofnewyork.us/resource/pri4-ifjk.json
        # 更新zip_codes表
    
    def census_fetch(self, vars_, rename_map):
        """从Census API获取指定变量"""
        # API: https://api.census.gov/data/2022/acs/acs5
        # 参数: 变量代码，ZIP Code范围
    
    def sync_all_data(self):
        """同步所有Census数据"""
        # 1. 获取ZIP列表
        # 2. 获取租金数据 (B25064_001E)
        # 3. 获取收入数据 (B19013_001E)
        # 4. 获取租金负担 (B25070_001E)
        # 5. 获取房屋单元 (B25001_001E)
        # 6. 获取空置数据 (B25002_001E/002E/003E)
        # 7. 合并所有数据
        # 8. 过滤NYC ZIP
        # 9. 批量插入housing_metrics表
    
    def fetch_pluto_residential(self, year_min, year_max, limit):
        """从NYC PLUTO API获取住宅建筑数据"""
        # API: https://data.cityofnewyork.us/resource/64uk-42ks.json
        # 分页获取（每页5000条）
        # 过滤条件: landuse in (01, 02, 03)
    
    def sync_pluto_data(self, year_min=1900, year_max=2025, limit=100000):
        """同步PLUTO数据"""
        # 1. 调用fetch_pluto_residential
        # 2. 清空building_info表
        # 3. 批量插入新数据
        # 4. 调用calculate_building_stats()
    
    def calculate_building_stats(self):
        """计算建筑统计数据"""
        # 1. 从building_info读取所有数据
        # 2. 按ZIP分组
        # 3. 计算各项统计指标
        # 4. 插入building_stats表
```

**Census API变量说明**:
- `B25064_001E`: Median Gross Rent
- `B19013_001E`: Median Household Income
- `B25070_001E`: Gross Rent as Percentage of Household Income
- `B25001_001E`: Housing Units
- `B25002_001E`: Total Occupancy
- `B25002_002E`: Occupied Units
- `B25002_003E`: Vacant Units

**PLUTO API参数**:
- `$select`: 选择字段
- `$where`: 过滤条件
- `$order`: 排序
- `$limit`: 每页数量
- `$offset`: 分页偏移

### 4. 自动同步模块 (services/auto_sync.py)

#### 类: AutoSyncManager
管理自动数据同步任务。

**配置文件**: `data/auto_sync_config.json`
```json
{
  "enabled": false,
  "interval_hours": 24,
  "last_sync": null,
  "sync_census": true,
  "sync_pluto": false
}
```

**核心方法**:

```python
class AutoSyncManager:
    def load_config(self):
        """从JSON文件加载配置"""
    
    def save_config(self):
        """保存配置到JSON文件"""
    
    def update_config(self, enabled, interval_hours, sync_census, sync_pluto):
        """更新配置"""
    
    def should_sync(self):
        """判断是否需要同步"""
        # 检查enabled状态
        # 计算时间间隔
    
    def perform_sync(self):
        """执行同步操作"""
        # 根据配置同步Census和/或PLUTO
        # 更新last_sync时间
        # 返回同步结果
    
    def check_and_sync(self):
        """检查并执行同步（手动触发）"""
    
    def start_auto_sync(self):
        """启动后台定时同步线程"""
        # 使用schedule库
        # 创建daemon线程
    
    def stop_auto_sync(self):
        """停止自动同步"""
    
    def get_next_sync_time(self):
        """计算下次同步时间"""
    
    def get_status(self):
        """获取同步状态信息"""
```

**工作原理**:
1. 使用Python `schedule`库定时任务
2. 在独立线程中运行（daemon=True）
3. 每分钟检查一次pending任务
4. 记录同步结果到配置文件

### 5. 地图组件模块 (components/map_layers.py)

#### 类: MapLayerManager
管理Folium地图的各种图层。

**核心方法**:

```python
class MapLayerManager:
    def create_base_map(self, tiles="CartoDB positron"):
        """创建基础地图"""
        # 中心点: NYC_CENTER [40.7128, -73.75]
        # 缩放级别: 10
    
    def add_marker_layer(self, map_obj, data, coords_dict, metric_column, 
                        color_scheme, opacity, building_stats, data_service):
        """添加标记图层"""
        # CircleMarker标记
        # 颜色根据指标值计算
        # Popup包含详细信息（3个Tab）
    
    def add_heatmap_layer(self, map_obj, data, coords_dict, metric_column):
        """添加热力图图层"""
        # 使用folium.plugins.HeatMap
        # 根据指标值生成热力数据
    
    def add_label_layer(self, map_obj, data, coords_dict):
        """添加ZIP标签图层"""
        # 使用folium.DivIcon
        # 在地图上显示ZIP代码
    
    def add_legend(self, map_obj, metric_column, color_scheme):
        """添加图例"""
        # HTML图例，固定在地图右下角
    
    def _get_marker_color(self, value, metric_column, color_scheme):
        """根据值计算标记颜色"""
        # 归一化值到0-1范围
        # 映射到颜色方案
    
    def _create_popup_html(self, row, zip_code, building_stats, data_service):
        """创建Popup HTML（3个Tab）"""
        # Tab1: Housing（房屋指标）
        # Tab2: Building Stats（建筑统计）
        # Tab3: Buildings（建筑列表）
        # JavaScript实现Tab切换
```

**Popup HTML结构**:
```html
<div style="...">
    <div class="tabs">
        <div class="tab active" onclick="switchTab('housing', this)">Housing</div>
        <div class="tab" onclick="switchTab('building-stats', this)">Building Stats</div>
        <div class="tab" onclick="switchTab('building-list', this)">Buildings</div>
    </div>
    
    <div class="tab-content active" id="housing">
        <!-- 房屋指标表格 -->
    </div>
    
    <div class="tab-content" id="building-stats">
        <!-- 建筑统计表格 -->
    </div>
    
    <div class="tab-content" id="building-list">
        <!-- 建筑列表表格 -->
    </div>
</div>
```

**颜色方案**:
- `YlOrRd`: 黄-橙-红（默认）
- `Blues`: 蓝色系
- `Greens`: 绿色系
- `Viridis`: Viridis渐变
- `Plasma`: Plasma渐变

### 6. 侧边栏组件 (components/sidebar.py)

#### 类: SidebarManager
渲染和管理所有侧边栏控件。

**核心方法**:

```python
class SidebarManager:
    def render_layer_controls(self):
        """渲染图层控制"""
        # 指标选择下拉框
        # 显示数据点复选框
        # 显示热力图复选框
        # 显示ZIP标签复选框
        # 返回配置字典
    
    def render_map_appearance(self):
        """渲染地图外观设置"""
        # 颜色方案选择
        # 地图样式选择
        # 透明度滑块
        # 返回配置字典
    
    def render_data_filters(self, metric):
        """渲染数据过滤器"""
        # ZIP搜索文本框
        # 值范围过滤滑块（根据指标动态）
        # 行政区多选
        # 建筑年份过滤
        # 返回配置字典
    
    def render_analysis_options(self):
        """渲染分析工具选项"""
        # 显示统计面板
        # 显示相关性矩阵
        # 对比模式
        # 返回配置字典
    
    def render_sync_controls(self, data_service, auto_sync_manager):
        """渲染数据同步控制"""
        # 手动同步按钮（Census、PLUTO、全部）
        # 自动同步设置
        # 同步历史显示
        # 返回操作类型或None
```

**过滤器动态范围**:
- median_rent: $0-$5000
- median_income: $0-$300,000
- vacancy_rate: 0.0-1.0
- rent_burden: 0%-100%
- housing_units: 0-50,000

### 7. 统计面板组件 (components/statistics.py)

#### 类: StatisticsPanel
渲染各种统计图表和分析。

**通用方法**（用于全局数据）:

```python
def render_summary_metrics(self, df):
    """渲染摘要指标卡片"""
    # 5个st.metric显示关键指标
    
def render_distribution_chart(self, df, metric_column):
    """渲染分布直方图"""
    # plotly.express.histogram
    
def render_top_bottom_charts(self, df, metric_column, n=10):
    """渲染Top/Bottom排行榜"""
    # 两列布局，柱状图
    
def render_correlation_matrix(self, df):
    """渲染相关性矩阵热力图"""
    # plotly.express.imshow
    
def render_comparison_charts(self, df, metric1, metric2):
    """渲染双指标对比散点图"""
    # plotly.express.scatter
    
def render_rent_burden_analysis(self, df):
    """渲染租金负担分析"""
    # 饼图 + 柱状图
```

**ZIP Code专用方法**（用于单个ZIP数据）:

```python
def render_zip_metrics_card(self, zip_row):
    """渲染选中ZIP的指标卡片"""
    # 显示该ZIP的所有关键指标
    
def render_zip_comparison_chart(self, all_df, selected_zip, metric_column):
    """渲染ZIP在全局中的位置对比"""
    # 直方图 + 垂直线标记选中ZIP的位置
    
def render_zip_detailed_metrics(self, zip_row, all_df):
    """渲染ZIP详细指标对比"""
    # 分组柱状图：选中ZIP vs 平均值
    
def render_building_stats_detailed(self, building_row):
    """渲染建筑统计详情"""
    # 指标卡片 + 年代分布柱状图
    
def render_zip_rank_analysis(self, all_df, selected_zip):
    """渲染排名分析"""
    # 计算各指标排名和百分位
    # 进度条显示
    
def render_multi_zip_comparison(self, all_df, selected_zip, n=5):
    """渲染多ZIP对比"""
    # 找出最相似的n个ZIP
    # 柱状图对比
```

---

## 业务逻辑流程

### 1. 应用启动流程

```
用户访问 → Streamlit启动
    ↓
初始化数据库 (initialize_database)
    ↓
创建自动同步管理器 (get_auto_sync_manager)
    ↓
创建服务实例
    ├─ DataService
    ├─ SidebarManager
    ├─ MapLayerManager
    └─ StatisticsPanel
    ↓
渲染侧边栏控件
    ↓
获取数据并过滤
    ↓
初始化selected_zip (第一个ZIP)
    ↓
渲染三个Tab页
```

### 2. 数据同步流程

#### 手动同步Census数据
```
用户点击"Sync Census" → sidebar返回"sync_census"
    ↓
显示spinner
    ↓
创建DataSyncService实例
    ↓
调用sync_all_data()
    ├─ fetch_nyc_zip_list() → 获取177个NYC ZIP
    ├─ census_fetch() × 5次 → 获取5类数据
    │   ├─ 租金 (B25064_001E)
    │   ├─ 收入 (B19013_001E)
    │   ├─ 租金负担 (B25070_001E)
    │   ├─ 房屋单元 (B25001_001E)
    │   └─ 空置数据 (B25002_001E/002E/003E)
    ├─ 合并所有DataFrame
    ├─ 过滤NYC ZIP
    ├─ 数据清理和验证
    └─ 批量插入housing_metrics表
    ↓
记录sync_logs
    ↓
显示成功消息
    ↓
st.rerun() → 刷新页面
```

#### 手动同步PLUTO数据
```
用户点击"Sync PLUTO" → sidebar返回"sync_pluto"
    ↓
显示spinner（可能需要数分钟）
    ↓
创建DataSyncService实例
    ↓
调用sync_pluto_data()
    ├─ fetch_pluto_residential()
    │   ├─ 构造API查询参数
    │   │   ├─ $select: bbl,landuse,yearbuilt,numfloors,unitsres,address,zipcode,borough
    │   │   ├─ $where: landuse in('01','02','03')
    │   │   ├─ $order: yearbuilt DESC
    │   │   └─ $limit: 5000 (分页)
    │   ├─ 循环获取所有页（最多100,000条）
    │   │   ├─ 发送HTTP请求
    │   │   ├─ 解析JSON
    │   │   ├─ 转换为DataFrame
    │   │   └─ sleep(0.15秒) → 避免API限流
    │   └─ 合并所有DataFrame
    ├─ 清空building_info表
    ├─ 批量插入新数据
    └─ calculate_building_stats()
        ├─ 从building_info读取
        ├─ 按zipcode分组
        ├─ 计算每个ZIP的统计指标
        │   ├─ total_buildings
        │   ├─ avg_floors
        │   ├─ avg_year_built
        │   ├─ total_residential_units
        │   ├─ buildings_pre_1950
        │   ├─ buildings_1950_2000
        │   └─ buildings_post_2000
        └─ 插入building_stats表
    ↓
记录sync_logs
    ↓
显示成功消息
    ↓
st.rerun()
```

#### 自动同步流程
```
用户启用自动同步 → AutoSyncManager.update_config(enabled=True)
    ↓
调用start_auto_sync()
    ├─ 清空schedule
    ├─ 设置定时任务（根据interval_hours）
    ├─ 创建daemon线程
    └─ 启动run_scheduler()
        └─ 每分钟检查pending任务
            ↓
        到达同步时间
            ↓
        perform_sync()
            ├─ 根据sync_census配置同步Census
            ├─ 根据sync_pluto配置同步PLUTO
            ├─ 更新last_sync时间
            └─ 保存配置
```

### 3. 地图交互流程

#### 地图渲染
```
获取filtered_df
    ↓
创建base_map (Folium.Map)
    ↓
根据layer_config添加图层
    ├─ show_markers=True → add_marker_layer()
    │   └─ 为每个ZIP创建CircleMarker
    │       ├─ 计算颜色（基于指标值）
    │       ├─ 创建Popup HTML（3个Tab）
    │       └─ 添加到地图
    ├─ show_heatmap=True → add_heatmap_layer()
    │   └─ 创建HeatMap插件
    └─ show_labels=True → add_label_layer()
        └─ 为每个ZIP创建DivIcon标签
    ↓
add_legend() → 添加图例
    ↓
st_folium() → 渲染地图（返回map_output）
```

#### ZIP Code点击联动（新功能）
```
用户点击地图标记
    ↓
st_folium返回last_object_clicked
    ↓
获取clicked_lat和clicked_lng
    ↓
遍历NYC_ZIP_COORDS计算距离
    ↓
找到最近的ZIP Code
    ↓
比较与session_state["selected_zip"]
    ↓
如果不同
    ├─ 更新session_state["selected_zip"]
    └─ st.rerun() → 触发页面刷新
        ↓
    Tab2和Tab3根据新的selected_zip重新渲染
```

### 4. Tab页渲染流程

#### Tab1: Map View（地图视图）
```
显示"Geographic Distribution"标题
    ↓
显示过滤后的ZIP数量
    ↓
创建并渲染地图（见上文）
    ↓
捕获点击事件并更新selected_zip
    ↓
显示地图使用说明（expander）
```

#### Tab2: Analytics（统计分析）
```
获取session_state["selected_zip"]
    ↓
从filtered_df筛选该ZIP的数据
    ↓
显示提示信息："Displaying data for ZIP Code: xxxxx"
    ↓
两列布局
    ├─ 左列: render_zip_metrics_card()
    │   └─ 显示该ZIP的5个关键指标
    └─ 右列: render_zip_comparison_chart()
        └─ 该ZIP在所有ZIP中的位置分布
    ↓
分割线
    ↓
render_zip_detailed_metrics()
    └─ 详细指标对比（选中ZIP vs 平均值）
```

#### Tab3: Advanced Analysis（高级分析）
```
获取session_state["selected_zip"]
    ↓
从filtered_df筛选该ZIP的数据
    ↓
显示提示信息："Displaying advanced analysis for ZIP Code: xxxxx"
    ↓
两列布局（3:2比例）
    ├─ 左列: render_building_stats_detailed()
    │   ├─ 建筑统计指标卡片
    │   └─ 年代分布柱状图
    └─ 右列: render_zip_rank_analysis()
        └─ 各指标的排名和百分位
    ↓
分割线
    ↓
"ZIP Code Comparison"标题
    ↓
render_multi_zip_comparison()
    ├─ 找出最相似的5个ZIP
    └─ 柱状图对比租金
```

### 5. 数据过滤流程

```
用户设置过滤条件（侧边栏）
    ├─ zip_search: "10001"
    ├─ enable_range: True
    ├─ rent_range: ($1000, $3000)
    ├─ borough_filter: ["Manhattan"]
    └─ year_range: (1950, 2000)
    ↓
sidebar返回filter_config字典
    ↓
apply_filters(df, filter_config)
    ├─ 应用ZIP搜索（包含匹配）
    │   df = df[df["zip"].str.contains("10001")]
    ├─ 应用值范围过滤
    │   df = df[(df["median_rent"] >= 1000) & (df["median_rent"] <= 3000)]
    └─ 行政区过滤（暂未实现）
    ↓
返回filtered_df
    ↓
年份过滤单独处理
    ├─ 保存到session_state
    └─ 在get_buildings_by_zip_filtered中使用
```

---

## 数据同步机制

### Census API集成

#### API端点
```
https://api.census.gov/data/2022/acs/acs5
```

#### 请求参数
```python
params = {
    "get": "NAME,B25064_001E",  # 获取的变量
    "for": "zip code tabulation area:*",  # 所有ZIP
}
```

#### 响应格式
```json
[
    ["NAME", "B25064_001E", "zip code tabulation area"],
    ["ZCTA5 10001", "2500", "10001"],
    ["ZCTA5 10002", "1800", "10002"]
]
```

#### 数据处理
1. 转换为DataFrame
2. 重命名列名
3. 提取ZIP代码（填充5位）
4. 过滤NYC ZIP（仅保留177个）
5. 合并多个数据集

### PLUTO API集成

#### API端点
```
https://data.cityofnewyork.us/resource/64uk-42ks.json
```

#### 请求参数
```python
params = {
    "$select": "bbl,landuse,yearbuilt,numfloors,unitsres,address,zipcode,borough",
    "$where": "landuse in('01','02','03')",
    "$order": "yearbuilt DESC",
    "$limit": 5000,
    "$offset": 0
}
```

#### 分页策略
- 每页5000条记录
- 循环获取直到无数据或达到limit
- 每次请求间隔0.15秒（避免限流）
- 最多获取100,000条

#### API Token（可选）
```python
headers = {"X-App-Token": os.getenv("SOCRATA_APP_TOKEN")}
```

好处：
- 提高请求限额
- 更快的响应速度
- 更稳定的服务

获取方式：https://data.cityofnewyork.us/profile/app_tokens

### 数据验证和清理

#### Census数据验证
```python
# 负值处理
if median_rent < 0:
    median_rent = None

if median_income < 0:
    median_income = None

# 范围验证
if rent_burden < 0 or rent_burden > 100:
    rent_burden = None

# 类型转换
median_rent = pd.to_numeric(row.get("median_rent"), errors="coerce")
```

#### PLUTO数据验证
```python
# ZIP代码格式化
zipcode_val = row.get("zipcode")
if pd.notna(zipcode_val):
    try:
        zipcode_str = str(int(float(zipcode_val))).zfill(5)
    except:
        zipcode_str = str(zipcode_val).zfill(5)
```

#### Numpy类型转换
```python
def convert_to_native_type(val):
    """将numpy类型转换为Python原生类型（兼容PostgreSQL）"""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    return val
```

### 同步日志

每次同步操作都会记录到`sync_logs`表：

```python
log = SyncLog(
    sync_type="full_sync",  # 同步类型
    status="success",       # 状态
    records_processed=177,  # 处理记录数
    error_message=None,     # 错误信息（如有）
    sync_time=datetime.now()  # 同步时间
)
```

可通过`DataService.get_last_sync_info()`查询最近同步记录。

---

## 前端交互设计

### Streamlit组件架构

```
app.py (主入口)
    │
    ├─ st.sidebar (侧边栏)
    │   └─ SidebarManager
    │       ├─ render_layer_controls()
    │       ├─ render_map_appearance()
    │       ├─ render_data_filters()
    │       ├─ render_analysis_options()
    │       └─ render_sync_controls()
    │
    └─ st.tabs (主内容区)
        ├─ Tab1: Map View
        │   └─ st_folium (Folium地图)
        │       └─ MapLayerManager
        │
        ├─ Tab2: Analytics
        │   └─ StatisticsPanel (ZIP专用图表)
        │
        └─ Tab3: Advanced Analysis
            └─ StatisticsPanel (ZIP专用图表)
```

### 状态管理

#### Session State变量
```python
st.session_state = {
    "selected_zip": "10001",           # 当前选中的ZIP
    "primary_metric": "median_rent",   # 主要指标
    "show_markers": True,              # 显示标记
    "show_heatmap": False,             # 显示热力图
    "show_labels": False,              # 显示标签
    "color_scheme": "YlOrRd",         # 颜色方案
    "map_style": "CartoDB positron",  # 地图样式
    "opacity": 0.7,                   # 透明度
    "zip_search": "",                 # ZIP搜索
    "enable_range": False,            # 启用范围过滤
    "enable_year_filter": False,      # 启用年份过滤
    "year_filter_min": None,          # 年份最小值
    "year_filter_max": None,          # 年份最大值
    "show_stats": True,               # 显示统计
    "show_corr": False,               # 显示相关性
    "compare_mode": False,            # 对比模式
    # ... 其他控件状态
}
```

#### 状态更新触发重渲染
```python
# 用户操作 → 控件状态改变 → session_state更新 → Streamlit重新执行脚本
if clicked_zip != st.session_state.get("selected_zip"):
    st.session_state["selected_zip"] = clicked_zip
    st.rerun()  # 触发重新渲染
```

### 缓存策略

#### 资源缓存
```python
@st.cache_resource
def initialize_database():
    """数据库初始化只执行一次"""
    init_db()

@st.cache_resource
def get_auto_sync_manager():
    """自动同步管理器单例"""
    return AutoSyncManager()
```

#### 数据缓存
Streamlit会自动缓存没有变化的数据：
- DataFrame在脚本重新执行时不会重新查询（除非数据源变化）
- 组件返回值会被缓存

### Folium地图集成

#### st_folium参数
```python
map_output = st_folium(
    base_map,                              # Folium地图对象
    width=None,                            # 宽度（None=自适应）
    height=800,                            # 高度（像素）
    returned_objects=["last_object_clicked"]  # 返回点击对象
)
```

#### 返回值结构
```python
map_output = {
    "last_object_clicked": {
        "lat": 40.7506,
        "lng": -73.9971
    },
    # ... 其他地图交互数据
}
```

### Plotly图表

#### 通用配置
```python
fig.update_layout(
    height=400,                    # 高度
    margin=dict(l=20, r=20, t=40, b=20),  # 边距
    showlegend=True,               # 显示图例
    title="Chart Title"            # 标题
)

st.plotly_chart(fig, use_container_width=True)  # 自适应宽度
```

#### 图表类型
- `px.histogram`: 直方图（分布）
- `px.bar`: 柱状图（排行）
- `px.scatter`: 散点图（相关性）
- `px.imshow`: 热力图（相关性矩阵）
- `px.pie`: 饼图（分类）
- `go.Figure`: 自定义图表

---

## 最新功能：ZIP Code联动

### 功能概述
点击地图上的ZIP Code标记后，Tab2和Tab3的所有图表会自动更新，显示该ZIP Code的详细数据。

### 实现原理

#### 1. 初始化选中ZIP
```python
# app.py
if "selected_zip" not in st.session_state:
    if not filtered_df.empty:
        st.session_state["selected_zip"] = filtered_df.iloc[0]["zip"]
    else:
        st.session_state["selected_zip"] = None
```

默认选择数据库中第一个ZIP Code。

#### 2. 捕获地图点击事件
```python
# app.py - Tab1
map_output = st_folium(base_map, width=None, height=800, 
                      returned_objects=["last_object_clicked"])

if map_output and map_output.get("last_object_clicked"):
    clicked_lat = map_output["last_object_clicked"].get("lat")
    clicked_lng = map_output["last_object_clicked"].get("lng")
```

使用`st_folium`的`returned_objects`参数捕获点击事件。

#### 3. 计算最近ZIP Code
```python
if clicked_lat and clicked_lng:
    min_dist = float('inf')
    clicked_zip = None
    
    # 遍历所有ZIP坐标
    for zip_code, coords in NYC_ZIP_COORDS.items():
        # 计算欧氏距离
        dist = ((coords[0] - clicked_lat) ** 2 + (coords[1] - clicked_lng) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            clicked_zip = zip_code
```

通过欧氏距离找到离点击位置最近的ZIP Code。

#### 4. 更新状态并刷新
```python
if clicked_zip and clicked_zip != st.session_state.get("selected_zip"):
    st.session_state["selected_zip"] = clicked_zip
    st.rerun()  # 触发页面重新渲染
```

如果点击的ZIP与当前选中的不同，更新状态并重新渲染。

#### 5. Tab2渲染逻辑
```python
# app.py - Tab2
with tab2:
    st.subheader("Statistical Analysis")
    
    selected_zip = st.session_state.get("selected_zip")
    if selected_zip:
        # 从filtered_df筛选该ZIP的数据
        selected_df = filtered_df[filtered_df["zip"] == selected_zip]
        
        if not selected_df.empty:
            st.info(f"Displaying data for ZIP Code: {selected_zip}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 显示ZIP指标卡片
                stats_panel.render_zip_metrics_card(selected_df.iloc[0])
            
            with col2:
                # 显示ZIP在全局中的位置
                stats_panel.render_zip_comparison_chart(
                    filtered_df, selected_zip, layer_config["metric"]
                )
            
            st.divider()
            
            # 详细指标对比
            if "median_rent" in selected_df.columns and "median_income" in selected_df.columns:
                stats_panel.render_zip_detailed_metrics(
                    selected_df.iloc[0], filtered_df
                )
```

#### 6. Tab3渲染逻辑
```python
# app.py - Tab3
with tab3:
    st.subheader("Advanced Analysis")
    
    selected_zip = st.session_state.get("selected_zip")
    if selected_zip:
        selected_df = filtered_df[filtered_df["zip"] == selected_zip]
        
        if not selected_df.empty:
            st.info(f"Displaying advanced analysis for ZIP Code: {selected_zip}")
            
            col1, col2 = st.columns([3, 2])

            with col1:
                # 显示建筑统计
                if not building_stats_df.empty:
                    selected_building_stats = building_stats_df[
                        building_stats_df["zip"] == selected_zip
                    ]
                    if not selected_building_stats.empty:
                        stats_panel.render_building_stats_detailed(
                            selected_building_stats.iloc[0]
                        )

            with col2:
                # 显示排名分析
                stats_panel.render_zip_rank_analysis(filtered_df, selected_zip)

            st.divider()

            st.subheader("ZIP Code Comparison")
            
            # 多ZIP对比
            stats_panel.render_multi_zip_comparison(filtered_df, selected_zip, n=5)
```

### 新增图表方法

#### 1. render_zip_metrics_card
显示选中ZIP的关键指标卡片。

```python
def render_zip_metrics_card(self, zip_row):
    st.markdown("### Selected ZIP Code Metrics")
    st.markdown(f"**ZIP Code: {zip_code}**")
    
    # 3列显示：租金、收入、租金负担
    # 2列显示：空置率、房屋单元
    # 使用st.metric组件
```

#### 2. render_zip_comparison_chart
显示ZIP在所有ZIP中的分布位置。

```python
def render_zip_comparison_chart(self, all_df, selected_zip, metric_column):
    # 创建直方图显示所有ZIP的分布
    # 添加垂直线标记选中ZIP的位置
    # 使用go.Figure + add_vline
```

#### 3. render_zip_detailed_metrics
详细指标对比（选中ZIP vs 平均值）。

```python
def render_zip_detailed_metrics(self, zip_row, all_df):
    # 对比4个指标：租金、收入、空置率、租金负担
    # 分组柱状图：选中ZIP vs 平均值
    # 使用go.Figure + add_trace
```

#### 4. render_building_stats_detailed
建筑统计详情。

```python
def render_building_stats_detailed(self, building_row):
    # 3个指标卡片：总建筑数、平均楼层、平均年份
    # 年代分布柱状图：Pre-1950、1950-2000、Post-2000
```

#### 5. render_zip_rank_analysis
各指标的排名分析。

```python
def render_zip_rank_analysis(self, all_df, selected_zip):
    # 计算租金、收入、空置率的排名
    # 显示排名、总数、百分位
    # 使用st.progress显示百分位进度条
```

#### 6. render_multi_zip_comparison
与相似ZIP对比。

```python
def render_multi_zip_comparison(self, all_df, selected_zip, n=5):
    # 基于租金差异找出最相似的n个ZIP
    # 柱状图对比租金（高亮选中ZIP）
    # 使用不同颜色区分Selected vs Similar
```

### 交互流程图

```
用户打开应用
    ↓
显示第一个ZIP的数据（默认）
    ↓
用户点击地图上的ZIP标记
    ↓
st_folium捕获点击坐标
    ↓
计算最近的ZIP Code
    ↓
更新session_state["selected_zip"]
    ↓
st.rerun() 触发重新渲染
    ↓
Tab2和Tab3根据新ZIP重新查询数据
    ↓
所有图表同步更新
```

### 关键技术点

#### 1. 坐标距离计算
```python
# 欧氏距离公式
dist = sqrt((lat1 - lat2)^2 + (lng1 - lng2)^2)

# Python实现
dist = ((coords[0] - clicked_lat) ** 2 + (coords[1] - clicked_lng) ** 2) ** 0.5
```

#### 2. 数据过滤
```python
# 从全局DataFrame筛选单个ZIP
selected_df = filtered_df[filtered_df["zip"] == selected_zip]

# 获取第一行数据（ZIP是唯一的）
zip_row = selected_df.iloc[0]
```

#### 3. 状态同步
```python
# 检查状态是否变化
if clicked_zip != st.session_state.get("selected_zip"):
    # 更新状态
    st.session_state["selected_zip"] = clicked_zip
    # 触发重新渲染
    st.rerun()
```

#### 4. 条件渲染
```python
selected_zip = st.session_state.get("selected_zip")
if selected_zip:
    selected_df = filtered_df[filtered_df["zip"] == selected_zip]
    
    if not selected_df.empty:
        # 渲染图表
        pass
    else:
        st.warning(f"No data available for ZIP Code: {selected_zip}")
else:
    st.warning("No ZIP Code selected")
```

### 性能优化

#### 1. 避免重复计算
- 使用`session_state`缓存选中的ZIP
- 只在ZIP改变时重新查询数据

#### 2. 数据预加载
- 在主函数中一次性加载所有数据
- 各Tab页只进行数据过滤，不重新查询

#### 3. 增量更新
- 只更新changed的状态
- 使用`st.rerun()`精确控制重渲染时机

---

## 附录

### 环境变量

```bash
# 数据库类型（留空使用SQLite）
set DB_TYPE=

# PostgreSQL配置（可选）
set DB_USER=xy
set DB_PASSWORD=123
set DB_HOST=172.17.172.107
set DB_PORT=5432
set DB_NAME=nyc_housing

# Socrata API Token（可选，提高限额）
set SOCRATA_APP_TOKEN=your_token_here
```

### 常用命令

```bash
# 激活环境
conda activate nyc

# 初始化数据库
python init_db.py

# 运行应用
streamlit run app.py

# 更新数据
python data/update_data.py

# 获取PLUTO数据
cd data
python fetch_pluto_residential.py --year-min 1900 --year-max 2025 --limit 100000
```

### 依赖包版本

```txt
streamlit==1.31.0
pandas==2.1.4
numpy==1.26.3
plotly==5.18.0
folium==0.14.0
streamlit-folium==0.16.0
sqlalchemy==2.0.25
requests==2.31.0
schedule==1.2.1
```

### 数据字典

#### Census ACS变量
| 变量代码 | 含义 | 单位 |
|---------|------|------|
| B25064_001E | Median Gross Rent | 美元/月 |
| B19013_001E | Median Household Income | 美元/年 |
| B25070_001E | Gross Rent as % of Income | 百分比 |
| B25001_001E | Housing Units | 数量 |
| B25002_001E | Total Occupancy | 数量 |
| B25002_002E | Occupied Units | 数量 |
| B25002_003E | Vacant Units | 数量 |

#### PLUTO土地使用代码
| 代码 | 含义 |
|------|------|
| 01 | One & Two Family Buildings |
| 02 | Multi-Family Walk-Up Buildings |
| 03 | Multi-Family Elevator Buildings |

### 常见问题

#### 1. 数据库为空
**解决**: 运行`python init_db.py`然后在应用中点击"Sync All Data"

#### 2. API请求失败
**原因**: 网络问题或API限流
**解决**: 
- 检查网络连接
- 设置`SOCRATA_APP_TOKEN`环境变量
- 使用CSV文件加载（`load_from_csv()`）

#### 3. Tab点击不生效
**原因**: Popup HTML的JavaScript问题
**解决**: 使用IIFE（立即执行函数表达式）包装点击处理

#### 4. ZIP Code格式问题
**原因**: PLUTO数据中ZIP可能是浮点数（如11427.0）
**解决**: 使用`str(int(float(zipcode_val))).zfill(5)`统一格式

#### 5. PostgreSQL类型错误
**原因**: numpy类型不兼容PostgreSQL
**解决**: 使用`convert_to_native_type()`转换为Python原生类型

---

## 总结

本项目是一个完整的数据可视化分析平台，涵盖了：

1. **数据采集**: Census API + NYC Open Data API
2. **数据存储**: SQLAlchemy ORM + SQLite/PostgreSQL
3. **数据处理**: Pandas数据清理和转换
4. **数据展示**: Streamlit + Folium + Plotly
5. **自动化**: 定时同步 + 后台任务
6. **交互设计**: ZIP Code联动 + 多Tab布局

关键技术亮点：
- 模块化架构设计
- 完整的数据同步机制
- 丰富的交互功能
- 优雅的错误处理
- 高性能的数据查询

适用场景：
- 房地产市场分析
- 城市规划研究
- 数据可视化教学
- Streamlit应用开发参考

---

**文档版本**: 1.0
**最后更新**: 2025-10-20
**作者**: NYC Housing Data Explorer Team

