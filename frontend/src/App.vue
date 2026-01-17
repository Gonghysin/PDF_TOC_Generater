<template>
  <div class="app">
    <header class="app-header">
      <div class="container">
        <h1 class="app-title">PDF 目录生成器</h1>
        <p class="app-subtitle">基于 AI 的 PDF 目录自动识别与添加工具</p>
        <button
          v-if="currentStep === 'upload'"
          class="btn-history"
          @click="currentStep = 'history'"
        >
          查看历史
        </button>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <HistoryView
          v-if="currentStep === 'history'"
          @back="currentStep = 'upload'"
          @edit="handleEditHistoryTask"
        />

        <UploadView
          v-else-if="currentStep === 'upload'"
          @uploaded="handleUploaded"
        />

        <ProcessView
          v-else-if="currentStep === 'process'"
          :pdf-info="pdfInfo"
          @started="handleProcessStarted"
          @back="currentStep = 'upload'"
        />

        <EditView
          v-else-if="currentStep === 'edit'"
          :task-id="taskId"
          :toc-text="tocText"
          :is-history-task="isHistoryTask"
          @completed="handleCompleted"
          @back="handleEditBack"
        />

        <CompleteView
          v-else-if="currentStep === 'complete'"
          :download-url="downloadUrl"
          @restart="handleRestart"
        />
      </div>
    </main>

    <footer class="app-footer">
      <div class="container">
        <p>Powered by Anthropic Claude & LangGraph</p>
      </div>
    </footer>
  </div>
</template>

<script>
import { ref } from 'vue'
import HistoryView from './views/HistoryView.vue'
import UploadView from './views/UploadView.vue'
import ProcessView from './views/ProcessView.vue'
import EditView from './views/EditView.vue'
import CompleteView from './views/CompleteView.vue'
import api from './services/api'

export default {
  name: 'App',
  components: {
    HistoryView,
    UploadView,
    ProcessView,
    EditView,
    CompleteView
  },
  setup() {
    const currentStep = ref('upload')
    const pdfInfo = ref(null)
    const taskId = ref(null)
    const tocText = ref('')
    const downloadUrl = ref('')
    const isHistoryTask = ref(false)

    const handleUploaded = (info) => {
      pdfInfo.value = info
      currentStep.value = 'process'
      isHistoryTask.value = false
    }

    const handleProcessStarted = (data) => {
      taskId.value = data.taskId
      tocText.value = data.tocText
      currentStep.value = 'edit'
      isHistoryTask.value = false
    }

    const handleEditHistoryTask = async (historyTaskId) => {
      try {
        // 加载历史任务的详情
        const response = await api.getTaskDetail(historyTaskId)

        taskId.value = historyTaskId
        tocText.value = response.toc_text || ''
        isHistoryTask.value = true
        currentStep.value = 'edit'
      } catch (err) {
        console.error('加载历史任务失败:', err)
        alert(`加载任务失败: ${err.message}`)
      }
    }

    const handleCompleted = (url) => {
      downloadUrl.value = url
      currentStep.value = 'complete'
    }

    const handleEditBack = () => {
      if (isHistoryTask.value) {
        currentStep.value = 'history'
      } else {
        currentStep.value = 'process'
      }
    }

    const handleRestart = () => {
      currentStep.value = 'upload'
      pdfInfo.value = null
      taskId.value = null
      tocText.value = ''
      downloadUrl.value = ''
      isHistoryTask.value = false
    }

    return {
      currentStep,
      pdfInfo,
      taskId,
      tocText,
      downloadUrl,
      isHistoryTask,
      handleUploaded,
      handleProcessStarted,
      handleEditHistoryTask,
      handleCompleted,
      handleEditBack,
      handleRestart
    }
  }
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: var(--color-white);
  border-bottom: 1px solid var(--color-border);
  padding: var(--spacing-xl) 0;
}

.app-header .container {
  position: relative;
}

.app-title {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-black);
  margin-bottom: var(--spacing-xs);
}

.app-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  font-weight: 400;
}

.btn-history {
  position: absolute;
  top: 0;
  right: 0;
  padding: 10px 20px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  color: var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-history:hover {
  background: var(--color-beige);
}

.app-main {
  flex: 1;
  padding: var(--spacing-2xl) 0;
}

.app-footer {
  background: var(--color-white);
  border-top: 1px solid var(--color-border);
  padding: var(--spacing-lg) 0;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
</style>
