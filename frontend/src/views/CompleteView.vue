<template>
  <div class="complete-view">
    <BaseCard padding="xl">
      <div class="complete-container">
        <div class="success-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <polyline points="22 4 12 14.01 9 11.01" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <h2 class="complete-title">处理完成</h2>
        <p class="complete-description">
          PDF 目录已成功生成！你可以下载带有目录的新 PDF 文件。
        </p>

        <div class="download-section">
          <BaseButton
            variant="primary"
            size="lg"
            full-width
            @click="downloadFile"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="margin-right: 8px;">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            下载 PDF
          </BaseButton>
        </div>

        <div class="actions-section">
          <BaseButton
            variant="outline"
            size="md"
            @click="$emit('restart')"
          >
            处理新文件
          </BaseButton>
        </div>

        <div class="tips-section">
          <h3 class="tips-title">使用提示</h3>
          <ul class="tips-list">
            <li>下载的 PDF 文件已包含完整的目录书签</li>
            <li>你可以在 PDF 阅读器中通过目录快速跳转到相应章节</li>
            <li>原始 PDF 文件保持不变，生成的是新文件</li>
          </ul>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import BaseCard from '../components/BaseCard.vue'
import BaseButton from '../components/BaseButton.vue'

export default {
  name: 'CompleteView',
  components: {
    BaseCard,
    BaseButton
  },
  props: {
    downloadUrl: {
      type: String,
      required: true
    }
  },
  emits: ['restart'],
  setup(props) {
    const downloadFile = () => {
      window.open(props.downloadUrl, '_blank')
    }

    return {
      downloadFile
    }
  }
}
</script>

<style scoped>
.complete-container {
  text-align: center;
  max-width: 500px;
  margin: 0 auto;
}

.success-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  background: var(--color-beige);
  border-radius: 50%;
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
}

.complete-title {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-black);
  margin-bottom: var(--spacing-sm);
}

.complete-description {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
  line-height: 1.6;
}

.download-section {
  margin-bottom: var(--spacing-lg);
}

.actions-section {
  padding: var(--spacing-lg) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--spacing-lg);
}

.tips-section {
  text-align: left;
  padding: var(--spacing-md);
  background: var(--color-beige);
  border-radius: var(--radius-md);
}

.tips-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-black);
  margin-bottom: var(--spacing-sm);
}

.tips-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tips-list li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding-left: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  position: relative;
}

.tips-list li:last-child {
  margin-bottom: 0;
}

.tips-list li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: var(--color-primary);
  font-weight: bold;
}
</style>
