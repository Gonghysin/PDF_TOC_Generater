# PDF 目录生成器 - 功能优化实施计划

## 项目概述

本文档详细说明了两个新功能的技术设计和实施计划：
1. **结构化 TOC 编辑器** - 替代当前的纯文本编辑器，提供表格化的结构编辑界面
2. **任务历史管理** - 支持查看、编辑和重新导出历史任务

## 一、需求分析

### 1.1 当前系统分析

**现有数据模型**（models.py）：
```python
class TOCEntry:
    title: str      # 目录标题
    page: int       # 页码
    level: int      # 层级（1-5）
```

**当前编辑方式**：
- 使用 `<textarea>` 编辑纯文本
- 文本格式：通过缩进（每层级2个空格）表示层级
- 用户需手动维护格式一致性

**当前任务存储**：
- 内存字典：`tasks_storage: Dict[str, Dict[str, Any]]`
- 服务器重启后数据丢失
- 无法访问历史任务

### 1.2 页码计算逻辑

系统中存在两种页码概念：

1. **书籍页码（Book Page）**：书籍原始印刷的页码
2. **PDF 页码（PDF Page）**：PDF 文件中的实际页码

**转换公式**：
```
pdf_page = book_page + (page_offset - 1)
```

**示例**：
- 书籍正文从第 1 页开始
- PDF 文件中正文从第 10 页开始
- 则 page_offset = 10
- 书籍页码 1 → PDF 页码 10

### 1.3 用户需求

#### 需求 1：结构化 TOC 编辑器

**功能要求**：
- [ ] 表格形式展示 TOC 条目
- [ ] 可编辑字段：
  - 目录标题（title）
  - 层级关系（level：1-5）
  - 书籍页码（book_page）
  - PDF 页码（pdf_page，自动计算或手动修正）
- [ ] 可调整条目顺序（拖拽排序）
- [ ] 支持添加、删除条目
- [ ] 实时预览目录结构
- [ ] 保留纯文本编辑模式（备用）

#### 需求 2：任务历史管理

**功能要求**：
- [ ] 查看所有历史任务列表
- [ ] 每个任务显示：文件名、处理时间、状态
- [ ] 点击任务进入编辑界面
- [ ] 可重新编辑 TOC
- [ ] 可重新生成并覆盖 PDF
- [ ] 可删除历史任务

## 二、技术设计

### 2.1 数据库设计

#### 2.1.1 技术选型

**选择 SQLite**：
- 轻量级，无需额外服务
- 文件存储，易于备份
- Python 内置支持
- 足够支撑中小规模使用

#### 2.1.2 数据库架构

