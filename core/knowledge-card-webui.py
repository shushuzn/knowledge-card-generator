#!/usr/bin/env python3
# knowledge-card-webui.py - 知识卡片生成器 Web 界面 v2.5
# 用法：py 30-scripts/knowledge-card-webui.py [--port 5000]

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import os
import json
import threading
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# 导入知识卡片生成器
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
spec = importlib.util.spec_from_file_location("knowledge_card_generator", Path(__file__).parent / "knowledge-card-generator.py")
knowledge_card_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge_card_generator)
KnowledgeCardGenerator = knowledge_card_generator.KnowledgeCardGenerator
ReferenceValidator = knowledge_card_generator.ReferenceValidator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# 全局状态
processing_status = {
    "active": False,
    "progress": 0,
    "current_file": "",
    "total_files": 0,
    "completed": 0,
    "failed": 0,
    "result": None
}

# 临时目录
TEMP_DIR = Path(tempfile.gettempdir()) / "knowledge-cards"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# API 配额跟踪
api_quota = {
    "crossref": {
        "requests": 0,
        "limit": 600,  # 10 请求/分钟 × 60 分钟
        "reset_at": datetime.now().replace(minute=0, second=0, microsecond=0)
    },
    "arxiv": {
        "requests": 0,
        "limit": 600,
        "reset_at": datetime.now().replace(minute=0, second=0, microsecond=0)
    }
}


def track_api_call(api_name: str):
    """跟踪 API 调用"""
    if api_name in api_quota:
        api_quota[api_name]["requests"] += 1


def check_quota(api_name: str) -> bool:
    """检查 API 配额"""
    if api_name not in api_quota:
        return True
    
    quota = api_quota[api_name]
    now = datetime.now()
    
    # 重置配额 (每小时)
    if now >= quota["reset_at"]:
        quota["requests"] = 0
        quota["reset_at"] = now.replace(minute=0, second=0, microsecond=0)
        quota["reset_at"] = quota["reset_at"].replace(hour=now.hour + 1)
    
    return quota["requests"] < quota["limit"]


