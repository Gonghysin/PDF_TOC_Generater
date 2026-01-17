<template>
  <button :class="buttonClasses" :disabled="disabled || loading" @click="handleClick">
    <span v-if="loading" class="btn-loader"></span>
    <slot v-else></slot>
  </button>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'BaseButton',
  props: {
    variant: {
      type: String,
      default: 'primary',
      validator: (value) => ['primary', 'secondary', 'outline'].includes(value)
    },
    size: {
      type: String,
      default: 'md',
      validator: (value) => ['sm', 'md', 'lg'].includes(value)
    },
    disabled: {
      type: Boolean,
      default: false
    },
    loading: {
      type: Boolean,
      default: false
    },
    fullWidth: {
      type: Boolean,
      default: false
    }
  },
  emits: ['click'],
  setup(props, { emit }) {
    const buttonClasses = computed(() => ({
      'btn': true,
      [`btn-${props.variant}`]: true,
      [`btn-${props.size}`]: true,
      'btn-full-width': props.fullWidth,
      'btn-loading': props.loading
    }))

    const handleClick = (event) => {
      if (!props.disabled && !props.loading) {
        emit('click', event)
      }
    }

    return {
      buttonClasses,
      handleClick
    }
  }
}
</script>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-family);
  font-weight: 500;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  outline: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 尺寸 */
.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.btn-md {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
}

.btn-lg {
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-lg);
}

/* 变体 */
.btn-primary {
  background: var(--color-primary);
  color: var(--color-white);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-primary:active:not(:disabled) {
  background: var(--color-primary-active);
  transform: translateY(0);
}

.btn-secondary {
  background: var(--color-white);
  color: var(--color-black);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-gray-100);
  border-color: var(--color-gray-400);
}

.btn-outline {
  background: transparent;
  color: var(--color-black);
  border: 2px solid var(--color-black);
}

.btn-outline:hover:not(:disabled) {
  background: var(--color-black);
  color: var(--color-white);
}

/* 全宽 */
.btn-full-width {
  width: 100%;
}

/* 加载动画 */
.btn-loader {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-white);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
