<template>
  <div :class="cardClasses">
    <div v-if="$slots.header" class="card-header">
      <slot name="header"></slot>
    </div>
    <div class="card-body">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'BaseCard',
  props: {
    padding: {
      type: String,
      default: 'md',
      validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value)
    },
    hoverable: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const cardClasses = computed(() => ({
      'card': true,
      [`card-padding-${props.padding}`]: true,
      'card-hoverable': props.hoverable
    }))

    return {
      cardClasses
    }
  }
}
</script>

<style scoped>
.card {
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.card-hoverable:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-header {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  font-size: var(--font-size-lg);
}

.card-body {
  padding: var(--spacing-lg);
}

.card-padding-sm .card-body {
  padding: var(--spacing-sm);
}

.card-padding-md .card-body {
  padding: var(--spacing-md);
}

.card-padding-lg .card-body {
  padding: var(--spacing-lg);
}

.card-padding-xl .card-body {
  padding: var(--spacing-xl);
}

.card-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  background: var(--color-gray-100);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
</style>
