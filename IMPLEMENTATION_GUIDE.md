# PDF 目录生成器 - 详细实施指南

> 本文档是 `IMPLEMENTATION_PLAN.md` 的详细补充，提供具体的代码示例、分步指南和实施清单。

## 📋 文档说明

- **主计划文档**: `IMPLEMENTATION_PLAN.md` - 提供整体技术方案和架构设计
- **本文档**: 提供详细的实施步骤、代码示例和验收清单
- **建议阅读顺序**: 先阅读主计划，再参考本详细指南进行实施

---

## 🎯 快速开始检查清单

### 环境准备

- [ ] Python 3.10+ 已安装
- [ ] Node.js 18+ 和 npm 已安装
- [ ] Git 仓库已配置
- [ ] 开发工具已准备（VS Code / PyCharm）

### 依赖安装

```bash
# 后端依赖
pip install aiosqlite>=0.19.0
pip install apscheduler>=3.10.0

# 前端依赖
cd frontend
npm install vuedraggable@next
```

---

## 📅 详细实施步骤（按天规划）

### Day 1: 数据库层开发

#### 任务 1.1: 创建数据库管理器

**文件**: `database.py`

```python
"""
数据库管理模块
使用 SQLite 持久化存储任务和 TOC 数据
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging

from models import TOCEntry, MergedTOC, TOCMetadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "data/tasks.db"):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False  # 允许多线程访问
        )
        self.conn.row_factory = sqlite3.Row  # 返回字典格式
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 创建 tasks 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                pdf_path TEXT NOT NULL,
                pdf_filename TEXT NOT NULL,
                page_offset INTEGER NOT NULL DEFAULT 0,
                page_range TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata TEXT
            )
        """)

        # 创建 toc_entries 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS toc_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                entry_order INTEGER NOT NULL,
                title TEXT NOT NULL,
                page INTEGER NOT NULL,
                level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)

        # 创建 task_outputs 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                output_path TEXT NOT NULL,
                download_url TEXT,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_toc_entries_task_id ON toc_entries(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_toc_entries_order ON toc_entries(task_id, entry_order)")

        self.conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    # ==================== 任务管理方法 ====================

    def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        创建新任务

        Args:
            task_data: 任务数据字典，必须包含:
                - task_id: 任务ID
                - pdf_path: PDF文件路径
                - pdf_filename: PDF文件名
                - page_offset: 页码偏置
                - status: 状态 (可选，默认pending)

        Returns:
            str: 任务ID
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (
                task_id, pdf_path, pdf_filename, page_offset,
                page_range, status, progress, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_data['task_id'],
            task_data['pdf_path'],
            task_data['pdf_filename'],
            task_data.get('page_offset', 0),
            task_data.get('page_range'),
            task_data.get('status', 'pending'),
            task_data.get('progress', 0),
            json.dumps(task_data.get('metadata', {}))
        ))

        self.conn.commit()
        logger.info(f"任务已创建: {task_data['task_id']}")

        return task_data['task_id']

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务数据字典，如果不存在返回 None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if row:
            task = dict(row)
            # 解析 metadata JSON
            if task.get('metadata'):
                task['metadata'] = json.loads(task['metadata'])
            return task
        return None

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """
        更新任务信息

        Args:
            task_id: 任务ID
            updates: 要更新的字段字典
        """
        # 构建 SET 子句
        set_clauses = []
        values = []

        for key, value in updates.items():
            if key == 'metadata':
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)

        # 自动更新 updated_at
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        values.append(task_id)

        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE tasks SET {', '.join(set_clauses)} WHERE task_id = ?",
            values
        )
        self.conn.commit()

        logger.info(f"任务已更新: {task_id}")

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取任务列表（分页）

        Args:
            status: 状态过滤（可选）
            limit: 每页数量
            offset: 偏移量

        Returns:
            任务列表
        """
        cursor = self.conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )

        rows = cursor.fetchall()
        tasks = []

        for row in rows:
            task = dict(row)
            if task.get('metadata'):
                task['metadata'] = json.loads(task['metadata'])
            tasks.append(task)

        return tasks

    def count_tasks(self, status: Optional[str] = None) -> int:
        """
        统计任务数量

        Args:
            status: 状态过滤（可选）

        Returns:
            任务数量
        """
        cursor = self.conn.cursor()

        if status:
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM tasks")

        return cursor.fetchone()[0]

    def delete_task(self, task_id: str):
        """
        删除任务及其所有关联数据

        Args:
            task_id: 任务ID
        """
        cursor = self.conn.cursor()

        # 由于设置了 ON DELETE CASCADE，只需删除任务即可
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        self.conn.commit()

        logger.info(f"任务已删除: {task_id}")

    # ==================== TOC 条目管理方法 ====================

    def save_toc_entries(self, task_id: str, entries: List[TOCEntry]):
        """
        批量保存 TOC 条目（替换式）

        Args:
            task_id: 任务ID
            entries: TOC条目列表
        """
        cursor = self.conn.cursor()

        # 先删除现有条目
        cursor.execute("DELETE FROM toc_entries WHERE task_id = ?", (task_id,))

        # 插入新条目
        for order, entry in enumerate(entries):
            cursor.execute("""
                INSERT INTO toc_entries (
                    task_id, entry_order, title, page, level
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                order,
                entry.title,
                entry.page,
                entry.level
            ))

        self.conn.commit()
        logger.info(f"已保存 {len(entries)} 个 TOC 条目 (任务: {task_id})")

    def get_toc_entries(self, task_id: str) -> List[TOCEntry]:
        """
        获取任务的所有 TOC 条目

        Args:
            task_id: 任务ID

        Returns:
            TOC条目列表（按 order_index 排序）
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM toc_entries WHERE task_id = ? ORDER BY entry_order",
            (task_id,)
        )

        rows = cursor.fetchall()
        entries = []

        for row in rows:
            entry = TOCEntry(
                title=row['title'],
                page=row['page'],
                level=row['level']
            )
            entries.append(entry)

        return entries

    def count_toc_entries(self, task_id: str) -> int:
        """
        统计任务的 TOC 条目数量

        Args:
            task_id: 任务ID

        Returns:
            条目数量
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM toc_entries WHERE task_id = ?",
            (task_id,)
        )
        return cursor.fetchone()[0]

    # ==================== 任务输出管理方法 ====================

    def add_task_output(self, task_id: str, output_data: Dict[str, Any]):
        """
        记录任务输出文件

        Args:
            task_id: 任务ID
            output_data: 输出数据，包含:
                - output_path: 输出文件路径
                - download_url: 下载URL
                - file_size: 文件大小
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO task_outputs (
                task_id, output_path, download_url, file_size
            ) VALUES (?, ?, ?, ?)
        """, (
            task_id,
            output_data['output_path'],
            output_data.get('download_url'),
            output_data.get('file_size')
        ))

        self.conn.commit()
        logger.info(f"已记录任务输出: {task_id}")

    def get_task_outputs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取任务的所有输出记录

        Args:
            task_id: 任务ID

        Returns:
            输出记录列表
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM task_outputs WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,)
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== 清理方法 ====================

    def cleanup_old_tasks(self, days: int = 30):
        """
        清理旧任务

        Args:
            days: 保留天数，超过该天数的已完成任务将被删除
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            DELETE FROM tasks
            WHERE status = 'completed'
            AND completed_at < datetime('now', '-' || ? || ' days')
        """, (days,))

        deleted_count = cursor.rowcount
        self.conn.commit()

        logger.info(f"已清理 {deleted_count} 个旧任务 (保留 {days} 天内)")

        return deleted_count

    # ==================== 工具方法 ====================

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
        logger.info("数据库连接已关闭")
```

