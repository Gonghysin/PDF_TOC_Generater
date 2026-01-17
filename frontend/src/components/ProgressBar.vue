<template>
  <div class="progress-bar">
    <div class="progress-info">
      <span class="progress-label">{{ label }}</span>
      <span class="progress-percentage">{{ percentage }}%</span>
    </div>
    <div class="progress-track">
      <div
        class="progress-fill"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>
    <div v-if="message" class="progress-message">{{ message }}</div>
  </div>
</template>

<script>
export default {
  name: 'ProgressBar',
  props: {
    percentage: {
      type: Number,
      required: true,
      validator: (value) => value >= 0 && value <= 100
    },
    label: {
      type: String,
      default: '处理进度'
    },
    message: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
.progress-bar {
  width: 100%;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.progress-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.progress-percentage {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-primary);
}

.progress-track {
  width: 100%;
  height: 8px;
  background: var(--color-gray-200);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-hover));
  border-radius: var(--radius-sm);
  transition: width var(--transition-slow);
  animation: shimmer 2s infinite;
}

.progress-message {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
}

@keyframes shimmer {
  0% {
    background-position: -100% 0;
  }
  100% {
    background-position: 100% 0;
  }
}
</style>