**tasks 表**（存储任务元信息）：
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- 任务ID（UUID）
    filename TEXT NOT NULL,            -- 原始文件名
    pdf_path TEXT NOT NULL,            -- PDF 文件路径
    page_range TEXT,                   -- 页码范围（如 "5-12"）
    page_offset INTEGER DEFAULT 0,     -- 页码偏置
    parallel BOOLEAN DEFAULT FALSE,    -- 是否并行处理
    status TEXT NOT NULL,              -- 状态：pending/processing/completed/failed
    progress INTEGER DEFAULT 0,        -- 进度（0-100）
    message TEXT,                      -- 状态消息
    toc_text TEXT,                     -- TOC 文本格式（兼容性）
    output_path TEXT,                  -- 输出文件路径
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);
```

**toc_entries 表**（存储结构化 TOC 条目）：
```sql
CREATE TABLE toc_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 条目ID
    task_id TEXT NOT NULL,                 -- 关联的任务ID
    title TEXT NOT NULL,                   -- 目录标题
    level INTEGER NOT NULL,                -- 层级（1-5）
    book_page INTEGER NOT NULL,            -- 书籍页码
    pdf_page INTEGER NOT NULL,             -- PDF 页码
    order_index INTEGER NOT NULL,          -- 排序索引
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_task_id ON toc_entries(task_id);
CREATE INDEX idx_order ON toc_entries(task_id, order_index);
```

#### 2.1.3 数据访问层设计

**database.py**（新建文件）：
```python
class DatabaseManager:
    def __init__(self, db_path: str):
        """初始化数据库连接"""

    # 任务管理
    async def create_task(self, task_data: dict) -> str:
        """创建新任务"""

    async def get_task(self, task_id: str) -> dict:
        """获取任务详情"""

    async def update_task(self, task_id: str, updates: dict):
        """更新任务信息"""

    async def list_tasks(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """获取任务列表（分页）"""

    async def delete_task(self, task_id: str):
        """删除任务及其所有 TOC 条目"""

    # TOC 条目管理
    async def save_toc_entries(self, task_id: str, entries: List[TOCEntry]):
        """批量保存 TOC 条目"""

    async def get_toc_entries(self, task_id: str) -> List[TOCEntry]:
        """获取任务的所有 TOC 条目"""

    async def update_toc_entry(self, entry_id: int, updates: dict):
        """更新单个 TOC 条目"""

    async def delete_toc_entry(self, entry_id: int):
        """删除 TOC 条目"""
```

### 2.2 后端 API 设计

#### 2.2.1 新增 API 端点

**任务历史相关**：

```
GET /api/tasks
功能：获取任务列表（分页）
参数：
  - limit (int, optional): 每页数量，默认 50
  - offset (int, optional): 偏移量，默认 0
  - status (str, optional): 过滤状态
响应：
{
  "tasks": [
    {
      "id": "task-uuid",
      "filename": "book.pdf",
      "status": "completed",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T10:45:00"
    }
  ],
  "total": 120,
  "limit": 50,
  "offset": 0
}
```

```
GET /api/tasks/{task_id}
功能：获取任务详情及 TOC 条目
响应：
{
  "task": {
    "id": "task-uuid",
    "filename": "book.pdf",
    "pdf_path": "/path/to/file.pdf",
    "page_offset": 10,
    "status": "completed",
    ...
  },
  "toc_entries": [
    {
      "id": 1,
      "title": "第一章 引言",
      "level": 1,
      "book_page": 1,
      "pdf_page": 10,
      "order_index": 0
    },
    ...
  ]
}
```

```
DELETE /api/tasks/{task_id}
功能：删除任务及其关联数据
响应：
{
  "success": true,
  "message": "任务已删除"
}
```

**TOC 结构化编辑相关**：

```
POST /api/toc/update
功能：批量更新 TOC 条目（结构化数据）
请求体：
{
  "task_id": "task-uuid",
  "entries": [
    {
      "id": 1,  // 已存在的条目有 id，新增的没有
      "title": "第一章 引言",
      "level": 1,
      "book_page": 1,
      "order_index": 0
    },
    {
      "title": "新章节",  // 新增条目
      "level": 1,
      "book_page": 50,
      "order_index": 1
    }
  ],
  "page_offset": 10  // 用于计算 pdf_page
}
响应：
{
  "success": true,
  "message": "TOC 已更新",
  "entries": [...]  // 返回更新后的完整条目列表
}
```

```
GET /api/toc/preview/{task_id}
功能：预览 TOC 文本格式（用于兼容性）
响应：
{
  "toc_text": "第一章 引言 ............... 1\n  1.1 背景 ............... 3\n..."
}
```

#### 2.2.2 修改现有 API

**`POST /api/ocr/start`** 修改：
- 完成后将 TOC 条目保存到数据库
- 同时保存文本格式（兼容性）

**`POST /api/toc/edit`** 保留：
- 继续支持纯文本编辑模式
- 解析文本后更新数据库中的结构化数据

### 2.3 前端设计

#### 2.3.1 组件架构

**新增组件**：

1. **`HistoryView.vue`** - 任务历史主视图
   - 展示任务列表（卡片或表格形式）
   - 搜索、筛选功能
   - 分页组件
   - 点击进入编辑模式

2. **`TaskCard.vue`** - 单个任务卡片
   - 显示文件名、处理时间、状态
   - 操作按钮：查看/编辑、删除
   - 状态徽章（成功/失败/处理中）

3. **`TOCEditor.vue`** - 结构化 TOC 编辑器
   - 可编辑表格
   - 列：[拖拽手柄] [层级] [标题] [书籍页码] [PDF页码] [操作]
   - 拖拽排序功能（vue-draggable-next）
   - 添加/删除行按钮
   - 层级调整按钮（+1/-1）

4. **`Pagination.vue`** - 分页组件
   - 上一页/下一页
   - 页码显示
   - 跳转到指定页

**修改组件**：

1. **`App.vue`** 修改：
   - 添加"任务历史"入口
   - 路由逻辑：upload | history | process | edit | complete
   - 状态管理增强

2. **`EditView.vue`** 修改：
   - 集成 `TOCEditor.vue` 组件
   - 提供视图切换：结构化 ↔ 文本
   - 支持从历史任务进入

#### 2.3.2 结构化编辑器设计

**表格列设计**：

| 列名 | 宽度 | 功能 | 编辑方式 |
|------|------|------|---------|
| 拖拽手柄 | 40px | 拖拽排序 | 鼠标拖拽 |
| 层级 | 80px | 显示和调整层级（1-5） | 下拉选择或 +/- 按钮 |
| 标题 | 自适应 | 目录标题 | 内联编辑（contenteditable） |
| 书籍页码 | 100px | 原始页码 | 数字输入框 |
| PDF 页码 | 100px | 实际页码 | 数字输入框（可自动计算） |
| 操作 | 80px | 删除按钮 | 点击删除 |

**交互特性**：

1. **拖拽排序**：
   - 使用 `vue-draggable-next` 库
   - 拖动时显示拖拽提示线
   - 松开后更新 `order_index`

2. **内联编辑**：
   - 单击单元格进入编辑模式
   - 失焦或按回车保存
   - ESC 取消编辑

3. **层级调整**：
   - 下拉选择：1（一级）、2（二级）...5（五级）
   - 或使用 +/- 按钮快速调整
   - 层级变化时标题自动添加/移除缩进（视觉效果）

4. **页码联动**：
   - 修改书籍页码时，自动计算 PDF 页码：`pdf_page = book_page + page_offset - 1`
   - PDF 页码也可手动修正

5. **批量操作**：
   - 全选/反选
   - 批量删除
   - 批量调整层级

**数据绑定**：
```javascript
const entries = ref([
  {
    id: 1,
    title: '第一章 引言',
    level: 1,
    bookPage: 1,
    pdfPage: 10,
    orderIndex: 0
  },
  // ...
])
```

**撤销/重做功能**：
```javascript
const history = ref([])
const historyIndex = ref(-1)

const undo = () => {
  if (historyIndex.value > 0) {
    historyIndex.value--
    entries.value = cloneDeep(history.value[historyIndex.value])
  }
}

const redo = () => {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++
    entries.value = cloneDeep(history.value[historyIndex.value])
  }
}
```

#### 2.3.3 任务历史界面设计

**列表视图**：
```vue
<div class="history-view">
  <div class="history-header">
    <h2>任务历史</h2>
    <div class="filters">
      <input type="text" placeholder="搜索文件名..." v-model="searchQuery">
      <select v-model="statusFilter">
        <option value="">全部状态</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
      </select>
    </div>
  </div>

  <div class="task-list">
    <TaskCard
      v-for="task in tasks"
      :key="task.id"
      :task="task"
      @edit="handleEdit"
      @delete="handleDelete"
    />
  </div>

  <Pagination
    :total="totalTasks"
    :page-size="pageSize"
    v-model:current-page="currentPage"
  />