**验收清单**:
- [ ] 文件已创建且无语法错误
- [ ] 数据库初始化成功
- [ ] 所有 CRUD 方法可正常调用
- [ ] 外键约束生效（删除任务时级联删除条目）

---

#### 任务 1.2: 编写数据库测试

**文件**: `tests/test_database.py`

```python
import pytest
import os
from pathlib import Path
from database import DatabaseManager
from models import TOCEntry

@pytest.fixture
def db():
    """测试数据库 fixture"""
    test_db_path = "test_tasks.db"

    # 创建测试数据库
    db_manager = DatabaseManager(test_db_path)

    yield db_manager

    # 清理
    db_manager.close()
    if Path(test_db_path).exists():
        os.remove(test_db_path)


def test_create_task(db):
    """测试创建任务"""
    task_id = db.create_task({
        'task_id': 'test-001',
        'pdf_path': '/path/to/test.pdf',
        'pdf_filename': 'test.pdf',
        'page_offset': 10,
        'status': 'pending'
    })

    assert task_id == 'test-001'

    # 验证任务已保存
    task = db.get_task('test-001')
    assert task is not None
    assert task['pdf_filename'] == 'test.pdf'
    assert task['page_offset'] == 10


def test_update_task(db):
    """测试更新任务"""
    db.create_task({
        'task_id': 'test-002',
        'pdf_path': '/path/to/test.pdf',
        'pdf_filename': 'test.pdf',
        'page_offset': 10
    })

    db.update_task('test-002', {
        'status': 'completed',
        'progress': 100
    })

    task = db.get_task('test-002')
    assert task['status'] == 'completed'
    assert task['progress'] == 100


def test_list_tasks(db):
    """测试任务列表"""
    # 创建多个任务
    for i in range(5):
        db.create_task({
            'task_id': f'test-{i}',
            'pdf_path': f'/path/to/test{i}.pdf',
            'pdf_filename': f'test{i}.pdf',
            'page_offset': 0,
            'status': 'completed' if i % 2 == 0 else 'pending'
        })

    # 获取全部
    all_tasks = db.list_tasks(limit=10, offset=0)
    assert len(all_tasks) == 5

    # 过滤已完成
    completed_tasks = db.list_tasks(status='completed')
    assert len(completed_tasks) == 3


def test_save_and_get_toc_entries(db):
    """测试保存和获取 TOC 条目"""
    db.create_task({
        'task_id': 'test-003',
        'pdf_path': '/path/to/test.pdf',
        'pdf_filename': 'test.pdf',
        'page_offset': 10
    })

    entries = [
        TOCEntry(title="第一章", page=1, level=1),
        TOCEntry(title="1.1 节", page=5, level=2),
        TOCEntry(title="第二章", page=20, level=1),
    ]

    db.save_toc_entries('test-003', entries)

    # 获取并验证
    saved_entries = db.get_toc_entries('test-003')
    assert len(saved_entries) == 3
    assert saved_entries[0].title == "第一章"
    assert saved_entries[1].level == 2


def test_delete_task_cascade(db):
    """测试删除任务时级联删除 TOC"""
    db.create_task({
        'task_id': 'test-004',
        'pdf_path': '/path/to/test.pdf',
        'pdf_filename': 'test.pdf',
        'page_offset': 10
    })

    entries = [TOCEntry(title="Test", page=1, level=1)]
    db.save_toc_entries('test-004', entries)

    # 删除任务
    db.delete_task('test-004')

    # 验证任务和条目都被删除
    assert db.get_task('test-004') is None
    assert len(db.get_toc_entries('test-004')) == 0
```

