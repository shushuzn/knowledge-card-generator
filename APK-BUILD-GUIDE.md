# 知识卡片生成器 - APK 打包指南

**版本:** v1.0  
**日期:** 2026-03-12  
**目标:** 将 Web UI 封装成 Android APK

---

## 📱 方案选择

### 推荐：在线打包 (最快)

| 工具 | 网址 | 免费额度 | 说明 |
|------|------|----------|------|
| **WebIntoApp** | webintoapp.com | 免费 | 最简单 |
| **AppsGeyser** | appsgeyser.com | 免费 | 有广告 |
| **WebViewGold** | webviewgold.com | $20 | 无广告 |

---

## 🚀 方案 1: WebIntoApp (推荐)

### 步骤 1: 部署 Web UI 到云端

**平台:** Railway.app

**步骤:**
```
1. 注册 Railway: https://railway.app
2. 创建 GitHub 仓库 (知识卡片代码)
3. Railway 连接 GitHub
4. 自动部署
5. 获得域名：xxx.railway.app
```

**时间:** 30 分钟

---

### 步骤 2: WebIntoApp 打包

**网址:** https://webintoapp.com

**步骤:**
1. 打开 WebIntoApp
2. 输入 URL: `https://xxx.railway.app`
3. 设置 App 名称：知识卡片生成器
4. 设置图标：上传 logo.png
5. 点击"Build"
6. 等待编译 (5-10 分钟)
7. 下载 APK

**设置:**
- App Name: 知识卡片生成器
- Package Name: com.knowledgecard.generator
- Version: 1.0.0
- Icon: 512x512 PNG
- Orientation: 自动

**时间:** 10 分钟

---

### 步骤 3: 测试 APK

**测试:**
1. 传输 APK 到手机
2. 安装 (允许未知来源)
3. 打开 App
4. 上传测试 PDF
5. 验证功能

**时间:** 5 分钟

---

## 🛠️ 方案 2: Android Studio (本地 Flask)

### 架构

```
APK 包含:
- Python 运行时 (Chaquopy)
- Flask 后端
- WebView 前端
- PDF 处理模块
```

### 需要工具

| 工具 | 用途 | 下载 |
|------|------|------|
| Android Studio | Android 开发 | android.com/studio |
| Chaquopy | Python-Android 桥 | chaquo.com/chaquopy |
| Buildozer | Python 打包 | github.com/kivy/buildozer |

### 步骤

**1. 创建 Android 项目**
```
1. Android Studio → New Project
2. Empty Activity
3. 添加 Chaquopy 插件
4. 配置 Python 环境
```

**2. 集成 Flask**
```python
# app/src/main/python/main.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "知识卡片生成器"

if __name__ == '__main__':
    app.run()
```

**3. WebView 配置**
```java
// MainActivity.java
WebView webView = findViewById(R.id.webview);
webView.getSettings().setJavaScriptEnabled(true);
webView.loadUrl("http://localhost:5000");
```

**4. 打包 APK**
```
Build → Build Bundle(s) / APK(s) → Build APK(s)
```

**时间:** 2-3 天  
**难度:** ⭐⭐⭐⭐

---

## 📦 方案 3: Kivy + Buildozer

### 架构

```
Python 代码 (Kivy UI)
    ↓
Buildozer 打包
    ↓
APK
```

### 步骤

**1. 安装 Buildozer**
```bash
pip install buildozer
buildozer init
```

**2. 配置 buildozer.spec**
```
[app]
title = 知识卡片生成器
package.name = knowledgecard
package.domain = org.knowledgecard
source.dir = .
version = 1.0.0
requirements = python3,flask,pymupdf
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
```

**3. 打包**
```bash
buildozer -v android debug
```

**时间:** 1-2 天  
**难度:** ⭐⭐⭐

---

## 💰 成本对比

| 方案 | 时间 | 成本 | 难度 |
|------|------|------|------|
| WebIntoApp | 1-2 小时 | $0 | ⭐ |
| Android Studio | 2-3 天 | $0 | ⭐⭐⭐⭐ |
| Kivy + Buildozer | 1-2 天 | $0 | ⭐⭐⭐ |

---

## 📋 推荐方案

### 今天完成 (最快)

```
1. Railway 部署 Web UI (30 分钟)
2. WebIntoApp 打包 (10 分钟)
3. 测试 APK (5 分钟)
```

**总时间:** 1 小时  
**成本:** $0

---

## 📝 准备材料

### 需要的文件

| 文件 | 用途 | 尺寸 |
|------|------|------|
| Logo | App 图标 | 512x512 PNG |
| 名称 | App 名称 | 知识卡片生成器 |
| 描述 | App 描述 | 100 字内 |
| URL | Web UI 地址 | Railway 域名 |

### 准备清单

- [ ] Railway 账号
- [ ] GitHub 账号
- [ ] App 图标 (PNG 512x512)
- [ ] WebIntoApp 账号 (可选)

---

## ⚠️ 注意事项

### 权限
APK 需要以下权限:
- `INTERNET` - 访问网络
- `READ_EXTERNAL_STORAGE` - 读取 PDF
- `WRITE_EXTERNAL_STORAGE` - 保存结果

### 兼容性
- Android 5.0+ (API 21+)
- 需要网络连接 (云端方案)

### 发布
- 自己用：直接安装 APK
- 公开发布：需要签名
- Google Play: 需要开发者账号 ($25)

---

## 🎯 下一步

**立即可做:**
1. 准备 App 图标 (512x512 PNG)
2. 注册 Railway 账号
3. 部署 Web UI
4. WebIntoApp 打包

**我来帮你准备什么？**
- [ ] Railway 部署配置
- [ ] WebIntoApp 打包指南
- [ ] App 图标设计
- [ ] 其他

---

*指南完成。按步骤操作即可。*
