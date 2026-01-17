<template>
  <div class="history-view">
    <div class="history-header">
      <h1>任务历史</h1>
      <div class="header-actions">
        <select v-model="statusFilter" class="status-filter">
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <button class="btn-back" @click="$emit('back')">
          返回上传
        </button>
      </div>
    </div>

    <div class="history-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button class="btn-retry" @click="loadTasks">重试</button>
      </div>

      <div v-else-if="tasks.length === 0" class="empty-state">
        <p>暂无任务记录</p>
        <button class="btn-new-task" @click="$emit('back')">
          创建新任务
        </button>
      </div>

      <div v-else class="task-list">
        <TaskCard
          v-for="task in tasks"
          :key="task.task_id"
          :task="task"
          @edit="handleEdit"
          @delete="handleDelete"
        />

        <Pagination
          v-if="total > 0"
          :total="total"
          :page-size="pageSize"
          v-model:current-page="currentPage"
        />
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="cancelDelete">
      <div class="modal-content" @click.stop>
        <h3>确认删除</h3>
        <p>确定要删除任务「{{ deleteTarget?.pdf_filename }}」吗？</p>
        <p class="warning-text">此操作不可恢复！</p>
        <div class="modal-actions">
          <button class="btn-cancel" @click="cancelDelete">取消</button>
          <button class="btn-confirm" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '../services/api'
import TaskCard from '../components/TaskCard.vue'
import Pagination from '../components/Pagination.vue'

const emit = defineEmits(['back', 'edit'])

// 状态
const tasks = ref([])
const loading = ref(false)
const error = ref(null)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await api.getTasks(
      statusFilter.value || null,
      currentPage.value,
      pageSize.value
    )

    tasks.value = response.tasks
    total.value = response.total
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// 编辑任务
const handleEdit = (task) => {
  emit('edit', task.task_id)
}

// 删除任务（显示确认对话框）
const handleDelete = (task) => {
  deleteTarget.value = task
  showDeleteConfirm.value = true
}

// 确认删除
const confirmDelete = async () => {
  if (!deleteTarget.value) return

  try {
    await api.deleteTask(deleteTarget.value.task_id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    // 重新加载列表
    await loadTasks()
  } catch (err) {
    error.value = `删除失败: ${err.message}`
    showDeleteConfirm.value = false
  }
}

// 取消删除
const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTarget.value = null
}

// 监听页码和过滤器变化
watch([currentPage, statusFilter], () => {
  loadTasks()
})

// 组件挂载时加载
onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.history-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--color-black);
}

.history-header h1 {
  font-size: 32px;
  font-weight: 700;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.status-filter {
  padding: 8px 16px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
}

.btn-back {
  padding: 10px 20px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-back:hover {
  background: var(--color-beige);
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-beige);
  border-top-color: var(--color-orange);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  color: #F44336;
  margin-bottom: 16px;
}

.btn-retry,
.btn-new-task {
  padding: 12px 24px;
  border: 1px solid var(--color-black);
  background: var(--color-orange);
  color: var(--color-white);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-retry:hover,
.btn-new-task:hover {
  background: #E85A2A;
}

.task-list {
  min-height: 400px;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-white);
  padding: 32px;
  border: 2px solid var(--color-black);
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 600;
}

.modal-content p {
  margin: 0 0 12px;
  line-height: 1.6;
}

.warning-text {
  color: #F44336;
  font-weight: 500;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn-cancel,
.btn-confirm {
  flex: 1;
  padding: 10px 20px;
  border: 1px solid var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel {
  background: var(--color-white);
  color: var(--color-black);
}

.btn-cancel:hover {
  background: var(--color-beige);
}

.btn-confirm {
  background: #F44336;
  border-color: #F44336;
  color: var(--color-white);
}

.btn-confirm:hover {
  background: #D32F2F;
  border-color: #D32F2F;
}
</style>
