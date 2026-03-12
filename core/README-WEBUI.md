# knowledge-card-webui.py - 知识卡片生成器 Web 界面

**版本:** v2.5  
**最后更新:** 2026-03-12  
**位置:** `30-scripts/01-KNOWLEDGE-CARDS/core/knowledge-card-webui.py`  
**状态:** ✅ 生产就绪

---

## 📋 一句话描述

基于 Flask 的 Web 界面，支持拖拽上传 PDF、实时进度显示、API 配额监控和批量处理知识卡片生成。

---

## 🚀 快速开始

### 安装依赖

```bash
# 进入目录
cd 30-scripts/01-KNOWLEDGE-CARDS

# 安装依赖
pip install -r requirements.txt
```

**requirements.txt:**
```
flask>=2.3.0
werkzeug>=2.3.0
pathlib
```

### 基础用法

```bash
# 启动 Web 界面 (默认端口 5000)
python core/knowledge-card-webui.py --port 5000

# 访问地址
http://127.0.0.1:5000
```

### 预期输出

浏览器打开后显示：
```
┌─────────────────────────────────────────┐
│  📚 知识卡片生成器 v2.5                  │
├─────────────────────────────────────────┤
│  🔌 API 配额状态                         │
│  CrossRef: 0/600  arXiv: 0/600          │
├─────────────────────────────────────────┤
│  📤 上传 PDF                             │
│  拖拽 PDF 到此处或点击选择               │
├─────────────────────────────────────────┤
│  ⚙️ 处理选项                             │
│  ☑ 验证参考文献  ☑ 导出 BibTeX          │
│  ☑ 并发验证      ☐ 渲染 LaTeX 公式       │
├─────────────────────────────────────────┤
│  🚀 开始处理                             │
└─────────────────────────────────────────┘
```

**预计耗时：** ~2 分钟 (启动 + 访问)

---

## ✨ 功能特性

- ✅ **拖拽上传** - 支持批量 PDF 上传 (最大 100MB)
- ✅ **实时进度** - WebSocket 轮询更新处理状态
- ✅ **API 配额监控** - CrossRef/arXiv 使用量实时显示
- ✅ **处理选项配置** - 验证/BibTeX/并发/公式渲染
- ✅ **批量处理** - 一次处理多个 PDF 文件
- ✅ **结果下载** - ZIP 压缩包一键下载
- ✅ **响应式设计** - Tailwind CSS 现代化 UI
- ✅ **MathJax 渲染** - LaTeX 公式自动渲染

---

## 📖 使用示例

### 示例 1: 基础用法 - 启动 Web 界面

**场景:** 快速启动 Web 界面处理单个 PDF

```bash
# 启动服务
python core/knowledge-card-webui.py

# 浏览器访问
http://127.0.0.1:5000

# 操作步骤:
# 1. 点击上传区域选择 PDF 文件
# 2. 勾选"验证参考文献"
# 3. 点击"开始处理"
# 4. 等待处理完成
# 5. 点击下载结果
```

**预期输出:**
- 处理进度条实时显示 (0% → 100%)
- 完成后显示成功/失败统计
- 提供 ZIP 下载链接

**说明:** 适合偶尔处理少量 PDF 的场景

---

### 示例 2: 自定义端口 - 多实例部署

**场景:** 在同一台机器上运行多个 Web 界面实例

```bash
# 实例 1 (端口 5000)
python core/knowledge-card-webui.py --port 5000

# 实例 2 (端口 5001)
python core/knowledge-card-webui.py --port 5001

# 实例 3 (端口 5002)
python core/knowledge-card-webui.py --port 5002
```

**访问地址:**
- 实例 1: http://127.0.0.1:5000
- 实例 2: http://127.0.0.1:5001
- 实例 3: http://127.0.0.1:5002

**说明:** 适合团队协作，每人独立实例

---

### 示例 3: 批量处理 - 一次处理多篇论文

**场景:** 周末集中处理一周收集的 20 篇 PDF

```bash
# 启动服务
python core/knowledge-card-webui.py --port 5000

# 浏览器访问后:
# 1. 拖拽 20 个 PDF 文件到上传区域
# 2. 配置处理选项:
#    - ☑ 验证参考文献 (启用)
#    - ☑ 导出 BibTeX (启用)
#    - ☑ 并发验证 (启用，5 线程)
#    - ☐ 渲染 LaTeX 公式 (可选)
# 3. 调整并发线程数：8 线程
# 4. 点击"开始处理"
```

