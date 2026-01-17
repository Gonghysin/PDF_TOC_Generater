# PDF 目录生成器 - Web 界面使用指南

## 项目简介

这是一个基于 AI 的 PDF 目录自动识别与添加工具的 Web 版本，提供了简约优雅的用户界面，采用 Anthropic 风格设计。

## 技术栈

### 后端
- **FastAPI**: 高性能的 Python Web 框架
- **Uvicorn**: ASGI 服务器
- **现有项目**: 基于 LangGraph 和 Claude 的 OCR 识别系统

### 前端
- **Vue 3**: 渐进式 JavaScript 框架
- **Vite**: 新一代前端构建工具
- **原生 CSS**: 使用 CSS 变量实现 Anthropic 风格设计

## 设计特点

### 配色方案
- **黑色** (#000000): 主要文字和轮廓
- **白色** (#FFFFFF): 主要背景和表面
- **米白** (#F5F5F0): 次要背景色
- **橙色** (#FF6B35): 强调色和交互元素

### 字体
- **思源宋体** (Noto Serif SC): 优雅的中文衬线字体

### 界面风格
- 简约大气的设计
- 清晰的视觉层次
- 流畅的交互体验

## 安装与启动

### 1. 安装后端依赖

```bash
# 在项目根目录下
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

### 3. 配置环境变量

确保根目录的 `.env` 文件已正确配置：

```env
# API 配置
API_BASE_URL=https://openrouter.ai/api/v1
API_KEY=your_api_key_here
MODEL_NAME=anthropic/claude-3.5-sonnet

# 代理配置（可选）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 4. 启动后端服务

```bash
# 在项目根目录下
python app.py
```

后端服务将启动在 `http://localhost:8000`

你可以访问 `http://localhost:8000/docs` 查看 API 文档

### 5. 启动前端开发服务器

```bash
# 在 frontend 目录下
npm run dev
```

前端服务将启动在 `http://localhost:3000`

## 使用流程

### 第一步：上传 PDF

1. 打开浏览器访问 `http://localhost:3000`
2. 在上传页面，可以通过以下方式上传 PDF：
   - 点击"点击选择文件"按钮选择文件
   - 直接拖拽 PDF 文件到上传区域
3. 确认文件信息无误后，点击"开始上传"

### 第二步：配置处理参数

1. 查看 PDF 基本信息（总页数、文件大小等）
2. 填写配置参数：
   - **目录页范围**: 填写目录所在的页码范围，例如 "5-12"
   - **页码偏置**: PDF 显示页码与实际页码的差值（通常为 0）
   - **并行处理**: 勾选后会使用并行处理，速度更快但消耗更多资源
3. 点击"开始识别"

### 第三步：等待处理完成

系统会自动进行以下步骤：
1. 提取目录页图片
2. AI 识别目录内容
3. 合并目录数据

处理过程中会显示实时进度和当前步骤。

### 第四步：审核并编辑目录

1. 查看识别出的目录内容
2. 如有错误，可以直接在文本框中编辑
3. 点击"保存编辑"保存修改
4. 确认无误后，点击"生成 PDF"

### 第五步：下载结果

1. 处理完成后，点击"下载 PDF"按钮
2. 下载的 PDF 文件已包含完整的目录书签
3. 可以在 PDF 阅读器中使用目录功能

## API 接口说明

### 上传文件
```
POST /api/upload
Content-Type: multipart/form-data

Body:
  file: PDF 文件

Response:
{
  "file_id": "uuid",
  "filename": "文件名.pdf",
  "path": "文件路径",
  "size": 文件大小（字节）
}
```

### 获取 PDF 信息
```
GET /api/pdf/info?pdf_path=文件路径

Response:
{
  "total_pages": 总页数,
  "has_toc": 是否已有目录,
  "file_size": 文件大小,
  "filename": 文件名
}
```

### 启动 OCR 任务
```
POST /api/ocr/start
Content-Type: multipart/form-data

Body:
  pdf_path: PDF 文件路径
  page_range: 页码范围（例如: "5-12"）
  page_offset: 页码偏置
  parallel: 是否并行处理

Response:
{
  "task_id": "任务ID",
  "status": "pending",
  "message": "任务已创建"
}
```

### 获取任务状态
```
GET /api/task/status/{task_id}

Response:
{
  "task_id": "任务ID",
  "status": "processing | completed | failed",
  "progress": 0-100,
  "message": "状态消息",
  "result": {...}
}
```

### 编辑目录
```
POST /api/toc/edit
Content-Type: application/json

Body:
{
  "task_id": "任务ID",
  "toc_text": "编辑后的目录文本"
}

Response:
{
  "success": true,
  "message": "目录已更新",
  "toc_preview": {...}
}
```

### 写入 PDF
```
POST /api/toc/write
Content-Type: multipart/form-data

Body:
  task_id: 任务ID
  output_filename: 输出文件名（可选）

Response:
{
  "success": true,
  "output_path": "输出文件路径",
  "download_url": "下载URL"
}
```

### 下载文件
```
GET /api/download/{filename}

Response: PDF 文件流
```

## 生产环境部署

### 构建前端

```bash
cd frontend
npm run build
```

构建后的文件在 `frontend/dist` 目录下。

### 部署后端

可以使用 Gunicorn 或其他 ASGI 服务器：

```bash
# 使用 Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# 或使用 Uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 常见问题

### Q: 上传文件大小限制是多少？
A: 默认限制为 100MB，可以在前端 UploadView.vue 中修改。

### Q: OCR 识别速度慢怎么办？
A: 可以勾选"并行处理"选项，或者调整 API 的并发参数。

### Q: 如何修改配色方案？
A: 在 `frontend/src/styles/global.css` 中修改 CSS 变量即可。

### Q: 支持哪些浏览器？
A: 支持所有现代浏览器（Chrome、Firefox、Safari、Edge 最新版本）。

## 项目结构

```
.
├── app.py                 # FastAPI 后端服务
├── config.py             # 配置管理
├── models.py             # 数据模型
├── main.py               # 原有的命令行工具
├── requirements.txt      # Python 依赖
├── frontend/             # 前端项目
│   ├── index.html       # HTML 入口
│   ├── package.json     # NPM 配置
│   ├── vite.config.js   # Vite 配置
│   └── src/
│       ├── main.js      # Vue 入口
│       ├── App.vue      # 主组件
│       ├── components/  # UI 组件
│       │   ├── BaseButton.vue
│       │   ├── BaseCard.vue
│       │   └── ProgressBar.vue
│       ├── views/       # 页面视图
│       │   ├── UploadView.vue
│       │   ├── ProcessView.vue
│       │   ├── EditView.vue
│       │   └── CompleteView.vue
│       ├── services/    # API 服务
│       │   └── api.js
│       └── styles/      # 样式文件
│           └── global.css
└── uploads/             # 上传文件存储（自动创建）
```

## 许可证

本项目采用 MIT 许可证。

## 致谢

- Anthropic Claude: AI 识别引擎
- LangGraph: 工作流编排
- Vue 3: 前端框架
- FastAPI: 后端框架
