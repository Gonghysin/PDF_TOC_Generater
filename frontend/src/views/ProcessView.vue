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
              placeholder="例如: 10"
              min="1"
            />
            <p class="form-hint">书籍第1页对应PDF文件第几页，这个数值就是偏置。例如：如果PDF第10页是书籍第1页，则填10</p>
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

        <!-- 主进度条 -->
        <ProgressBar
          :percentage="progress"
          :message="statusMessage"
          label="总体进度"
        />

        <!-- 详细进度信息 -->
        <div class="progress-info">
          <div class="progress-stats">
            <div class="stat-item">
              <div class="stat-value">{{ progress }}%</div>
              <div class="stat-label">完成进度</div>
            </div>
            <div class="stat-item" v-if="currentStepName">
              <div class="stat-value">{{ currentStepName }}</div>
              <div class="stat-label">当前阶段</div>
            </div>
            <div class="stat-item" v-if="detailedProgress">
              <div class="stat-value">{{ detailedProgress }}</div>
              <div class="stat-label">处理详情</div>
            </div>
          </div>
        </div>

        <!-- 步骤指示器 -->
        <div class="progress-details">
          <div class="progress-step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
            <div class="step-icon">
              <span v-if="currentStep > 1">✓</span>
              <span v-else>1</span>
            </div>
            <div class="step-text">提取目录页图片</div>
            <div class="step-progress" v-if="currentStep === 1">{{ getStepProgress(1) }}</div>
          </div>
          <div class="step-divider" :class="{ completed: currentStep > 1 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
            <div class="step-icon">
              <span v-if="currentStep > 2">✓</span>
              <span v-else>2</span>
            </div>
            <div class="step-text">AI 识别目录内容</div>
            <div class="step-progress" v-if="currentStep === 2">{{ getStepProgress(2) }}</div>
          </div>
          <div class="step-divider" :class="{ completed: currentStep > 2 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 3, completed: currentStep > 3 }">
            <div class="step-icon">
              <span v-if="currentStep > 3">✓</span>
              <span v-else>3</span>
            </div>
            <div class="step-text">合并目录数据</div>
            <div class="step-progress" v-if="currentStep === 3">{{ getStepProgress(3) }}</div>
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
    const pageOffset = ref(1)
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

    // 计算属性：当前步骤名称
    const currentStepName = computed(() => {
      const stepNames = {
        1: '提取图片',
        2: 'AI识别',
        3: '合并数据'
      }
      return stepNames[currentStep.value] || ''
    })

    // 计算属性：详细进度（从消息中提取 "1/3" 这样的信息）
    const detailedProgress = computed(() => {
      const match = statusMessage.value.match(/\((\d+)\/(\d+)\)/)
      if (match) {
        return `${match[1]}/${match[2]} 页`
      }
      return ''
    })

    // 获取步骤进度文字
    const getStepProgress = (step) => {
      if (currentStep.value === step) {
        // 从消息中提取进度
        const match = statusMessage.value.match(/\((\d+)\/(\d+)\)/)
        if (match) {
          return `${match[1]}/${match[2]}`
        }
        // 或者根据进度百分比计算
        if (step === 1) {
          return progress.value < 30 ? `${Math.round((progress.value / 30) * 100)}%` : '100%'
        } else if (step === 2) {
          if (progress.value >= 30 && progress.value < 60) {
            return `${Math.round(((progress.value - 30) / 30) * 100)}%`
          }
        } else if (step === 3) {
          if (progress.value >= 60 && progress.value < 100) {
            return `${Math.round(((progress.value - 60) / 40) * 100)}%`
          }
        }
      }
      return ''
    }

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
      currentStepName,
      detailedProgress,
      getStepProgress,
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

.progress-info {
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: var(--color-beige);
  border-radius: var(--radius-md);
}

.progress-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--spacing-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-orange);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  padding: 0 var(--spacing-md);
}

.progress-step {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  opacity: 0.4;
  transition: all var(--transition-base);
  position: relative;
}

.progress-step.active {
  opacity: 1;
}

.progress-step.completed {
  opacity: 1;
}

.step-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 3px solid var(--color-border);
  font-weight: 700;
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  background: var(--color-white);
  transition: all var(--transition-base);
}

.progress-step.active .step-icon {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-white);
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
}

.progress-step.completed .step-icon {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-white);
}

.step-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
  font-weight: 500;
}

.progress-step.active .step-text {
  color: var(--color-black);
  font-weight: 600;
}

.step-progress {
  position: absolute;
  top: -8px;
  right: -8px;
  background: var(--color-orange);
  color: var(--color-white);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  white-space: nowrap;
}

.step-divider {
  flex: 1;
  height: 3px;
  background: var(--color-border);
  margin: 0 var(--spacing-sm);
  position: relative;
  top: -20px;
  transition: background var(--transition-base);
}

.step-divider.completed {
  background: var(--color-primary);
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