**运行测试**:
```bash
pytest tests/test_database.py -v
```

**验收清单**:
- [ ] 所有测试通过
- [ ] 测试覆盖率 > 80%

---

### Day 2-3: 后端 API 集成

#### 任务 2.1: 修改 app.py 集成数据库

在 `app.py` 开头添加：

```python
from database import DatabaseManager
from apscheduler.schedulers.background import BackgroundScheduler

# 初始化数据库
db_manager = DatabaseManager("data/tasks.db")

# 初始化定时任务调度器
scheduler = BackgroundScheduler()
```

修改现有的任务创建逻辑（示例）：

```python
# 旧代码（内存存储）
tasks_storage[task_id] = {
    "task_id": task_id,
    "status": "pending",
    ...
}

# 新代码（数据库存储）
db_manager.create_task({
    "task_id": task_id,
    "pdf_path": pdf_path,
    "pdf_filename": Path(pdf_path).name,
    "page_offset": page_offset,
    "page_range": page_range,
    "status": "pending",
    "progress": 0
})
```

**验收清单**:
- [ ] 所有原有 API 正常工作
- [ ] 任务数据正确保存到数据库
- [ ] 服务重启后数据不丢失

---

#### 任务 2.2: 新增任务历史 API

在 `app.py` 中添加：

```python
@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """
    获取任务列表

    Query Parameters:
        status: 状态过滤（可选）
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        {
            "total": int,
            "page": int,
            "page_size": int,
            "tasks": [...]
        }
    """
    offset = (page - 1) * page_size
    tasks = db_manager.list_tasks(status, limit=page_size, offset=offset)
    total = db_manager.count_tasks(status)

    # 为每个任务添加 TOC 条目数量
    for task in tasks:
        task['toc_count'] = db_manager.count_toc_entries(task['task_id'])

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": tasks
    }


@app.get("/api/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """
    获取任务详情

    Returns:
        {
            "task": {...},
            "toc_entries": [...],
            "outputs": [...]
        }
    """
    task = db_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    entries = db_manager.get_toc_entries(task_id)
    outputs = db_manager.get_task_outputs(task_id)

    return {
        "task": task,
        "toc_entries": [
            {
                "title": e.title,
                "page": e.page,
                "level": e.level
            }
            for e in entries
        ],
        "outputs": outputs
    }


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    task = db_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db_manager.delete_task(task_id)

    return {"success": True, "message": "任务已删除"}
```

**验收清单**:
- [ ] `GET /api/tasks` 返回正确的任务列表
- [ ] 分页功能正常
- [ ] 状态过滤正常
- [ ] `GET /api/tasks/{id}` 返回完整任务详情
- [ ] `DELETE /api/tasks/{id}` 正确删除任务

---

#### 任务 2.3: 添加结构化 TOC 更新 API