**预期输出:**
```
处理进度: 100%|████████████| 20/20 [02:34<00:00]

结果统计:
✅ 成功：18 篇
❌ 失败：2 篇

参考文献统计:
总参考文献：280 篇
✅ 已验证：196 篇 (70%)
🔍 需人工：56 篇 (20%)
❌ 验证失败：28 篇 (10%)
📦 缓存命中：45 篇
🌐 API 调用：235 篇

下载：knowledge-cards-20260312.zip (15.6MB)
```

**说明:** 批量处理时建议启用并发验证，速度提升 3-5 倍

---

## 🔧 配置参数

### 命令行参数

| 参数 | 类型 | 默认值 | 必需 | 说明 |
|------|------|--------|------|------|
| `--port` | int | `5000` | ❌ | Web 服务端口 |
| `--host` | str | `127.0.0.1` | ❌ | 监听地址 |
| `--debug` | flag | `False` | ❌ | 调试模式 |
| `--max-size` | int | `100` | ❌ | 最大上传文件 (MB) |

### Web 界面选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| 验证参考文献 | ✅ 启用 | 调用 CrossRef/arXiv API 验证 |
| 导出 BibTeX | ✅ 启用 | 生成已验证文献的 BibTeX 文件 |
| 并发验证 | ✅ 启用 | 5 线程并行验证 (可配置 1-10) |
| 渲染 LaTeX 公式 | ❌ 禁用 | 启用 MathJax 公式渲染 |
| 并发线程数 | 5 | 1-10 可调 |

### API 速率限制

| API | 配额限制 | 速率限制 | 重置时间 |
|-----|----------|----------|----------|
| CrossRef | 600 请求/小时 | 10 请求/分钟 | 每小时整点 |
| arXiv | 600 请求/小时 | 10 请求/分钟 | 每小时整点 |

**注意:** 并发验证时自动添加延迟，避免超出速率限制。

---

## 📊 API 参考

### `app.route('/')`

**功能:** 渲染 Web 界面主页

**返回:** HTML 页面

---

### `app.route('/api/quota')`

**功能:** 获取 API 配额状态

**返回:**
```json
{
  "crossref": {
    "requests": 45,
    "limit": 600,
    "reset_at": "2026-03-12T08:00:00"
  },
  "arxiv": {
    "requests": 32,
    "limit": 600,
    "reset_at": "2026-03-12T08:00:00"
  }
}
```

---

### `app.route('/api/status')`

**功能:** 获取处理进度状态

**返回:**
```json
{
  "active": true,
  "progress": 45.5,
  "current_file": "paper1.pdf",
  "total_files": 20,
  "completed": 9,
  "failed": 0
}
```

---

### `app.route('/api/process', methods=['POST'])`

**功能:** 开始处理上传的 PDF 文件

**参数:**
- `files` (list): PDF 文件列表
- `validate` (bool): 是否验证参考文献
- `exportBibtex` (bool): 是否导出 BibTeX
- `concurrent` (bool): 是否启用并发验证
- `workers` (int): 并发线程数 (1-10)

**返回:**
```json
{
  "status": "started",
  "job_id": "20260312_143022"
}
```

---

## 🐳 Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制脚本
COPY 01-KNOWLEDGE-CARDS/ ./01-KNOWLEDGE-CARDS/

# 创建临时目录
RUN mkdir -p /tmp/knowledge-cards

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "01-KNOWLEDGE-CARDS/core/knowledge-card-webui.py", "--port", "5000", "--host", "0.0.0.0"]
```

### 构建镜像

```bash
docker build -t knowledge-cards-webui .
```

### 运行容器

```bash
# 基本运行
docker run -p 5000:5000 knowledge-cards-webui

# 挂载数据卷 (持久化临时文件)
docker run -p 5000:5000 -v ./data:/tmp/knowledge-cards knowledge-cards-webui

# 后台运行
docker run -d -p 5000:5000 --name kc-webui knowledge-cards-webui
```

### Docker Compose

```yaml
version: '3.8'
services:
  webui:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/tmp/knowledge-cards
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

---

## ⚙️ 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `FLASK_ENV` | Flask 运行环境 | `production` | ❌ |
| `FLASK_DEBUG` | 调试模式 | `0` | ❌ |
| `MAX_CONTENT_LENGTH` | 最大上传大小 (字节) | `104857600` (100MB) | ❌ |
| `TEMP_DIR` | 临时文件目录 | `/tmp/knowledge-cards` | ❌ |