</div>
```

**任务卡片设计**：
```vue
<div class="task-card">
  <div class="card-header">
    <h3>{{ task.filename }}</h3>
    <span :class="['status-badge', task.status]">
      {{ statusText }}
    </span>
  </div>

  <div class="card-body">
    <div class="info-item">
      <span class="label">处理时间：</span>
      <span class="value">{{ formatDate(task.created_at) }}</span>
    </div>
    <div class="info-item">
      <span class="label">目录条目：</span>
      <span class="value">{{ task.toc_count }} 项</span>
    </div>
  </div>

  <div class="card-actions">
    <BaseButton @click="$emit('edit', task)">编辑</BaseButton>
    <BaseButton variant="outline" @click="$emit('delete', task)">删除</BaseButton>
  </div>
</div>
```

### 2.4 状态管理设计

**App.vue 状态扩展**：
```javascript
const state = ref({
  // 视图路由
  currentView: 'upload',  // upload | history | process | edit | complete

  // 当前任务
  taskId: null,

  // 历史任务模式
  isHistoryTask: false,  // 标识是否从历史进入

  // 编辑器模式
  editorMode: 'structured',  // structured | text

  // 其他状态...
})

// 从历史任务进入编辑
const editHistoryTask = (taskId) => {
  state.value.taskId = taskId
  state.value.isHistoryTask = true
  state.value.currentView = 'edit'
}