```python
class TOCEntryUpdate(BaseModel):
    """TOC 条目更新模型"""
    title: str
    page: int
    level: int = Field(ge=1, le=5)


class TOCBatchUpdateRequest(BaseModel):
    """批量更新请求"""
    task_id: str
    entries: List[TOCEntryUpdate]
    page_offset: int


@app.post("/api/toc/update")
async def update_toc_structured(request: TOCBatchUpdateRequest):
    """
    结构化批量更新 TOC

    Returns:
        {
            "success": bool,
            "updated_count": int,
            "message": str
        }
    """
    try:
        # 验证任务存在
        task = db_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(404, "任务不存在")

        # 转换为 TOCEntry 对象
        entries = [
            TOCEntry(
                title=e.title,
                page=e.page,
                level=e.level
            )
            for e in request.entries
        ]

        # 保存到数据库
        db_manager.save_toc_entries(request.task_id, entries)

        # 更新页码偏置
        db_manager.update_task(request.task_id, {
            "page_offset": request.page_offset
        })

        return {
            "success": True,
            "updated_count": len(entries),
            "message": f"已更新 {len(entries)} 个条目"
        }

    except Exception as e:
        logger.error(f"更新 TOC 失败: {e}")
        raise HTTPException(500, f"更新失败: {str(e)}")
```

**验收清单**:
- [ ] 可成功批量更新 TOC 条目
- [ ] 数据库中的数据正确更新
- [ ] 错误处理正确

---

#### 任务 2.4: 添加定时清理任务

```python
# 在 app.py 中添加

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 启动定时清理任务
    scheduler.add_job(
        func=cleanup_old_tasks_job,
        trigger='cron',
        hour=2,  # 每天凌晨 2 点执行
        minute=0
    )
    scheduler.start()
    logger.info("定时清理任务已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    scheduler.shutdown()
    db_manager.close()
    logger.info("应用已关闭")


def cleanup_old_tasks_job():
    """清理旧任务的定时任务"""
    try:
        deleted_count = db_manager.cleanup_old_tasks(days=30)
        logger.info(f"定时清理完成，删除了 {deleted_count} 个旧任务")
    except Exception as e:
        logger.error(f"定时清理失败: {e}")
```

**验收清单**:
- [ ] 应用启动时定时任务正常启动
- [ ] 清理逻辑正确（保留最近30天的已完成任务）
- [ ] 日志记录完整

---

### Day 4-5: 前端任务历史界面

#### 任务 4.1: 更新 API 服务层

**文件**: `frontend/src/services/api.js`

在现有 API 服务中添加：

```javascript
/**
 * 获取任务列表
 */
async listTasks(status = null, page = 1, pageSize = 20) {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString()
  })

  if (status) {
    params.append('status', status)
  }

  const response = await fetch(
    `${API_BASE_URL}/api/tasks?${params.toString()}`
  )

  if (!response.ok) {
    throw new Error(`获取任务列表失败: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 获取任务详情
 */
async getTaskDetail(taskId) {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`)

  if (!response.ok) {
    throw new Error(`获取任务详情失败: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 删除任务
 */
async deleteTask(taskId) {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error(`删除任务失败: ${response.statusText}`)
  }

  return await response.json()
}

/**
 * 结构化更新 TOC
 */
async updateTOCStructured(taskId, data) {
  const response = await fetch(`${API_BASE_URL}/api/toc/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      task_id: taskId,
      entries: data.entries,
      page_offset: data.page_offset
    })
  })

  if (!response.ok) {
    throw new Error(`更新 TOC 失败: ${response.statusText}`)
  }

  return await response.json()
}
```

**验收清单**:
- [ ] API 方法正确封装
- [ ] 错误处理完善
- [ ] 可正常调用后端接口

---

## ⏭️ 后续步骤预览

由于文档篇幅限制，剩余的详细步骤包括：

- **Day 6-7**: 创建 HistoryView、TaskCard、Pagination 组件
- **Day 8-11**: 开发 TOCEditor 结构化编辑器（包含完整代码）
- **Day 12-13**: 集成测试与优化

完整的代码示例、样式设计和验收清单请参考主计划文档 `IMPLEMENTATION_PLAN.md`。

---

## 📋 总体验收清单

### 后端验收
- [ ] 数据库表结构正确创建
- [ ] 所有 CRUD 操作正常
- [ ] API 端点全部可访问
- [ ] 定时清理任务正常运行
- [ ] 日志记录完整

### 前端验收
- [ ] 任务历史页面正常显示
- [ ] 可查看、搜索、过滤任务
- [ ] 可从历史进入编辑
- [ ] 结构化编辑器功能完整
- [ ] 拖拽排序流畅
- [ ] 数据保存正确

### 集成验收
- [ ] 完整流程测试通过
- [ ] 性能测试通过（1000+ 条目）
- [ ] 浏览器兼容性测试通过
- [ ] 文档更新完整

---

**文档版本**: v1.0
**最后更新**: 2026-01-17
**状态**: 进行中
