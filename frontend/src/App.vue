<template>
  <div class="app">
    <header class="app-header">
      <div class="container">
        <h1 class="app-title">PDF 目录生成器</h1>
        <p class="app-subtitle">基于 AI 的 PDF 目录自动识别与添加工具</p>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <UploadView
          v-if="currentStep === 'upload'"
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
          @completed="handleCompleted"
          @back="currentStep = 'process'"
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
import UploadView from './views/UploadView.vue'
import ProcessView from './views/ProcessView.vue'
import EditView from './views/EditView.vue'
import CompleteView from './views/CompleteView.vue'

export default {
  name: 'App',
  components: {
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

    const handleUploaded = (info) => {
      pdfInfo.value = info
      currentStep.value = 'process'
    }

    const handleProcessStarted = (data) => {
      taskId.value = data.taskId
      tocText.value = data.tocText
      currentStep.value = 'edit'
    }

    const handleCompleted = (url) => {
      downloadUrl.value = url
      currentStep.value = 'complete'
    }

    const handleRestart = () => {
      currentStep.value = 'upload'
      pdfInfo.value = null
      taskId.value = null
      tocText.value = ''
      downloadUrl.value = ''
    }

    return {
      currentStep,
      pdfInfo,
      taskId,
      tocText,
      downloadUrl,
      handleUploaded,
      handleProcessStarted,
      handleCompleted,
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