// 从上传流程进入编辑
const editNewTask = (taskId) => {
  state.value.taskId = taskId
  state.value.isHistoryTask = false
  state.value.currentView = 'edit'
}
```

## 三、实施计划

### 3.1 阶段划分

#### 阶段 1：数据库层实现（1-2天）

**任务清单**：
- [ ] 创建 `database.py` 文件
- [ ] 实现 `DatabaseManager` 类
- [ ] 编写数据库初始化脚本（创建表）
- [ ] 编写单元测试
- [ ] 编写数据迁移脚本（可选，用于迁移现有数据）

**依赖**：
```bash
pip install aiosqlite  # 异步 SQLite 支持
```

**验收标准**：
- 所有 CRUD 操作正常
- 外键关联正确
- 事务处理正确

#### 阶段 2：后端 API 扩展（2-3天）

**任务清单**：
- [ ] 修改 `app.py`，集成 `DatabaseManager`
- [ ] 实现任务历史 API（GET /api/tasks, GET /api/tasks/{id}, DELETE /api/tasks/{id}）
- [ ] 实现结构化 TOC 更新 API（POST /api/toc/update）
- [ ] 修改现有 OCR 流程，完成后保存到数据库
- [ ] 编写 API 测试用例

**文件修改**：
- `app.py`（主要修改）
- `models.py`（可能需要扩展）

**验收标准**：
- 所有 API 端点可通过 Postman 或 curl 测试
- API 文档（/docs）更新完整

#### 阶段 3：任务历史前端（2-3天）

**任务清单**：
- [ ] 创建 `HistoryView.vue`
- [ ] 创建 `TaskCard.vue`
- [ ] 创建 `Pagination.vue`
- [ ] 更新 `App.vue`，添加路由逻辑
- [ ] 更新 `api.js`，添加历史相关 API 调用
- [ ] 样式调整（Anthropic 风格）

**新增文件**：
- `frontend/src/views/HistoryView.vue`
- `frontend/src/components/TaskCard.vue`
- `frontend/src/components/Pagination.vue`

**验收标准**：
- 可查看任务列表
- 可搜索和过滤
- 分页正常
- 可删除任务
- 点击进入编辑界面

#### 阶段 4：结构化编辑器（3-4天）

**任务清单**：
- [ ] 安装依赖：`npm install vue-draggable-next`
- [ ] 创建 `TOCEditor.vue` 组件
- [ ] 实现拖拽排序功能
- [ ] 实现内联编辑
- [ ] 实现层级调整
- [ ] 实现页码联动计算
- [ ] 实现撤销/重做功能
- [ ] 修改 `EditView.vue`，集成新编辑器
- [ ] 添加视图切换功能（结构化 ↔ 文本）

**新增文件**：
- `frontend/src/components/TOCEditor.vue`
- `frontend/src/composables/useUndoRedo.js`（可选）

**验收标准**：
- 拖拽排序流畅
- 编辑操作响应及时
- 数据同步正确
- 撤销/重做正常

#### 阶段 5：集成测试与优化（1-2天）

**任务清单**：
- [ ] 端到端测试完整流程
- [ ] 性能优化（大数据量测试）
- [ ] 样式细节调整
- [ ] 错误处理完善
- [ ] 更新文档（WEB_GUIDE.md）
- [ ] 创建更新日志（CHANGELOG.md）

**测试场景**：
1. 上传新 PDF → 识别 → 结构化编辑 → 生成 PDF
2. 从历史打开任务 → 编辑 → 重新生成
3. 大数据量测试（1000+ 条目）
4. 并发任务测试
5. 异常情况测试（网络中断、服务重启等）

**验收标准**：
- 所有功能正常
- 无明显性能问题
- 界面美观一致

### 3.2 技术风险与应对

#### 风险 1：大数据量性能问题

**风险描述**：
- TOC 条目可能超过 1000 项（大型图书）
- 表格渲染可能卡顿
- 拖拽操作可能延迟

**应对方案**：
1. **虚拟滚动**：使用 `vue-virtual-scroller` 仅渲染可见区域
2. **分页加载**：超过 100 条目时启用分页
3. **防抖处理**：编辑操作使用防抖（debounce）

#### 风险 2：数据一致性问题

**风险描述**：
- 结构化数据与文本数据可能不同步
- 用户在两种模式间切换可能丢失数据

**应对方案**：
1. **单一数据源**：结构化数据为主，文本格式为导出结果
2. **实时同步**：任何编辑立即更新数据库
3. **版本控制**：每次保存记录版本号，支持回滚

#### 风险 3：拖拽功能兼容性

**风险描述**：
- 不同浏览器拖拽行为可能不同
- 触摸屏设备可能不支持拖拽

**应对方案**：
1. **库选择**：使用成熟的 `vue-draggable-next`（基于 Sortable.js）
2. **降级方案**：触摸设备提供上/下移动按钮
3. **浏览器检测**：检测并提示不支持的浏览器

#### 风险 4：数据库迁移风险

**风险描述**：
- 现有用户可能有进行中的任务
- 迁移过程可能丢失数据

**应对方案**：
1. **备份机制**：迁移前自动备份内存数据
2. **平滑迁移**：保留内存存储作为回退方案
3. **版本检测**：启动时检测数据版本，自动迁移

### 3.3 依赖清单

**后端新增依赖**（requirements.txt）：
```
aiosqlite>=0.19.0    # 异步 SQLite 支持
```

**前端新增依赖**（package.json）：
```json
{
  "dependencies": {
    "vue-draggable-next": "^2.2.1"
  },
  "devDependencies": {
    "@types/node": "^20.0.0"  // 可选，TypeScript 支持
  }
}
```

## 四、文件清单

### 4.1 新增文件

**后端**：
- `database.py` - 数据库管理器
- `migrations/001_initial_schema.sql` - 初始数据库架构（可选）

**前端**：
- `frontend/src/views/HistoryView.vue` - 任务历史视图
- `frontend/src/components/TaskCard.vue` - 任务卡片组件
- `frontend/src/components/TOCEditor.vue` - 结构化编辑器
- `frontend/src/components/Pagination.vue` - 分页组件
- `frontend/src/composables/useUndoRedo.js` - 撤销/重做逻辑（可选）

**文档**：
- `IMPLEMENTATION_PLAN.md` - 本文档
- `CHANGELOG.md` - 更新日志

### 4.2 修改文件

**后端**：
- `app.py` - 集成数据库，添加新 API
- `models.py` - 可能添加新的数据模型
- `requirements.txt` - 添加依赖

**前端**：
- `frontend/src/App.vue` - 路由和状态管理
- `frontend/src/views/EditView.vue` - 集成结构化编辑器
- `frontend/src/services/api.js` - 添加新 API 调用
- `frontend/package.json` - 添加依赖
- `WEB_GUIDE.md` - 更新使用文档

## 五、数据库迁移策略

### 5.1 初始化数据库

**启动流程**：
```python
# app.py
from database import DatabaseManager

