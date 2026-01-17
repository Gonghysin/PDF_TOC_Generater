<template>
  <div class="task-card">
    <div class="card-header">
      <h3 class="task-filename">{{ task.pdf_filename }}</h3>
      <span class="status-badge" :class="statusClass">
        {{ statusText }}
      </span>
    </div>

    <div class="card-body">
      <div class="info-row">
        <span class="label">处理时间：</span>
        <span class="value">{{ formatDate(task.created_at) }}</span>
      </div>

      <div class="info-row" v-if="task.page_range">
        <span class="label">页码范围：</span>
        <span class="value">{{ task.page_range }}</span>
      </div>

      <div class="info-row" v-if="task.toc_count !== undefined">
        <span class="label">目录条目：</span>
        <span class="value">{{ task.toc_count }} 项</span>
      </div>

      <div class="info-row" v-if="task.error_message">
        <span class="label error">错误信息：</span>
        <span class="value error">{{ task.error_message }}</span>
      </div>
    </div>

    <div class="card-actions">
      <button class="action-btn primary" @click="$emit('edit', task)">
        编辑
      </button>
      <button class="action-btn secondary" @click="$emit('delete', task)" v-if="canDelete">
        删除
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

defineEmits(['edit', 'delete'])

const statusClass = computed(() => {
  const statusMap = {
    'pending': 'pending',
    'processing': 'processing',
    'completed': 'completed',
    'failed': 'failed'
  }
  return statusMap[props.task.status] || 'pending'
})

const statusText = computed(() => {
  const textMap = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return textMap[props.task.status] || '未知'
})

const canDelete = computed(() => {
  return ['completed', 'failed'].includes(props.task.status)
})

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.task-card {
  border: 1px solid var(--color-black);
  background: var(--color-white);
  padding: 20px;
  margin-bottom: 16px;
  transition: box-shadow var(--transition-fast);
}

.task-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.task-filename {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--color-black);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 16px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.status-badge.pending {
  background: #E0E0E0;
  color: #666;
}

.status-badge.processing {
  background: var(--color-orange);
  color: var(--color-white);
  animation: pulse 2s infinite;
}

.status-badge.completed {
  background: #4CAF50;
  color: var(--color-white);
}

.status-badge.failed {
  background: #F44336;
  color: var(--color-white);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.card-body {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.label {
  color: rgba(0, 0, 0, 0.6);
  margin-right: 8px;
  min-width: 80px;
}

.label.error {
  color: #F44336;
}

.value {
  color: var(--color-black);
}

.value.error {
  color: #F44336;
}

.card-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 10px 20px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  color: var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn.primary {
  background: var(--color-orange);
  border-color: var(--color-orange);
  color: var(--color-white);
}

.action-btn.primary:hover {
  background: #E85A2A;
  border-color: #E85A2A;
}

.action-btn.secondary:hover {
  background: var(--color-beige);
}
</style>