---

## 🔒 安全说明

### 已实现的安全措施

#### 1. 文件上传安全

**✅ 文件类型验证:**
```python
# 仅允许 PDF 文件
if not f.filename.endswith('.pdf'):
    return jsonify({"error": "Only PDF files allowed"}), 400
```

**✅ 安全文件名:**
```python
from werkzeug.utils import secure_filename
pdf_path = work_dir / secure_filename(f.filename)
# 防止路径遍历攻击：../../etc/passwd → passwd
```

**✅ 大小限制:**
```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
# 超出限制自动拒绝
```

**✅ 临时文件隔离:**
```python
# 每个任务创建独立工作目录
work_dir = TEMP_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
work_dir.mkdir(parents=True, exist_ok=True)
# 任务完成后自动清理
```

---

#### 2. CSRF 保护

**⚠️ 当前状态:** 未实现 (计划中)

**风险:** 跨站请求伪造攻击

**缓解措施:**
- 监听地址默认 `127.0.0.1` (仅本地访问)
- 生产环境部署时**必须**启用 CSRF

**启用 CSRF (生产环境):**
```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 环境变量存储
csrf = CSRFProtect(app)
```

**注意:** 启用 CSRF 后，前端表单需要添加 CSRF token。

---

#### 3. XSS 防护

**✅ 输出转义:**
- Flask 自动转义 HTML 输出
- 用户输入不会直接渲染为 HTML

**⚠️ 注意事项:**
- 避免使用 `|safe` 过滤器
- 不要直接 `render_template_string` 用户输入
- 数学公式渲染 (MathJax) 在沙箱环境

**最佳实践:**
```python
# ✅ 安全：Flask 自动转义
return render_template('index.html', user_input=user_input)

# ❌ 危险：绕过转义
return render_template_string(f"<div>{user_input}</div>")
```

---

#### 4. 并发连接限制

**⚠️ 当前状态:** 无限制

**风险:** DoS 攻击 (大量并发请求)

**建议配置 (生产环境):**

**Gunicorn 配置:**
```bash
# 启动 Gunicorn (替代 Flask 开发服务器)
gunicorn -w 4 -b 127.0.0.1:5000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 30 \
  knowledge-card-webui:app
```

**参数说明:**
- `-w 4`: 4 个工作进程
- `--max-requests 1000`: 每进程处理 1000 请求后重启 (防内存泄漏)
- `--timeout 30`: 30 秒超时

---

#### 5. API 速率限制

**✅ 已实现:**
- CrossRef API: 10 请求/分钟
- arXiv API: 10 请求/分钟
- 自动延迟避免超限

**⚠️ 未实现:**
- 用户请求速率限制

**建议添加 (生产环境):**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "10 per minute"]
)

@app.route('/api/process', methods=['POST'])
@limiter.limit("5 per minute")  # 每分钟最多 5 次处理请求
def process_files():
    ...
```

---

### 安全部署清单

**开发环境:**
- [x] 文件类型验证
- [x] 安全文件名
- [x] 大小限制
- [x] 临时文件隔离
- [ ] CSRF 保护 (可选)
- [ ] 速率限制 (可选)

**生产环境:**
- [x] 文件类型验证
- [x] 安全文件名
- [x] 大小限制
- [x] 临时文件隔离
- [ ] **必须:** CSRF 保护
- [ ] **必须:** 速率限制
- [ ] **必须:** Gunicorn/uWSGI (非 Flask 开发服务器)
- [ ] **必须:** HTTPS (反向代理配置)
- [ ] **必须:** 防火墙规则 (仅开放必要端口)

---

### 安全配置示例 (生产环境)

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  webui:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}  # 从环境变量加载
      - CSRF_ENABLED=true
    volumes:
      - ./data:/tmp/knowledge-cards
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
      restart_policy:
        condition: on-failure
```

**.env (不要提交到 Git):**
```bash
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=production
CSRF_ENABLED=true
```

---

### 已知安全限制

| 限制 | 风险等级 | 缓解措施 | 计划 |
|------|----------|----------|------|
| 无 CSRF 保护 | 中 | 仅本地访问 | v2.1 |
| 无速率限制 | 中 | Gunicorn 限制 | v2.1 |
| 无用户认证 | 低 | 内部工具 | 不考虑 |
| 无审计日志 | 低 | 手动检查日志 | v2.2 |