db = DatabaseManager("./data/tasks.db")

@app.on_event("startup")
async def startup():
    await db.initialize()  # 创建表结构

@app.on_event("shutdown")
async def shutdown():
    await db.close()
```

### 5.2 向后兼容

**策略**：
1. 保留 `tasks_storage` 字典作为缓存层
2. 所有写操作同时写入数据库和内存
3. 读取优先从内存，未命中则查数据库
4. 逐步过渡，最终移除内存存储

**代码示例**：
```python
async def create_task_compatible(task_data: dict) -> str:
    task_id = str(uuid.uuid4())

    # 写入数据库
    await db.create_task(task_data)

    # 写入内存（兼容）
    tasks_storage[task_id] = task_data

    return task_id
```

## 六、UI/UX 设计细节

### 6.1 结构化编辑器 UI

**配色方案**（遵循 Anthropic 风格）：
- 表格边框：`#E0E0E0`（浅灰）
- 表头背景：`#F5F5F0`（米白）
- 悬停行背景：`rgba(255, 107, 53, 0.05)`（淡橙）
- 选中行背景：`rgba(255, 107, 53, 0.1)`（橙色高亮）
- 拖拽提示线：`#FF6B35`（橙色）

**层级视觉表现**：
- 层级 1：无缩进，字体加粗
- 层级 2：缩进 20px
- 层级 3：缩进 40px
- 层级 4：缩进 60px
- 层级 5：缩进 80px

**图标使用**：
- 拖拽手柄：`☰` 或 SVG 图标
- 删除按钮：`🗑️` 或 SVG 垃圾桶图标
- 添加按钮：`+` 或 SVG 加号图标
- 层级调整：`▲` `▼` 或 SVG 箭头

### 6.2 任务历史 UI

