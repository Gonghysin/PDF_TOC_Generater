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

        # 启用外键约束
        self.conn.execute("PRAGMA foreign_keys = ON")

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
