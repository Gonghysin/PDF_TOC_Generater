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
