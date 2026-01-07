# 安装指南

## 系统要求

- Python 3.11+
- Git
- Conda（推荐）或 venv

## 安装步骤

### 1. 克隆仓库

```bash
git clone git@github.com:Gonghysin/PDF_TOC_Generater.git
cd PDF_TOC_Generater
```

### 2. 创建虚拟环境

#### 使用 Conda（推荐）

```bash
conda create -n pdf-toc python=3.11
conda activate pdf-toc
```

#### 使用 venv

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenRouter API 配置
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# 可选配置
TEMPERATURE=0.1
MAX_TOKENS=4000
```

### 5. 验证安装

```bash
python main.py --help
```

应显示帮助信息。

## 获取 API Key

1. 访问 [OpenRouter](https://openrouter.ai/)
2. 注册账号
3. 在 Dashboard 创建 API Key
4. 充值账户（按使用量计费）

## 桌面启动（macOS）

使用提供的启动脚本：

```bash
# 脚本路径：Desktop/启动PDF目录工具.sh
./启动PDF目录工具.sh
```

脚本会自动激活环境并启动应用。

## 故障排查

### 依赖安装失败

确保使用 Python 3.11+：
```bash
python --version
```

### API 连接失败

检查 `.env` 文件配置是否正确，测试网络连接。

### 模块导入错误

确认已激活虚拟环境：
```bash
which python  # 应指向虚拟环境
```

## 卸载

```bash
# 删除虚拟环境
conda env remove -n pdf-toc
# 或
rm -rf venv

# 删除项目目录
rm -rf PDF_TOC_Generater
```
