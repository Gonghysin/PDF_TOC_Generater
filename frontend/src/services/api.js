/**
 * API 服务层
 * 与后端 FastAPI 接口通信
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class APIService {
  /**
   * 上传 PDF 文件
   */
  async uploadPDF(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(`上传失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 获取 PDF 信息
   */
  async getPDFInfo(pdfPath) {
    const response = await fetch(
      `${API_BASE_URL}/api/pdf/info?pdf_path=${encodeURIComponent(pdfPath)}`
    )

    if (!response.ok) {
      throw new Error(`获取 PDF 信息失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 启动 OCR 任务
   */
  async startOCRTask(pdfPath, pageRange, pageOffset, parallel = true) {
    const formData = new FormData()
    formData.append('pdf_path', pdfPath)
    formData.append('page_range', pageRange)
    formData.append('page_offset', pageOffset.toString())
    formData.append('parallel', parallel.toString())

    const response = await fetch(`${API_BASE_URL}/api/ocr/start`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(`启动 OCR 任务失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 获取任务状态
   */
  async getTaskStatus(taskId) {
    const response = await fetch(`${API_BASE_URL}/api/task/status/${taskId}`)

    if (!response.ok) {
      throw new Error(`获取任务状态失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 编辑目录
   */
  async editTOC(taskId, tocText) {
    const response = await fetch(`${API_BASE_URL}/api/toc/edit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        task_id: taskId,
        toc_text: tocText
      })
    })

    if (!response.ok) {
      throw new Error(`编辑目录失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 将目录写入 PDF
   */
  async writeTOCToPDF(taskId, outputFilename = null) {
    const formData = new FormData()
    formData.append('task_id', taskId)
    if (outputFilename) {
      formData.append('output_filename', outputFilename)
    }

    const response = await fetch(`${API_BASE_URL}/api/toc/write`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(`写入 PDF 失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 从文本导入目录
   */
  async importFromText(pdfPath, txtContent) {
    const formData = new FormData()
    formData.append('pdf_path', pdfPath)
    formData.append('txt_content', txtContent)

    const response = await fetch(`${API_BASE_URL}/api/import/text`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(`文本导入失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 获取下载链接
   */
  getDownloadURL(filename) {
    return `${API_BASE_URL}/api/download/${filename}`
  }

  /**
   * 获取任务列表
   */
  async getTasks(status = null, page = 1, pageSize = 20) {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString()
    })

    if (status) {
      params.append('status', status)
    }

    const response = await fetch(`${API_BASE_URL}/api/tasks?${params}`)

    if (!response.ok) {
      throw new Error(`获取任务列表失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 获取任务详情
   */
  async getTaskDetail(taskId) {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`)

    if (!response.ok) {
      throw new Error(`获取任务详情失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId) {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error(`删除任务失败: ${response.statusText}`)
    }

    return await response.json()
  }

  /**
   * 更新结构化 TOC
   */
  async updateStructuredTOC(taskId, entries, pageOffset) {
    const response = await fetch(`${API_BASE_URL}/api/toc/update-structured`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        task_id: taskId,
        entries: entries,
        page_offset: pageOffset
      })
    })

    if (!response.ok) {
      throw new Error(`更新结构化 TOC 失败: ${response.statusText}`)
    }

    return await response.json()
  }
}

export default new APIService()
