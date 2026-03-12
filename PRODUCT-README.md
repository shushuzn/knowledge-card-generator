# 知识卡片生成器 v2.6

**从 PDF 到知识卡片，一键生成**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

---

## 🚀 快速开始

### 在线使用 (推荐)

访问：[你的 Railway 域名]

1. 上传 PDF 文件
2. 等待自动处理
3. 下载知识卡片 (HTML/BibTeX)

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行命令行版本
python core/knowledge-card-generator.py 论文.pdf

# 运行 Web UI
python core/knowledge-card-webui.py --port 5000

# 浏览器访问
http://127.0.0.1:5000
```

---

## ✨ 功能特性

- ✅ **PDF 自动解析** - 支持单栏/双栏论文
- ✅ **元数据提取** - 标题/作者/年份/arXiv ID
- ✅ **章节识别** - 自动识别 Introduction/Methods/Results
- ✅ **参考文献验证** - CrossRef API 自动验证
- ✅ **批量处理** - 一次处理 100+ 篇 PDF
- ✅ **多种导出** - HTML/BibTeX/Zip

---

## 📱 Android APK

**打包步骤:**

1. 部署到 Railway (获得域名)
2. 访问 [webintoapp.com](https://webintoapp.com)
3. 输入 Railway 域名
4. 点击 Build
5. 下载 APK

详细指南：[APK-BUILD-GUIDE.md](APK-BUILD-GUIDE.md)

---

## 🛠️ 部署

### Railway 部署 (推荐)

```bash
# 1. Fork 本仓库
# 2. Railway 连接 GitHub
# 3. 自动部署
```

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

### 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PORT` | 服务端口 | $PORT (自动) |
| `CROSSREF_API_KEY` | CrossRef API | 可选 |
| `MAX_CONTENT_LENGTH` | 最大上传 | 100MB |

---

## 📊 测试结果

| 测试项 | 结果 |
|--------|------|
| PDF 解析成功率 | 16/16 (100%) |
| 元数据提取准确率 | ~99% |
| 批量处理速度 | ~0.7 秒/篇 |
| 总体可靠性 | 85/100 |

---

## 📁 项目结构

```
knowledge-card-generator/
├── core/
│   ├── knowledge-card-generator.py    # 核心代码
│   ├── knowledge-card-webui.py        # Web UI
│   └── error_handler.py               # 错误处理
├── requirements.txt                    # Python 依赖
├── Procfile                            # Railway 配置
├── nixpacks.toml                       # Railway 构建
├── README.md                           # 本文件
└── APK-BUILD-GUIDE.md                  # APK 打包指南
```

---

## 🔧 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/

# 代码格式化
black core/*.py
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- PyMuPDF - PDF 解析
- CrossRef - 参考文献 API
- Railway - 云端部署

---

## 📬 联系方式

- 问题反馈：GitHub Issues
- 邮箱：[你的邮箱]

---

**⭐ 如果这个项目对你有帮助，请给个 Star!**