HTML_INDEX = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#667eea">
    <meta name="description" content="从 PDF 到知识卡片，一键生成">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <title>知识卡片生成器</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        .nav-link { color: #667eea; text-decoration: none; font-weight: bold; }
        .nav-link:hover { text-decoration: underline; }
    </style>
    <style>
        .dropzone {
            border: 2px dashed #4a9eff;
            transition: all 0.3s;
        }
        .dropzone:hover, .dropzone.dragover {
            background: #e3f2fd;
            border-color: #2196f3;
        }
        .progress-bar {
            transition: width 0.3s;
        }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- 导航栏 -->
        <nav class="mb-6 flex gap-4">
            <a href="/" class="nav-link">📚 知识卡片</a>
            <a href="/graph" class="nav-link">🗺️ 知识图谱</a>
        </nav>
        
        <header class="mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">📚 知识卡片生成器</h1>
            <p class="text-gray-600">从学术论文 PDF 自动生成结构化 HTML 知识卡片 v2.5</p>
        </header>

        <!-- API 配额状态 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4">🔌 API 配额状态</h2>
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-600">CrossRef API</div>
                    <div class="text-2xl font-bold text-blue-600">
                        <span id="crossref-usage">0</span> / 600
                    </div>
                    <div class="text-xs text-gray-500">每小时重置</div>
                </div>
                <div class="bg-green-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-600">arXiv API</div>
                    <div class="text-2xl font-bold text-green-600">
                        <span id="arxiv-usage">0</span> / 600
                    </div>
                    <div class="text-xs text-gray-500">每小时重置</div>
                </div>
            </div>
        </div>

        <!-- 上传区域 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4">📤 上传 PDF</h2>
            <div id="dropzone" class="dropzone rounded-lg p-12 text-center cursor-pointer">
                <input type="file" id="fileInput" accept=".pdf" multiple class="hidden">
                <div class="text-6xl mb-4">📄</div>
                <p class="text-lg text-gray-600 mb-2">拖拽 PDF 文件到此处，或点击选择文件</p>
                <p class="text-sm text-gray-500">支持批量上传 (最大 100MB)</p>
            </div>
            <div id="fileList" class="mt-4"></div>
        </div>

        <!-- 处理选项 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-semibold mb-4">⚙️ 处理选项</h2>
            <div class="grid grid-cols-2 gap-4">
                <label class="flex items-center">
                    <input type="checkbox" id="validateRefs" checked class="mr-2">
                    <span>验证参考文献 (CrossRef/arXiv)</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" id="exportBibtex" checked class="mr-2">
                    <span>导出 BibTeX</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" id="enableConcurrent" checked class="mr-2">
                    <span>并发验证 (5 线程)</span>
                </label>
                <label class="flex items-center">
                    <input type="checkbox" id="renderMath" class="mr-2">
                    <span>渲染 LaTeX 公式 (MathJax)</span>
                </label>
            </div>
            <div class="mt-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">并发线程数</label>
                <input type="range" id="workers" min="1" max="10" value="5" class="w-full">
                <div class="text-sm text-gray-500">当前：<span id="workersValue">5</span> 线程</div>
            </div>
        </div>

        <!-- 处理进度 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-6" id="progressSection" style="display:none;">
            <h2 class="text-xl font-semibold mb-4">⏳ 处理进度</h2>
            <div class="w-full bg-gray-200 rounded-full h-4 mb-4">
                <div id="progressBar" class="progress-bar bg-blue-600 h-4 rounded-full" style="width: 0%"></div>
            </div>
            <div class="grid grid-cols-3 gap-4 text-center">
                <div>
                    <div class="text-2xl font-bold text-blue-600" id="progressPercent">0%</div>
                    <div class="text-sm text-gray-500">进度</div>
                </div>
                <div>
                    <div class="text-2xl font-bold text-green-600" id="completedCount">0</div>
                    <div class="text-sm text-gray-500">已完成</div>
                </div>
                <div>
                    <div class="text-2xl font-bold text-red-600" id="failedCount">0</div>
                    <div class="text-sm text-gray-500">失败</div>
                </div>
            </div>
            <div class="mt-4 text-sm text-gray-600">
                当前文件：<span id="currentFile">-</span>
            </div>
        </div>

        <!-- 处理按钮 -->
        <div class="text-center mb-6">
            <button id="processBtn" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg text-lg" disabled>
                🚀 开始处理
            </button>
        </div>

        <!-- 结果下载 -->
        <div id="resultSection" class="bg-white rounded-lg shadow-md p-6" style="display:none;">
            <h2 class="text-xl font-semibold mb-4">✅ 处理完成</h2>
            <div id="resultStats" class="mb-4"></div>
            <a id="downloadLink" class="inline-block bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded-lg">
                📥 下载结果 (ZIP)
            </a>
        </div>
    </div>

    <script>
        // 拖拽上传
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const processBtn = document.getElementById('processBtn');
        
        let selectedFiles = [];

        dropzone.addEventListener('click', () => fileInput.click());
        
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        function handleFiles(files) {
            selectedFiles = Array.from(files).filter(f => f.name.endsWith('.pdf'));
            updateFileList();
            processBtn.disabled = selectedFiles.length === 0;
        }
        
        function updateFileList() {
            if (selectedFiles.length === 0) {
                fileList.innerHTML = '';
                return;
            }
            fileList.innerHTML = '<div class="text-sm text-gray-600">已选择文件:</div>' +
                selectedFiles.map(f => 
                    `<div class="flex items-center justify-between bg-gray-50 p-2 mt-1 rounded">
                        <span>📄 ${f.name}</span>
                        <span class="text-xs text-gray-500">${(f.size/1024/1024).toFixed(2)} MB</span>
                    </div>`
                ).join('');
        }
        
        // 线程数滑块
        document.getElementById('workers').addEventListener('input', (e) => {
            document.getElementById('workersValue').textContent = e.target.value;
        });
        
        // 处理按钮
        processBtn.addEventListener('click', async () => {
            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('files', f));
            formData.append('validate', document.getElementById('validateRefs').checked);
            formData.append('exportBibtex', document.getElementById('exportBibtex').checked);
            formData.append('concurrent', document.getElementById('enableConcurrent').checked);
            formData.append('renderMath', document.getElementById('renderMath').checked);
            formData.append('workers', document.getElementById('workers').value);
            
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultSection').style.display = 'none';
            processBtn.disabled = true;
            
            // 轮询进度
            const pollInterval = setInterval(async () => {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                document.getElementById('progressBar').style.width = status.progress + '%';
                document.getElementById('progressPercent').textContent = status.progress.toFixed(1) + '%';
                document.getElementById('completedCount').textContent = status.completed;
                document.getElementById('failedCount').textContent = status.failed;
                document.getElementById('currentFile').textContent = status.current_file || '-';
                
                if (!status.active && status.result) {
                    clearInterval(pollInterval);
                    showResult(status.result);
                }
            }, 1000);
            
            // 开始处理
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                clearInterval(pollInterval);
                alert('处理失败：' + await response.text());
                processBtn.disabled = false;
            }
        });
        
        function showResult(result) {
            document.getElementById('resultSection').style.display = 'block';
            document.getElementById('resultStats').innerHTML = `
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="bg-green-50 p-4 rounded">
                        <div class="text-sm text-gray-600">成功</div>
                        <div class="text-2xl font-bold text-green-600">${result.success}</div>
                    </div>
                    <div class="bg-red-50 p-4 rounded">
                        <div class="text-sm text-gray-600">失败</div>
                        <div class="text-2xl font-bold text-red-600">${result.failed}</div>
                    </div>
                </div>
                ${result.total_refs ? `
                <div class="bg-blue-50 p-4 rounded mb-4">
                    <div class="text-sm text-gray-600">参考文献统计</div>
                    <div class="grid grid-cols-3 gap-2 mt-2">
                        <div class="text-center">
                            <div class="text-lg font-bold text-green-600">${result.verified}</div>
                            <div class="text-xs text-gray-500">已验证</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-bold text-orange-600">${result.manual}</div>
                            <div class="text-xs text-gray-500">需人工</div>
                        </div>
                        <div class="text-center">
                            <div class="text-lg font-bold text-red-600">${result.invalid}</div>
                            <div class="text-xs text-gray-500">验证失败</div>
                        </div>
                    </div>
                </div>
                ` : ''}
            `;
            document.getElementById('downloadLink').href = result.download_url;
            processBtn.disabled = false;
        }
        
        // 加载 API 配额
        async function loadQuota() {
            const response = await fetch('/api/quota');
            const quota = await response.json();
            document.getElementById('crossref-usage').textContent = quota.crossref.requests;
            document.getElementById('arxiv-usage').textContent = quota.arxiv.requests;
        }
        
        // 注册 Service Worker (PWA)
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => console.log('Service Worker registered'))
                .catch(err => console.log('Service Worker registration failed:', err));
        }
        
        loadQuota();
        setInterval(loadQuota, 60000);  // 每分钟刷新
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

