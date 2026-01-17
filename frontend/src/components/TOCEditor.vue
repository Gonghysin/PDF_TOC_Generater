<template>
  <div class="toc-editor">
    <div class="editor-header">
      <h3>结构化目录编辑</h3>
      <div class="header-actions">
        <button class="btn-icon" @click="undo" :disabled="!canUndo" title="撤销 (Ctrl+Z)">
          ↶
        </button>
        <button class="btn-icon" @click="redo" :disabled="!canRedo" title="重做 (Ctrl+Y)">
          ↷
        </button>
        <button class="btn-add" @click="addEntry">
          + 添加条目
        </button>
      </div>
    </div>

    <div class="editor-config">
      <label class="config-label">
        <span class="config-label-text">页码偏置设置：</span>
        <input
          type="number"
          v-model.number="pageOffset"
          @change="recalculatePdfPages"
          class="config-input"
          min="1"
        />
        <span class="config-hint">书籍第1页对应PDF文件第 {{ pageOffset }} 页</span>
      </label>
      <p class="config-note">提示：书籍页码可以是负数（摘要、前言等），PDF页码必须大于0。修改任一页码后会自动排序。</p>
    </div>

    <div class="table-container">
      <table class="toc-table">
        <thead>
          <tr>
            <th class="col-level">层级</th>
            <th class="col-title">标题</th>
            <th class="col-book-page">书籍页码 <span class="th-hint">（可为负数）</span></th>
            <th class="col-pdf-page">PDF页码 <span class="th-hint">（必须≥1）</span></th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(element, index) in sortedEntries" :key="element.id">
            <td class="col-level">
              <select
                v-model.number="element.level"
                @change="saveHistory"
                class="level-select"
              >
                <option :value="1">一级</option>
                <option :value="2">二级</option>
                <option :value="3">三级</option>
                <option :value="4">四级</option>
                <option :value="5">五级</option>
              </select>
            </td>
            <td class="col-title">
              <input
                v-model="element.title"
                @blur="saveHistory"
                @keydown.enter="saveHistory"
                class="title-input"
                :style="{ paddingLeft: (element.level - 1) * 20 + 'px' }"
                placeholder="输入标题"
              />
            </td>
            <td class="col-book-page">
              <input
                type="number"
                v-model.number="element.bookPage"
                @change="updatePdfPage(element)"
                class="page-input"
                placeholder="可为负数"
              />
            </td>
            <td class="col-pdf-page">
              <input
                type="number"
                v-model.number="element.pdfPage"
                @change="updateBookPage(element)"
                class="page-input"
                min="1"
              />
            </td>
            <td class="col-actions">
              <button
                class="btn-delete"
                @click="deleteEntry(index)"
                title="删除"
              >
                ✕
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="editor-footer">
      <div class="entry-count">
        共 {{ entries.length }} 个条目
      </div>
      <div class="footer-actions">
        <button class="btn-secondary" @click="$emit('cancel')">
          取消
        </button>
        <button class="btn-primary" @click="saveChanges">
          保存修改
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  tocEntries: {
    type: Array,
    required: true
  },
  initialPageOffset: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['save', 'cancel'])

// 状态
let nextId = 1
const entries = ref([])
const pageOffset = ref(props.initialPageOffset)
const editingId = ref(null)

// 撤销/重做历史
const history = ref([])
const historyIndex = ref(-1)

// 自动按PDF页码排序的条目列表
const sortedEntries = computed(() => {
  return [...entries.value].sort((a, b) => a.pdfPage - b.pdfPage)
})

// 初始化条目
const initializeEntries = () => {
  entries.value = props.tocEntries.map((entry, index) => ({
    id: nextId++,
    title: entry.title,
    level: entry.level,
    bookPage: entry.page - (props.initialPageOffset - 1), // 反推书籍页码
    pdfPage: entry.page,
    orderIndex: index
  }))

  // 保存初始状态到历史
  saveHistory()
}

// 计算属性
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

// 保存历史状态
const saveHistory = () => {
  // 移除当前位置之后的历史
  history.value = history.value.slice(0, historyIndex.value + 1)

  // 添加新状态
  history.value.push(JSON.parse(JSON.stringify(entries.value)))
  historyIndex.value = history.value.length - 1

  // 限制历史记录数量
  if (history.value.length > 50) {
    history.value.shift()
    historyIndex.value--
  }
}

// 撤销
const undo = () => {
  if (canUndo.value) {
    historyIndex.value--
    entries.value = JSON.parse(JSON.stringify(history.value[historyIndex.value]))
  }
}

// 重做
const redo = () => {
  if (canRedo.value) {
    historyIndex.value++
    entries.value = JSON.parse(JSON.stringify(history.value[historyIndex.value]))
  }
}

// 从书籍页码更新 PDF 页码
const updatePdfPage = (entry) => {
  entry.pdfPage = entry.bookPage + (pageOffset.value - 1)
  saveHistory()
}

// 从 PDF 页码更新书籍页码
const updateBookPage = (entry) => {
  entry.bookPage = entry.pdfPage - (pageOffset.value - 1)
  saveHistory()
}

// 重新计算所有 PDF 页码（页码偏置改变时）
const recalculatePdfPages = () => {
  entries.value.forEach(entry => {
    entry.pdfPage = entry.bookPage + (pageOffset.value - 1)
  })
  saveHistory()
}

