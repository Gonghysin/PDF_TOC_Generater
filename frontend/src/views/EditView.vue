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
        </div>
      </template>

      <div class="edit-container">
        <div class="edit-info">
          <p>请仔细审核识别出的目录内容，确认无误后点击"生成 PDF"按钮。</p>
          <p class="edit-hint">提示：你可以直接编辑文本框中的内容来修改目录。</p>
        </div>

        <div class="editor-section">
          <div class="editor-toolbar">
            <span class="editor-label">目录内容</span>
            <button class="toolbar-btn" @click="saveEdit" :disabled="saving">
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
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div v-if="saveSuccess" class="success-message">
          保存成功！目录已更新。
        </div>

        <div class="action-buttons">
          <BaseButton
            variant="secondary"
            size="lg"
            @click="resetEdit"
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
    </BaseCard>
  </div>
</template>

<script>
import { ref } from 'vue'
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'
import api from '../services/api.js'

export default {
  name: 'EditView',
  components: {
    BaseCard,
    BaseButton
  },
  props: {
    taskId: {
      type: String,
      required: true
    },
    tocText: {
      type: String,
      required: true
    }
  },
  emits: ['completed', 'back'],
  setup(props, { emit }) {
    const editedText = ref(props.tocText)
    const originalText = ref(props.tocText)
    const saving = ref(false)
    const generating = ref(false)
    const saveSuccess = ref(false)
    const error = ref('')

    const saveEdit = async () => {
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

    const resetEdit = () => {
      editedText.value = originalText.value
      error.value = ''
      saveSuccess.value = false
    }

    const generatePDF = async () => {
      try {
        generating.value = true
        error.value = ''

        // 如果有未保存的修改，先保存
        if (editedText.value !== originalText.value) {
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

    return {
      editedText,
      saving,
      generating,
      saveSuccess,
      error,
      saveEdit,
      resetEdit,
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

.editor-section {
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
