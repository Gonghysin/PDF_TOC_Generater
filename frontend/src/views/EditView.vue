<template>
  <div class="edit-view">
    <BaseCard padding="xl">
      <template #header>
        <div class="card-header-content">
          <button class="back-btn" @click="$emit('back')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M19 12H5M12 19l-7-7 7-7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            返回
          </button>
          <h2>审核并编辑目录</h2>
          <div class="mode-switch">
            <button
              :class="['mode-btn', { active: editorMode === 'structured' }]"
              @click="editorMode = 'structured'"
            >
              结构化编辑
            </button>
            <button
              :class="['mode-btn', { active: editorMode === 'text' }]"
              @click="editorMode = 'text'"
            >
              文本编辑
            </button>
          </div>
        </div>
      </template>

      <div class="edit-container">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="loadError" class="error-state">
          <p class="error-message">{{ loadError }}</p>
          <button class="btn-retry" @click="loadTaskDetail">重试</button>
        </div>

        <template v-else>
          <div class="edit-info">
            <p>请仔细审核识别出的目录内容，确认无误后点击"生成 PDF"按钮。</p>
            <p class="edit-hint">
              提示：{{ editorMode === 'structured' ? '使用结构化编辑器可以拖拽排序、调整层级和页码' : '可以直接编辑文本框中的内容来修改目录' }}
            </p>
          </div>

          <!-- 结构化编辑模式 -->
          <div v-if="editorMode === 'structured'" class="structured-editor">
            <TOCEditor
              v-if="tocEntries.length > 0"
              :toc-entries="tocEntries"
              :initial-page-offset="pageOffset"
              @save="handleStructuredSave"
              @cancel="handleCancel"
            />
            <div v-else class="empty-state">
              <p>暂无目录条目</p>
            </div>
          </div>

          <!-- 文本编辑模式 -->
          <div v-else class="text-editor">
            <div class="editor-toolbar">
              <span class="editor-label">目录内容</span>
              <button class="toolbar-btn" @click="saveTextEdit" :disabled="saving">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" stroke-width="2"/>
                  <polyline points="17 21 17 13 7 13 7 21" stroke-width="2"/>
                  <polyline points="7 3 7 8 15 8" stroke-width="2"/>
                </svg>
                {{ saving ? '保存中...' : '保存编辑' }}
              </button>
            </div>

            <textarea
              v-model="editedText"
              class="editor-textarea"
              :readonly="saving || generating"
              spellcheck="false"
            ></textarea>

            <div v-if="saveSuccess" class="success-message">
              保存成功！目录已更新。
            </div>

            <div class="action-buttons">
              <BaseButton
                variant="secondary"
                size="lg"
                @click="resetTextEdit"
                :disabled="saving || generating"
              >
                重置
              </BaseButton>

              <BaseButton
                variant="primary"
                size="lg"
                :loading="generating"
                @click="generatePDF"
              >
                {{ generating ? '生成中...' : '生成 PDF' }}
              </BaseButton>
            </div>
          </div>

          <div v-if="error" class="error-message">
            {{ error }}
          </div>
        </template>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import TOCEditor from '../components/TOCEditor.vue'
import api from '../services/api.js'

