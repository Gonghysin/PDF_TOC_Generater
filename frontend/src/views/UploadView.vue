<template>
  <div class="upload-view">
    <BaseCard padding="xl">
      <div class="upload-container">
        <div class="upload-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <h2 class="upload-title">上传 PDF 文件</h2>
        <p class="upload-description">
          请选择需要添加目录的 PDF 文件
        </p>

        <div
          class="upload-dropzone"
          :class="{ 'upload-dropzone-active': isDragOver }"
          @drop.prevent="handleDrop"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".pdf"
            class="upload-input"
            @change="handleFileSelect"
          />

          <div class="upload-dropzone-content">
            <p class="upload-dropzone-text">
              拖拽文件到这里，或
              <button class="upload-browse-btn" @click="openFileDialog">
                点击选择文件
              </button>
            </p>
            <p class="upload-dropzone-hint">仅支持 PDF 格式</p>
          </div>
        </div>

        <div v-if="selectedFile" class="upload-file-info">
          <div class="file-info-content">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
            </svg>
            <div class="file-info-details">
              <p class="file-name">{{ selectedFile.name }}</p>
              <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
            </div>
            <button class="file-remove-btn" @click="removeFile">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <line x1="18" y1="6" x2="6" y2="18" stroke-width="2"/>
                <line x1="6" y1="6" x2="18" y2="18" stroke-width="2"/>
              </svg>
            </button>
          </div>
        </div>

        <div v-if="error" class="upload-error">
          {{ error }}
        </div>

        <BaseButton
          v-if="selectedFile"
          variant="primary"
          size="lg"
          full-width
          :loading="uploading"
          @click="uploadFile"
          class="mt-md"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
        </BaseButton>
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
  name: 'UploadView',
  components: {
    BaseCard,
    BaseButton
  },
  emits: ['uploaded'],
  setup(props, { emit }) {
    const fileInput = ref(null)
    const selectedFile = ref(null)
    const isDragOver = ref(false)
    const uploading = ref(false)
    const error = ref('')

    const openFileDialog = () => {
      fileInput.value.click()
    }

    const handleFileSelect = (event) => {
      const file = event.target.files[0]
      if (file) {
        validateAndSetFile(file)
      }
    }

    const handleDrop = (event) => {
      isDragOver.value = false
      const file = event.dataTransfer.files[0]
      if (file) {
        validateAndSetFile(file)
      }
    }

    const validateAndSetFile = (file) => {
      error.value = ''

      if (!file.name.toLowerCase().endsWith('.pdf')) {
        error.value = '仅支持 PDF 格式的文件'
        return
      }

      if (file.size > 100 * 1024 * 1024) {
        error.value = '文件大小不能超过 100MB'
        return
      }

      selectedFile.value = file
    }

    const removeFile = () => {
      selectedFile.value = null
      error.value = ''
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }

    const uploadFile = async () => {
      if (!selectedFile.value) return

      try {
        uploading.value = true
        error.value = ''

        const response = await api.uploadPDF(selectedFile.value)
        const pdfInfo = await api.getPDFInfo(response.path)

        emit('uploaded', {
          ...response,
          ...pdfInfo
        })
      } catch (err) {
        error.value = err.message || '上传失败，请重试'
      } finally {
        uploading.value = false
      }
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    return {
      fileInput,
      selectedFile,
      isDragOver,
      uploading,
      error,
      openFileDialog,
      handleFileSelect,
      handleDrop,
      removeFile,
      uploadFile,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.upload-view {
  max-width: 600px;
  margin: 0 auto;
}

.upload-container {
  text-align: center;
}

.upload-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: var(--color-beige);
  border-radius: 50%;
  color: var(--color-primary);
  margin-bottom: var(--spacing-md);
}

.upload-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-black);
  margin-bottom: var(--spacing-xs);
}

.upload-description {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
}

.upload-dropzone {
  position: relative;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl) var(--spacing-xl);
  transition: all var(--transition-base);
  cursor: pointer;
}

.upload-dropzone:hover,
.upload-dropzone-active {
  border-color: var(--color-primary);
  background: var(--color-beige);
}

.upload-input {
  display: none;
}

.upload-dropzone-text {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.upload-browse-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.upload-browse-btn:hover {
  color: var(--color-primary-hover);
}

.upload-dropzone-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.upload-file-info {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-beige);
  border-radius: var(--radius-md);
}

.file-info-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.file-info-content > svg {
  color: var(--color-primary);
  flex-shrink: 0;
}

.file-info-details {
  flex: 1;
  text-align: left;
}

.file-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-black);
  margin-bottom: 2px;
}

.file-size {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.file-remove-btn {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);
  flex-shrink: 0;
}

.file-remove-btn:hover {
  color: var(--color-primary);
}

.upload-error {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: #FEE;
  border: 1px solid #FCC;
  border-radius: var(--radius-md);
  color: #C33;
  font-size: var(--font-size-sm);
}
</style>