// 添加条目
const addEntry = () => {
  const newEntry = {
    id: nextId++,
    title: '',
    level: 1,
    bookPage: 1,
    pdfPage: pageOffset.value,
    orderIndex: entries.value.length
  }
  entries.value.push(newEntry)
  saveHistory()
}

// 删除条目
const deleteEntry = (index) => {
  // 注意：index 是 sortedEntries 的索引，需要找到原始 entries 中的对应项
  const sortedItem = sortedEntries.value[index]
  const originalIndex = entries.value.findIndex(e => e.id === sortedItem.id)
  if (originalIndex !== -1) {
    entries.value.splice(originalIndex, 1)
    saveHistory()
  }
}

// 保存修改
const saveChanges = () => {
  // 验证数据
  for (const entry of entries.value) {
    if (!entry.title.trim()) {
      alert('请填写所有标题')
      return
    }
    // 只验证PDF页码，书籍页码可以是负数
    if (entry.pdfPage < 1) {
      alert(`条目"${entry.title}"的PDF页码必须大于0（当前值：${entry.pdfPage}）`)
      return
    }
  }

  // 转换为API格式，按PDF页码排序
  const sortedByPdf = [...entries.value].sort((a, b) => a.pdfPage - b.pdfPage)
  const entriesForApi = sortedByPdf.map((entry, index) => ({
    title: entry.title,
    level: entry.level,
    book_page: entry.bookPage,
    order_index: index
  }))

  emit('save', {
    entries: entriesForApi,
    pageOffset: pageOffset.value
  })
}

// 键盘快捷键
const handleKeyboard = (e) => {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z') {
      e.preventDefault()
      undo()
    } else if (e.key === 'y') {
      e.preventDefault()
      redo()
    }
  }
}

// 监听页码偏置变化
watch(() => props.initialPageOffset, (newVal) => {
  pageOffset.value = newVal
})

// 生命周期
onMounted(() => {
  initializeEntries()
  window.addEventListener('keydown', handleKeyboard)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboard)
})
</script>

<style scoped>
.toc-editor {
  border: 1px solid var(--color-black);
  background: var(--color-white);
  padding: 24px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.editor-header h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-icon {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  font-size: 18px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-icon:hover:not(:disabled) {
  background: var(--color-beige);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-add {
  padding: 8px 16px;
  border: 1px solid var(--color-black);
  background: var(--color-orange);
  color: var(--color-white);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-add:hover {
  background: #E85A2A;
}

.editor-config {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--color-beige);
}

.config-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
}

.config-label-text {
  font-weight: 600;
  color: var(--color-black);
}

.config-input {
  width: 80px;
  padding: 6px 8px;
  border: 1px solid var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
}

.config-hint {
  color: rgba(0, 0, 0, 0.6);
  font-size: 13px;
}

.config-note {
  margin-top: 8px;
  margin-bottom: 0;
  color: rgba(0, 0, 0, 0.5);
  font-size: 12px;
}

.table-container {
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid var(--color-black);
  margin-bottom: 20px;
}

.toc-table {
  width: 100%;
  border-collapse: collapse;
}

.toc-table thead {
  position: sticky;
  top: 0;
  background: var(--color-beige);
  z-index: 10;
}

.toc-table th {
  padding: 12px 8px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid var(--color-black);
}

.th-hint {
  font-weight: 400;
  font-size: 11px;
  color: rgba(0, 0, 0, 0.5);
}

.toc-table td {
  padding: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.toc-table tbody tr:hover {
  background: rgba(255, 107, 53, 0.05);
}

.toc-table tbody tr.row-editing {
  background: rgba(255, 107, 53, 0.1);
}

.col-level { width: 100px; }
.col-title { width: auto; min-width: 200px; }
.col-book-page { width: 120px; }
.col-pdf-page { width: 120px; }
.col-actions { width: 80px; text-align: center; }

.level-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--color-black);
  background: var(--color-white);
  font-family: var(--font-family);
  font-size: 13px;
  cursor: pointer;
}

.title-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid transparent;
  background: transparent;
  font-family: var(--font-family);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.title-input:focus {
  border-color: var(--color-orange);
  background: var(--color-white);
  outline: none;
}

.page-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid transparent;
  background: transparent;
  font-family: var(--font-family);
  font-size: 13px;
  text-align: center;
  transition: all var(--transition-fast);
}

.page-input:focus {
  border-color: var(--color-orange);
  background: var(--color-white);
  outline: none;
}

.btn-delete {
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  background: transparent;
  color: #F44336;
  font-size: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-delete:hover {
  border-color: #F44336;
  background: rgba(244, 67, 54, 0.1);
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.entry-count {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.btn-secondary,
.btn-primary {
  padding: 10px 24px;
  border: 1px solid var(--color-black);
  font-family: var(--font-family);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-secondary {
  background: var(--color-white);
  color: var(--color-black);
}

.btn-secondary:hover {
  background: var(--color-beige);
}

.btn-primary {
  background: var(--color-orange);
  border-color: var(--color-orange);
  color: var(--color-white);
}

.btn-primary:hover {
  background: #E85A2A;
  border-color: #E85A2A;
}
</style>