export default {
  name: 'EditView',
  components: {
    BaseCard,
    BaseButton,
    TOCEditor
  },
  props: {
    taskId: {
      type: String,
      required: true
    },
    tocText: {
      type: String,
      default: ''
    },
    isHistoryTask: {
      type: Boolean,
      default: false
    }
  },
  emits: ['completed', 'back'],
  setup(props, { emit }) {
    // 状态
    const editorMode = ref('structured')
    const loading = ref(false)
    const loadError = ref('')
    const tocEntries = ref([])
    const pageOffset = ref(0)
    const editedText = ref(props.tocText)
    const originalText = ref(props.tocText)
    const saving = ref(false)
    const generating = ref(false)
    const saveSuccess = ref(false)
    const error = ref('')

    // 加载任务详情
    const loadTaskDetail = async () => {
      loading.value = true
      loadError.value = ''

      try {
        const response = await api.getTaskDetail(props.taskId)

        tocEntries.value = response.toc_entries || []
        pageOffset.value = response.task.page_offset || 0
        editedText.value = response.toc_text || props.tocText
        originalText.value = editedText.value
      } catch (err) {
        console.error('加载任务详情失败:', err)
        loadError.value = err.message

        // 如果加载失败，尝试使用传入的文本
        if (props.tocText) {
          editedText.value = props.tocText
          originalText.value = props.tocText
          editorMode.value = 'text' // 切换到文本模式
        }
      } finally {
        loading.value = false
      }
    }

    // 处理结构化编辑保存
    const handleStructuredSave = async (data) => {
      try {
        saving.value = true
        error.value = ''

        const response = await api.updateStructuredTOC(
          props.taskId,
          data.entries,
          data.pageOffset
        )

        // 更新本地数据
        tocEntries.value = response.entries.map((entry, index) => ({
          title: entry.title,
          level: entry.level,
          page: entry.pdf_page
        }))
        pageOffset.value = data.pageOffset
        editedText.value = response.toc_text
        originalText.value = response.toc_text

        saveSuccess.value = true
        setTimeout(() => {
          saveSuccess.value = false
        }, 2000)

        // 直接生成PDF
        await generatePDF()
      } catch (err) {
        error.value = err.message || '保存失败'
      } finally {
        saving.value = false
      }
    }

    // 处理取消
    const handleCancel = () => {
      emit('back')
    }

    // 保存文本编辑
    const saveTextEdit = async () => {
      if (editedText.value === originalText.value) {
        saveSuccess.value = true
        setTimeout(() => {
          saveSuccess.value = false
        }, 2000)
        return
      }

      try {
        saving.value = true
        error.value = ''
        saveSuccess.value = false

        await api.editTOC(props.taskId, editedText.value)

        originalText.value = editedText.value
        saveSuccess.value = true

        setTimeout(() => {
          saveSuccess.value = false
        }, 2000)
      } catch (err) {
        error.value = err.message || '保存失败'
      } finally {
        saving.value = false
      }
    }

    // 重置文本编辑
    const resetTextEdit = () => {
      editedText.value = originalText.value
      error.value = ''
      saveSuccess.value = false
    }

    // 生成 PDF
    const generatePDF = async () => {
      try {
        generating.value = true
        error.value = ''

        // 如果在文本模式且有未保存的修改，先保存
        if (editorMode.value === 'text' && editedText.value !== originalText.value) {
          await api.editTOC(props.taskId, editedText.value)
          originalText.value = editedText.value
        }

        const response = await api.writeTOCToPDF(props.taskId)

        emit('completed', response.download_url)
      } catch (err) {
        error.value = err.message || '生成 PDF 失败'
      } finally {
        generating.value = false
      }
    }

    // 组件挂载时加载
    onMounted(async () => {
      // 无论新任务还是历史任务，都尝试从数据库加载
      // 因为新任务完成 OCR 后，TOC 条目已经保存到数据库
      try {
        await loadTaskDetail()

        // 如果成功加载到条目，默认使用结构化编辑器
        if (tocEntries.value.length > 0) {
          editorMode.value = 'structured'
        } else {
          // 如果没有条目但有文本，使用文本编辑器
          editorMode.value = 'text'
        }
      } catch (err) {
        // 如果加载失败，回退到文本模式
        editedText.value = props.tocText
        originalText.value = props.tocText
        editorMode.value = 'text'
      }
    })

    return {
      editorMode,
      loading,
      loadError,
      tocEntries,
      pageOffset,
      editedText,
      saving,
      generating,
      saveSuccess,
      error,
      loadTaskDetail,
      handleStructuredSave,
      handleCancel,
      saveTextEdit,
      resetTextEdit,
      generatePDF
    }
  }
}
</script>

<style scoped>
.card-header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.card-header-content h2 {
  flex: 1;
}

.mode-switch {
  display: flex;
  border: 1px solid var(--color-black);
  overflow: hidden;
}

.mode-btn {
  padding: 8px 16px;
  border: none;
  background: var(--color-white);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
  border-right: 1px solid var(--color-black);
}

.mode-btn:last-child {
  border-right: none;
}

.mode-btn.active {
  background: var(--color-orange);
  color: var(--color-white);
}

.mode-btn:hover:not(.active) {
  background: var(--color-beige);
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

.btn-retry {
  padding: 10px 20px;
  border: 1px solid var(--color-black);
  background: var(--color-orange);
  color: var(--color-white);
  font-family: var(--font-family);
  cursor: pointer;
}

.edit-info {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-beige);
  border-radius: var(--radius-md);
}

.edit-info p {
  font-size: var(--font-size-base);
  color: var(--color-black);
  margin-bottom: var(--spacing-xs);
}

.edit-info p:last-child {
  margin-bottom: 0;
}

.edit-hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.structured-editor {
  margin-bottom: var(--spacing-lg);
}

.text-editor {
  margin-bottom: var(--spacing-lg);
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border);
}

.editor-label {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-black);
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-black);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--color-beige);
  border-color: var(--color-primary);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.editor-textarea {
  width: 100%;
  min-height: 400px;
  padding: var(--spacing-md);
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  line-height: 1.8;
  color: var(--color-black);
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.editor-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

.editor-textarea:read-only {
  background: var(--color-gray-100);
  cursor: not-allowed;
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

.success-message {
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: #EFE;
  border: 1px solid #CFC;
  border-radius: var(--radius-md);
  color: #3C3;
  font-size: var(--font-size-sm);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
}

.action-buttons > * {
  min-width: 140px;
}
</style>