@app.route('/graph')
def graph_page():
    """知识图谱可视化页面"""
    from flask import send_file
    template_path = Path(__file__).parent.parent / 'templates' / 'graph.html'
    return send_file(template_path)


@app.route('/api/quota')
def get_quota():
    return jsonify(api_quota)

@app.route('/api/load-stress-test/<int:n_papers>')
def load_stress_test(n_papers):
    """加载压力测试数据"""
    import random
    
    # 生成测试数据
    fields = {
        'NLP': ['BERT', 'transformer', 'attention', 'NLP', 'language model'],
        'CV': ['CNN', 'ResNet', 'AlexNet', 'ImageNet', 'image classification'],
        'ML': ['deep learning', 'neural network', 'optimization', 'gradient']
    }
    
    papers = []
    for i in range(n_papers):
        field = random.choice(list(fields.keys()))
        keywords = random.sample(fields[field], min(3, len(fields[field])))
        year = random.randint(2010, 2024)
        
        references = []
        if i > 0:
            n_refs = random.randint(0, min(3, i))
            for idx in random.sample(range(i), n_refs):
                references.append({"title": f"Paper {idx}", "doi": f"10.1000/test{idx}"})
        
        papers.append({
            "id": i + 1,
            "title": f"Paper {i + 1}: {random.choice(keywords)} Study",
            "doi": f"10.1000/test{i}",
            "year": year,
            "keywords": keywords,
            "references": references
        })
    
    # 生成图谱
    from graph_generator import GraphGenerator
    graph_gen = GraphGenerator()
    
    start_time = __import__('time').time()
    citation_graph = graph_gen.generate_citation_graph(papers)
    gen_time = __import__('time').time() - start_time
    
    return jsonify({
        "success": True,
        "data": {"citation": citation_graph},
        "stats": {"citation": citation_graph.get('stats', {})},
        "performance": {
            "papers": n_papers,
            "generation_time": round(gen_time, 3),
            "nodes": citation_graph['stats']['nodes'],
            "links": citation_graph['stats']['links']
        }
    })