**状态徽章**：
- 已完成（completed）：绿色徽章
- 失败（failed）：红色徽章
- 处理中（processing）：橙色徽章，带动画
- 待处理（pending）：灰色徽章

**卡片布局**（参考）：
```
┌─────────────────────────────────────┐
│ 📄 book_name.pdf          [已完成]  │
├─────────────────────────────────────┤
│ 处理时间：2025-01-15 10:30         │
│ 目录条目：145 项                    │
│ 页码范围：5-150                     │
├─────────────────────────────────────┤
│     [编辑]  [重新生成]  [删除]      │
└─────────────────────────────────────┘
```

## 七、测试计划

### 7.1 单元测试

**数据库层测试**：
```python
# tests/test_database.py
async def test_create_task():
    db = DatabaseManager(":memory:")
    task_id = await db.create_task({...})
    assert task_id is not None

async def test_toc_crud():
    # 测试 TOC 条目的增删改查
```

**API 测试**：
```python
# tests/test_api.py
def test_list_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert "tasks" in response.json()
```

### 7.2 集成测试

**完整流程测试**：
1. 上传 PDF → 识别 → 编辑 → 生成
2. 从历史打开 → 编辑 → 重新生成
3. 删除任务 → 验证数据已清除

### 7.3 性能测试

**大数据量测试**：
- 创建 1000 条 TOC 条目
- 测试列表加载时间（< 1s）
- 测试拖拽操作响应（< 100ms）
- 测试保存操作时间（< 2s）

**并发测试**：
- 同时处理 5 个 OCR 任务
- 验证数据库锁机制
- 验证任务状态更新正确

## 八、部署注意事项

### 8.1 数据目录

建议创建专门的数据目录：
```
/path/to/project/
├── app.py
├── data/
│   ├── tasks.db          # SQLite 数据库
│   └── tasks.db.backup   # 自动备份
├── uploads/              # 上传文件
└── outputs/              # 生成文件
```

### 8.2 环境变量

添加到 `.env`：
```env
# 数据库配置
DATABASE_PATH=./data/tasks.db
DATABASE_BACKUP_ENABLED=true

# 文件存储
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs

# 任务配置
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT=3600  # 秒
```

### 8.3 备份策略

**自动备份**：
- 每天凌晨 3 点自动备份数据库
- 保留最近 7 天的备份
- 使用 cron 任务或后台定时器

**手动备份**：
```bash
# 备份数据库
cp data/tasks.db data/tasks.db.backup.$(date +%Y%m%d)

# 备份上传文件
tar -czf uploads_backup.tar.gz uploads/
```

## 九、后续优化方向

### 9.1 功能增强

1. **批量导入**：支持从 Excel/CSV 导入 TOC
2. **模板系统**：保存常用的 TOC 模板
3. **智能推荐**：根据历史数据推荐页码偏置
4. **协作功能**：多人同时编辑（需要 WebSocket）
5. **版本历史**：每次编辑保存快照，支持回滚

### 9.2 性能优化

1. **缓存层**：使用 Redis 缓存热点数据
2. **CDN**：前端静态资源使用 CDN
3. **数据库优化**：添加更多索引，优化查询
4. **异步处理**：使用消息队列（Celery）处理长任务

### 9.3 用户体验

1. **快捷键支持**：Ctrl+S 保存，Ctrl+Z 撤销
2. **自动保存**：每 30 秒自动保存草稿
3. **离线模式**：使用 Service Worker 支持离线编辑
4. **移动端适配**：响应式设计，支持平板和手机

## 十、总结

本实施计划详细描述了两个新功能的技术方案：

1. **结构化 TOC 编辑器**：
   - 采用表格化界面，支持拖拽排序
   - 提供层级、标题、页码的独立编辑
   - 保留纯文本模式作为备用方案

2. **任务历史管理**：
   - 使用 SQLite 持久化存储任务
   - 支持查看、编辑、重新生成历史任务
   - 提供搜索、筛选、分页功能

**预计总工时**：9-14 天

**关键里程碑**：
- 第 2 天：数据库层完成
- 第 5 天：后端 API 完成
- 第 8 天：任务历史前端完成
- 第 12 天：结构化编辑器完成
- 第 14 天：完成测试和优化

**下一步行动**：
1. 评审本计划，确认技术方案
2. 开始阶段 1：数据库层实现
3. 逐步推进后续阶段

---

**文档版本**：v1.0
**创建日期**：2025-01-17
**最后更新**：2025-01-17
