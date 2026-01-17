<template>
  <div class="pagination" v-if="totalPages > 1">
    <button
      class="pagination-btn"
      :disabled="currentPage === 1"
      @click="goToPage(currentPage - 1)"
    >
      上一页
    </button>

    <div class="pagination-pages">
      <button
        v-for="page in visiblePages"
        :key="page"
        class="pagination-page"
        :class="{ active: page === currentPage }"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>
    </div>

    <button
      class="pagination-btn"
      :disabled="currentPage === totalPages"
      @click="goToPage(currentPage + 1)"
    >
      下一页
    </button>

    <div class="pagination-info">
      共 {{ total }} 项，第 {{ currentPage }} / {{ totalPages }} 页
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: {
    type: Number,
    required: true
  },
  pageSize: {
    type: Number,
    default: 20
  },
  currentPage: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['update:currentPage'])

const totalPages = computed(() => {
  return Math.ceil(props.total / props.pageSize)
})

// 计算可见的页码按钮
const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5
  let start = Math.max(1, props.currentPage - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)

  // 调整起始位置
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value && page !== props.currentPage) {
    emit('update:currentPage', page)
  }
}
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 32px;
  padding: 16px;
}

.pagination-btn,
.pagination-page {
  padding: 8px 16px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  color: var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.pagination-btn:hover:not(:disabled),
.pagination-page:hover:not(.active) {
  background: var(--color-beige);
}

.pagination-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 4px;
}

.pagination-page.active {
  background: var(--color-orange);
  color: var(--color-white);
  border-color: var(--color-orange);
}

.pagination-info {
  margin-left: 12px;
  font-size: 14px;
  color: var(--color-black);
  opacity: 0.6;
}
</style>