@app.route('/api/arxiv/search')
def arxiv_search():
    """arXiv 搜索 API"""
    from arxiv_api import ArXivClient
    
    query = request.args.get('q', '')
    max_results = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({"error": "请输入搜索关键词"}), 400
    
    try:
        client = ArXivClient(max_results=max_results)
        papers = client.search(query, max_results)
        
        return jsonify({
            "success": True,
            "count": len(papers),
            "papers": papers
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/arxiv/download')
def arxiv_download():
    """下载 arXiv PDF"""
    import tempfile
    from arxiv_api import ArXivClient
    
    pdf_url = request.args.get('url', '')
    arxiv_id = request.args.get('id', '')
    
    if not pdf_url:
        return jsonify({"error": "请提供 PDF URL"}), 400
    
    try:
        # 创建临时文件
        temp_dir = Path(tempfile.gettempdir()) / 'knowledge-cards' / 'arxiv'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = temp_dir / f"{arxiv_id or 'paper'}.pdf"
        
        client = ArXivClient()
        if client.download_pdf(pdf_url, str(pdf_path)):
            # 直接处理 PDF
            from graph_generator import GraphGenerator
            from knowledge_card_generator import KnowledgeCardGenerator
            
            generator = KnowledgeCardGenerator()
            result = generator.process_pdf(pdf_path)
            
            return jsonify({
                "success": True,
                "result": result,
                "pdf_path": str(pdf_path)
            })
        else:
            return jsonify({"error": "下载失败"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/load-sample/<field>')
def load_sample_field(field):
    """加载指定领域的示例数据"""
    import json
    sample_path = Path(__file__).parent.parent / 'data' / 'sample_papers_multi_field.json'
    
    try:
        with open(sample_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if field not in data['fields']:
            return jsonify({"error": f"未知领域：{field}"}), 400
        
        papers = data['fields'][field]['papers']
        
        from graph_generator import GraphGenerator
        graph_gen = GraphGenerator()
        
        keyword_graph = graph_gen.generate_keyword_graph(papers)
        citation_graph = graph_gen.generate_citation_graph(papers)
        
        return jsonify({
            "success": True,
            "field": field,
            "field_name": data['fields'][field]['name'],
            "data": {
                "keyword": keyword_graph,
                "citation": citation_graph
            },
            "stats": {
                "keyword": keyword_graph.get('stats', {}),
                "citation": citation_graph.get('stats', {})
            },
            "message": f"已加载 {len(papers)} 篇{data['fields'][field]['name']}论文"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/load-sample')
def load_sample():
    """加载示例数据 (默认 AI 领域)"""
    import json
    sample_path = Path(__file__).parent.parent / 'data' / 'sample_papers.json'
    
    try:
        with open(sample_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        papers = data['papers']
        
        # 生成三种图谱
        from graph_generator import GraphGenerator
        graph_gen = GraphGenerator()
        
        keyword_graph = graph_gen.generate_keyword_graph(papers)
        citation_graph = graph_gen.generate_citation_graph(papers)
        domain_graph = graph_gen.generate_domain_graph(papers)
        
        # 返回所有图谱类型
        return jsonify({
            "success": True,
            "data": {
                "keyword": keyword_graph,
                "citation": citation_graph,
                "domain": domain_graph
            },
            "stats": {
                "keyword": keyword_graph.get('stats', {}),
                "citation": citation_graph.get('stats', {}),
                "domain": domain_graph.get('stats', {})
            },
            "message": f"已加载 {len(papers)} 篇示例论文"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-graph', methods=['POST'])
def generate_graph():
    """生成知识图谱 API"""
    from graph_generator import GraphGenerator
    
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    files = request.files.getlist('files')
    graph_type = request.form.get('graph_type', 'keyword')
    
    # 保存上传的文件
    work_dir = TEMP_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_paths = []
    for f in files:
        if f.filename.endswith('.pdf'):
            pdf_path = work_dir / secure_filename(f.filename)
            f.save(str(pdf_path))
            pdf_paths.append(pdf_path)
    
    try:
        # 处理 PDF 提取信息
        generator = KnowledgeCardGenerator()
        papers = []
        
        for pdf_path in pdf_paths:
            result = generator.process_pdf(pdf_path)
            papers.append({
                'title': result.get('metadata', {}).get('title', ''),
                'abstract': result.get('abstract', ''),
                'keywords': result.get('keywords', []),
                'references': result.get('references', [])
            })
        
        # 生成图谱
        graph_gen = GraphGenerator()
        
        if graph_type == 'keyword':
            graph_data = graph_gen.generate_keyword_graph(papers)
        elif graph_type == 'citation':
            graph_data = graph_gen.generate_citation_graph(papers)
        elif graph_type == 'domain':
            graph_data = graph_gen.generate_domain_graph(papers)
        else:
            return jsonify({"error": "Invalid graph type"}), 400
        
        return jsonify({
            "success": True,
            "data": graph_data,
            "stats": graph_data.get('stats', {})
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PWA 静态文件路由
@app.route('/static/manifest.json')
def serve_manifest():
    return send_file(Path(__file__).parent.parent / 'static/manifest.json', mimetype='application/json')

@app.route('/static/sw.js')
def serve_sw():
    return send_file(Path(__file__).parent.parent / 'static/sw.js', mimetype='application/javascript')

@app.route('/api/status')
def get_status():
    return jsonify(processing_status)


@app.route('/api/process', methods=['POST'])
def process_files():
    global processing_status
    
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    files = request.files.getlist('files')
    validate = request.form.get('validate', 'false') == 'true'
    export_bibtex = request.form.get('exportBibtex', 'false') == 'true'
    concurrent = request.form.get('concurrent', 'false') == 'true'
    workers = int(request.form.get('workers', 5))
    
    # 创建临时工作目录
    work_dir = TEMP_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存上传的文件
    pdf_paths = []
    for f in files:
        if f.filename.endswith('.pdf'):
            pdf_path = work_dir / secure_filename(f.filename)
            f.save(str(pdf_path))
            pdf_paths.append(pdf_path)
    
    # 启动后台处理
    def process_background():
        global processing_status
        processing_status["active"] = True
        processing_status["total_files"] = len(pdf_paths)
        processing_status["completed"] = 0
        processing_status["failed"] = 0
        
        results = {
            "total": len(pdf_paths),
            "success": 0,
            "failed": 0,
            "files": [],
            "stats": {
                "total_refs": 0,
                "verified": 0,
                "manual": 0,
                "invalid": 0,
                "cache_hits": 0,
                "api_calls": 0
            }
        }
        
        generator = KnowledgeCardGenerator()
        generator.validator = ReferenceValidator(max_workers=workers)
        
        for i, pdf_path in enumerate(pdf_paths):
            processing_status["current_file"] = pdf_path.name
            processing_status["progress"] = (i / len(pdf_paths)) * 100
            
            try:
                # 处理 PDF
                html = generator.process_pdf(pdf_path)
                
                # 验证参考文献
                if validate:
                    stats = generator.validate_references(show_progress=False, use_concurrent=concurrent)
                    results["stats"]["total_refs"] += stats["total"]
                    results["stats"]["verified"] += stats["verified"]
                    results["stats"]["manual"] += stats["manual"]
                    results["stats"]["invalid"] += stats["invalid"]
                    results["stats"]["cache_hits"] += stats["cache_hits"]
                    results["stats"]["api_calls"] += stats["api_calls"]
                    html = generator.generate_html_card()
                    
                    # 跟踪 API 调用
                    track_api_call("crossref")
                    track_api_call("arxiv")
                
                # 保存 HTML
                output_file = work_dir / f"{pdf_path.stem}.html"
                output_file.write_text(html, encoding='utf-8')
                
                # 导出 BibTeX
                if export_bibtex:
                    bibtex = generator.export_bibtex()
                    bibtex_file = work_dir / f"{pdf_path.stem}.bib"
                    bibtex_file.write_text(bibtex, encoding='utf-8')
                
                results["success"] += 1
                results["files"].append({
                    "file": pdf_path.name,
                    "output": output_file.name,
                    "status": "success"
                })
                
            except Exception as e:
                results["failed"] += 1
                results["files"].append({
                    "file": pdf_path.name,
                    "error": str(e),
                    "status": "failed"
                })
            
            processing_status["completed"] = results["success"]
            processing_status["failed"] = results["failed"]
        
        # 保存统计
        stats_file = work_dir / "batch-stats.json"
        stats_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # 压缩结果
        import zipfile
        zip_path = work_dir.parent / f"{work_dir.name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in work_dir.rglob('*'):
                zipf.write(file, file.relative_to(work_dir))
        
        processing_status["active"] = False
        processing_status["progress"] = 100
        processing_status["result"] = {
            "success": results["success"],
            "failed": results["failed"],
            "total_refs": results["stats"]["total_refs"],
            "verified": results["stats"]["verified"],
            "manual": results["stats"]["manual"],
            "invalid": results["stats"]["invalid"],
            "download_url": f"/api/download/{zip_path.name}"
        }
    
    thread = threading.Thread(target=process_background)
    thread.start()
    
    return jsonify({"status": "started"})


@app.route('/api/download/<filename>')
def download(filename):
    file_path = TEMP_DIR / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(str(file_path), as_attachment=True)


if __name__ == "__main__":
    import os
    
    # 直接从环境变量读取 (Render 自动设置 PORT)
    host = "0.0.0.0"
    port = int(os.environ.get('PORT', 5000))
    
    # 禁用 Flask 启动 banner (Render Python 3.14 兼容)
    import sys
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    # 启动服务
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