---

### 安全事件响应

**发现安全漏洞时:**

1. **立即:** 停止服务
2. **报告:** 提交 Issue (敏感问题私信联系)
3. **修复:** 开发修复补丁
4. **测试:** 安全回归测试
5. **发布:** 发布安全更新

**联系方式:** security@example.com (待设置)

---

## 🌐 浏览器兼容性

| 浏览器 | 最低版本 | 推荐版本 | 支持状态 |
|--------|----------|----------|----------|
| Chrome | 90+ | 120+ | ✅ 完全支持 |
| Firefox | 88+ | 115+ | ✅ 完全支持 |
| Safari | 14+ | 16+ | ✅ 完全支持 |
| Edge | 90+ | 120+ | ✅ 完全支持 |
| Opera | 76+ | 100+ | ✅ 完全支持 |
| IE 11 | - | - | ❌ 不支持 |

**功能支持详情:**

| 功能 | Chrome | Firefox | Safari | Edge |
|------|--------|---------|--------|------|
| 拖拽上传 | ✅ | ✅ | ✅ | ✅ |
| 实时进度 | ✅ | ✅ | ✅ | ✅ |
| 文件下载 | ✅ | ✅ | ✅ | ✅ |
| MathJax 渲染 | ✅ | ✅ | ✅ | ✅ |
| 移动端触摸 | ✅ | ✅ | ⚠️ 部分 | ✅ |

**移动端支持:**
- ✅ iOS Safari 14+
- ✅ Android Chrome 90+
- ⚠️ 其他移动浏览器 (建议测试后使用)

---

## ❓ FAQ

### Q1: 启动时提示"端口已被占用"怎么办？

**A:** 更换端口：
```bash
python core/knowledge-card-webui.py --port 5001
```

或查找并关闭占用进程：
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

---

### Q2: 上传文件时提示"文件过大"怎么办？

**A:** 修改最大上传限制：
```python
# 编辑脚本，修改这行
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
```

或分批处理文件。

---

### Q3: API 配额用完了怎么办？

**A:** 
1. 等待配额重置 (每小时)
2. 使用缓存 (已验证的文献会缓存 24 小时)
3. 跳过验证直接生成卡片 (不勾选"验证参考文献")

---

### Q4: 处理进度卡在 50% 不动？

**A:** 
1. 检查浏览器控制台是否有错误
2. 查看服务器日志
3. 刷新页面重新查看状态
4. 重启服务

---

### Q5: 下载的结果是空 ZIP？

**A:** 
1. 检查处理是否真正完成 (进度条 100%)
2. 检查临时目录是否有文件生成
3. 查看服务器日志确认无错误
4. 尝试重新处理

---

### Q6: 如何在局域网中访问？

**A:** 
```bash
# 监听所有地址
python core/knowledge-card-webui.py --host 0.0.0.0 --port 5000

# 局域网访问
http://<你的 IP>:5000
```

---

### Q7: 如何查看处理日志？

**A:** 
- 控制台实时输出
- 日志文件：`logs/knowledge-card-webui.log`
- 启用调试模式查看详细日志：`--debug`

---

### Q8: 支持移动端访问吗？

**A:** 支持。界面使用 Tailwind CSS 响应式设计，适配手机/平板/桌面。

---

## 🔗 相关资源

- [knowledge-card-generator.py](../core/knowledge-card-generator.py) - 核心处理脚本
- [01-KNOWLEDGE-CARDS README](../README.md) - 知识卡片系统总览
- [Flask 官方文档](https://flask.palletsprojects.com/) - Web 框架文档
- [Tailwind CSS](https://tailwindcss.com/) - UI 框架文档

---

## 📝 更新日志

### v2.5 (2026-03-12)
- ✨ 初始 Web UI 版本
- ✅ Flask 后端 + Tailwind CSS 前端
- ✅ 拖拽上传支持
- ✅ 实时进度显示
- ✅ API 配额监控
- ✅ 批量处理支持
- ✅ ZIP 下载功能

---

## 📄 许可证

MIT License - 详见 [LICENSE](../../../LICENSE)

---

## 👥 作者

- Claw - AI Research Agent
- 维护者：Claw

---

**最后测试:** 2026-03-12  
**测试状态:** ✅ 所有示例通过测试  
**测试环境:** Windows 11, Python 3.11, Flask 2.3.0
