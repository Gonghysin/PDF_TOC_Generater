<template>
  <div class="process-view">
    <BaseCard padding="xl">
      <template #header>
        <div class="card-header-content">
          <button class="back-btn" @click="$emit('back')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M19 12H5M12 19l-7-7 7-7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <h2>配置处理参数</h2>
        </div>
      </template>

      <div v-if="!processing && !taskStarted" class="config-container">
        <div class="pdf-info-section">
          <h3 class="section-title">PDF 信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">文件名</span>
              <span class="info-value">{{ pdfInfo.filename }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">总页数</span>
              <span class="info-value">{{ pdfInfo.total_pages }} 页</span>
            </div>
            <div class="info-item">
              <span class="info-label">文件大小</span>
              <span class="info-value">{{ formatFileSize(pdfInfo.file_size) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">现有目录</span>
              <span class="info-value">{{ pdfInfo.has_toc ? '有' : '无' }}</span>
            </div>
          </div>
        </div>

        <div class="config-section">
          <h3 class="section-title">目录识别配置</h3>

          <div class="form-group">
            <label class="form-label">目录页范围</label>
            <input
              v-model="pageRange"
              type="text"
              class="form-input"
              placeholder="例如: 5-12"
            />
            <p class="form-hint">填写目录所在的页码范围，例如 "5-12" 表示第 5 页到第 12 页</p>
          </div>

          <div class="form-group">
            <label class="form-label">页码偏置</label>
            <input
              v-model.number="pageOffset"
              type="number"
              class="form-input"
              placeholder="0"
            />
            <p class="form-hint">PDF 显示页码与实际页码的差值（通常为 0）</p>
          </div>

          <div class="form-group">
            <label class="form-checkbox">
              <input v-model="parallel" type="checkbox" />
              <span>并行处理（更快但消耗更多资源）</span>
            </label>
          </div>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <BaseButton
          variant="primary"
          size="lg"
          full-width
          @click="startProcessing"
        >
          开始识别
        </BaseButton>
      </div>

      <div v-else class="progress-container">
        <h3 class="section-title">正在处理</h3>

        <ProgressBar
          :percentage="progress"
          :message="statusMessage"
          label="OCR 识别进度"
        />

        <div class="progress-details">
          <div class="progress-step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
            <div class="step-icon">1</div>
            <div class="step-text">提取目录页图片</div>
          </div>
          <div class="progress-step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
            <div class="step-icon">2</div>
            <div class="step-text">AI 识别目录内容</div>
          </div>
          <div class="progress-step" :class="{ active: currentStep >= 3, completed: currentStep > 3 }">
            <div class="step-icon">3</div>
            <div class="step-text">合并目录数据</div>
          </div>
        </div>

        <div v-if="taskCompleted" class="completion-message">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <polyline points="22 4 12 14.01 9 11.01" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <p>识别完成！共识别到 {{ totalEntries }} 个目录条目</p>
          <BaseButton
            variant="primary"
            size="lg"
            @click="goToEdit"
            class="mt-md"
          >
            查看并编辑目录
          </BaseButton>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import ProgressBar from '../components/ProgressBar.vue'
import api from '../services/api.js'

export default {
  name: 'ProcessView',
  components: {
    BaseCard,
    BaseButton,
    ProgressBar
  },
  props: {
    pdfInfo: {
      type: Object,
      required: true
    }
  },
  emits: ['started', 'back'],
  setup(props, { emit }) {
    const pageRange = ref('')
    const pageOffset = ref(0)
    const parallel = ref(true)
    const processing = ref(false)
    const taskStarted = ref(false)
    const taskCompleted = ref(false)
    const error = ref('')
    const progress = ref(0)
    const statusMessage = ref('')
    const currentStep = ref(0)
    const taskId = ref(null)
    const tocText = ref('')
    const totalEntries = ref(0)

    const startProcessing = async () => {
      if (!pageRange.value) {
        error.value = '请填写目录页范围'
        return
      }

      try {
        error.value = ''
        processing.value = true
        taskStarted.value = true
        currentStep.value = 1

        const response = await api.startOCRTask(
          props.pdfInfo.path,
          pageRange.value,
          pageOffset.value,
          parallel.value
        )

        taskId.value = response.task_id
        pollTaskStatus()
      } catch (err) {
        error.value = err.message || '启动任务失败'
        processing.value = false
        taskStarted.value = false
      }
    }

    const pollTaskStatus = async () => {
      const checkStatus = async () => {
        try {
          const status = await api.getTaskStatus(taskId.value)

          progress.value = status.progress
          statusMessage.value = status.message

          if (status.progress >= 30 && status.progress < 60) {
            currentStep.value = 2
          } else if (status.progress >= 60) {
            currentStep.value = 3
          }

          if (status.status === 'completed') {
            taskCompleted.value = true
            tocText.value = status.result.toc_text
            totalEntries.value = status.result.total_entries
          } else if (status.status === 'failed') {
            error.value = status.error || '处理失败'
            processing.value = false
          } else {
            setTimeout(checkStatus, 2000)
          }
        } catch (err) {
          error.value = '获取任务状态失败'
          processing.value = false
        }
      }

      checkStatus()
    }

    const goToEdit = () => {
      emit('started', {
        taskId: taskId.value,
        tocText: tocText.value
      })
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    return {
      pageRange,
      pageOffset,
      parallel,
      processing,
      taskStarted,
      taskCompleted,
      error,
      progress,
      statusMessage,
      currentStep,
      totalEntries,
      startProcessing,
      goToEdit,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.card-header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  cursor: pointer;
  padding: var(--spacing-xs);
  transition: color var(--transition-fast);
}

.back-btn:hover {
  color: var(--color-primary);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-black);
  margin-bottom: var(--spacing-md);
}

.pdf-info-section {
  margin-bottom: var(--spacing-xl);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.info-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.info-value {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-black);
}

.config-section {
  margin-bottom: var(--spacing-xl);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-label {
  display: block;
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--color-black);
  margin-bottom: var(--spacing-xs);
}

.form-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  color: var(--color-black);
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-hint {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-size: var(--font-size-base);
}

.form-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.error-message {
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: #FEE;
  border: 1px solid #FCC;
  border-radius: var(--radius-md);
  color: #C33;
  font-size: var(--font-size-sm);
}

.progress-container {
  text-align: center;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.progress-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  opacity: 0.4;
  transition: opacity var(--transition-base);
}

.progress-step.active {
  opacity: 1;
}

.progress-step.completed {
  opacity: 1;
}

.step-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.progress-step.active .step-icon,
.progress-step.completed .step-icon {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-white);
}

.step-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
}

.completion-message {
  text-align: center;
  padding: var(--spacing-xl);
}

.completion-message svg {
  color: var(--color-primary);
  margin-bottom: var(--spacing-md);
}

.completion-message p {
  font-size: var(--font-size-lg);
  color: var(--color-black);
  margin-bottom: var(--spacing-md);
}
</style>
