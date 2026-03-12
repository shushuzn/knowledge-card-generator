#!/usr/bin/env python3
# knowledge-card-generator.py - 学术论文知识卡片生成器 v2.0
# 用法：py knowledge-card-generator.py <pdf_file> [--output <output_dir>] [--batch <folder>] [--validate]

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse
import fitz  # PyMuPDF
import json
import re
import time
import urllib.request
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class ReferenceValidator:
    """参考文献验证器 v2.2 - 支持并发验证、缓存管理、日志"""
    
    def __init__(self, cache_file: Optional[str] = None, max_cache_size: int = 1000, max_workers: int = 5):
        self.crossref_base = "https://api.crossref.org/works/"
        self.arxiv_base = "http://export.arxiv.org/api/query?id_list="
        self.rate_limit_delay = 6.0  # CrossRef: 10 请求/分钟
        self.max_retries = 3
        self.cache_file = Path(cache_file) if cache_file else None
        self.max_cache_size = max_cache_size
        self.max_workers = max_workers
        self.cache = self._load_cache()
        self.log_file = Path("knowledge-card-validator.log")
        self._lock = threading.Lock()
        
        # 启动时清理缓存
        self._cleanup_cache()
        
    def _load_cache(self) -> Dict:
        """加载缓存"""
        if self.cache_file and self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding='utf-8'))
            except:
                pass
        return {}
    
    def _save_cache(self):
        """保存缓存"""
        if self.cache_file:
            try:
                self.cache_file.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False), encoding='utf-8')
            except:
                pass
    
    def _cleanup_cache(self):
        """清理缓存 (LRU 淘汰，保留最近的 max_cache_size 条)"""
        if not self.cache:
            return
        
        # 按缓存时间排序
        sorted_items = sorted(
            self.cache.items(),
            key=lambda x: x[1].get("cached_at", "2000-01-01"),
            reverse=True
        )
        
        # 保留最近的 max_cache_size 条
        if len(sorted_items) > self.max_cache_size:
            removed_count = len(sorted_items) - self.max_cache_size
            self.cache = dict(sorted_items[:self.max_cache_size])
            self._save_cache()
            self._log(f"缓存清理：删除 {removed_count} 条旧记录，保留 {self.max_cache_size} 条", "INFO")
        
        # 清理过期缓存 (>24 小时)
        now = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if datetime.fromisoformat(value.get("cached_at", "2000-01-01")) < now - timedelta(hours=24)
        ]
        
        if expired_keys:
            for key in expired_keys:
                del self.cache[key]
            self._save_cache()
            self._log(f"缓存清理：删除 {len(expired_keys)} 条过期记录", "INFO")
    
    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.log_file, "a", encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass
    
    def _validate_doi_with_retry(self, doi: str) -> Dict:
        """DOI 验证 (带重试)"""
        for attempt in range(1, self.max_retries + 1):
            try:
                url = f"{self.crossref_base}{doi}"
                req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeCardGenerator/2.1"})
                
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                if data["status"] == "ok":
                    message = data["message"]
                    result = {
                        "valid": True,
                        "title": message.get("title", [""])[0],
                        "author": self._format_authors(message.get("author", [])),
                        "journal": message.get("container-title", [""])[0],
                        "year": str(message.get("created", {}).get("date-parts", [[None]])[0][0] or ""),
                        "cited_by": message.get("is-referenced-by-count", 0),
                        "publisher": message.get("publisher", ""),
                        "verified_at": datetime.now().isoformat()
                    }
                    self._log(f"DOI {doi} 验证成功", "INFO")
                    return result
                    
            except Exception as e:
                self._log(f"DOI {doi} 验证失败 (尝试 {attempt}/{self.max_retries}): {e}", "WARNING")
                if attempt < self.max_retries:
                    wait_time = self.rate_limit_delay * (2 ** (attempt - 1))  # 指数退避
                    time.sleep(wait_time)
        
        self._log(f"DOI {doi} 验证失败 (已达最大重试次数)", "ERROR")
        return {"valid": False, "error": "Max retries exceeded"}
        
    def validate_doi(self, doi: str) -> Dict:
        """通过 CrossRef 验证 DOI (带缓存)"""
        # 检查缓存
        cache_key = f"doi:{doi}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # 缓存有效期 24 小时
            if datetime.fromisoformat(cached.get("cached_at", "2000-01-01")) > datetime.now() - timedelta(hours=24):
                self._log(f"DOI {doi} 使用缓存", "INFO")
                cached["from_cache"] = True
                return cached
        
        # 验证
        result = self._validate_doi_with_retry(doi)
        
        # 缓存结果
        if result.get("valid"):
            result["cached_at"] = datetime.now().isoformat()
            result["from_cache"] = False
            self.cache[cache_key] = result
            self._save_cache()
        
        return result
    
    def validate_arxiv(self, arxiv_id: str) -> Dict:
        """通过 arXiv API 验证预印本"""
        try:
            # 清理 arXiv ID 格式
            arxiv_id = arxiv_id.replace("arXiv:", "").strip()
            url = f"{self.arxiv_base}{arxiv_id}"
            
            req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeCardGenerator/2.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml = response.read().decode('utf-8')
            
            # 简单 XML 解析
            title_match = re.search(r'<title>(.*?)</title>', xml, re.DOTALL)
            author_match = re.findall(r'<name><surname>(.*?)</surname>.*?<given>(.*?)</given>', xml, re.DOTALL)
            published_match = re.search(r'<published>(.*?)</published>', xml)
            
            if title_match:
                authors = [f"{given.strip()} {surname.strip()}" for surname, given in author_match]
                return {
                    "valid": True,
                    "title": title_match.group(1).strip(),
                    "author": ", ".join(authors[:3]),  # 限制前 3 位
                    "journal": "arXiv preprint",
                    "year": published_match.group(1)[:4] if published_match else "",
                    "cited_by": 0,  # arXiv 不提供引用数
                    "publisher": "arXiv",
                    "verified_at": datetime.now().isoformat()
                }
        except Exception as e:
            pass
        
        return {"valid": False, "error": str(e)}
    
    def _format_authors(self, authors: List) -> str:
        """格式化作者列表"""
        if not authors:
            return ""
        
        formatted = []
        for author in authors[:3]:  # 限制前 3 位
            given = author.get("given", "")
            family = author.get("family", "")
            formatted.append(f"{given} {family}".strip())
        
        return ", ".join(formatted)
    
    def validate_reference(self, ref_content: str) -> Dict:
        """智能验证参考文献（自动检测 DOI 或 arXiv ID）"""
        # 检测 DOI
        doi_match = re.search(r'10\.\d{4,}/\S+', ref_content)
        if doi_match:
            time.sleep(self.rate_limit_delay)
            return self.validate_doi(doi_match.group(0))
        
        # 检测 arXiv ID
        arxiv_match = re.search(r'arXiv[:\s]+(\d+\.\d+)', ref_content, re.IGNORECASE)
        if arxiv_match:
            time.sleep(self.rate_limit_delay)
            return self.validate_arxiv(arxiv_match.group(1))
        
        # 无 DOI/arXiv，返回待验证
        return {"valid": False, "error": "No DOI or arXiv ID found", "needs_manual_check": True}


class KnowledgeCardGenerator:
    """学术论文知识卡片生成器 v2.0"""
    
    def __init__(self):
        self.metadata = {}
        self.sections = []
        self.figures = []
        self.tables = []
        self.equations = []
        self.references = []
        self.validator = ReferenceValidator()
        
    def extract_metadata(self, doc: fitz.Document) -> Dict:
        """提取论文元数据"""
        metadata = {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "journal": "",
            "year": "",
            "doi": "",
            "arxiv_id": ""
        }
        
        # 从 PDF 元数据提取
        pdf_meta = doc.metadata
        metadata["title"] = pdf_meta.get("title", "")
        metadata["authors"] = pdf_meta.get("author", "").split("; ")
        metadata["year"] = str(pdf_meta.get("creationDate", ""))[:4]
        
        # 从第一页提取标题和摘要
        if len(doc) > 0:
            first_page = doc[0]
            text = first_page.get_text("text")
            lines = text.split("\n")
            
            # 提取标题 (通常在前 5 行，最长的一行)
            title_candidates = [l.strip() for l in lines[:5] if len(l.strip()) > 20]
            if title_candidates:
                metadata["title"] = max(title_candidates, key=len)
            
            # 提取摘要
            abstract_start = -1
            abstract_end = -1
            for i, line in enumerate(lines):
                lower = line.lower()
                if "abstract" in lower or "摘要" in lower:
                    abstract_start = i + 1
                elif abstract_start > 0 and len(line.strip()) < 10 and i > abstract_start + 3:
                    abstract_end = i
                    break
            
            if abstract_start > 0:
                if abstract_end < 0:
                    abstract_end = min(abstract_start + 10, len(lines))
                metadata["abstract"] = "\n".join(lines[abstract_start:abstract_end]).strip()
            
            # 提取 arXiv ID
            arxiv_match = re.search(r'arXiv[:\s]+(\d+\.\d+)', text, re.IGNORECASE)
            if arxiv_match:
                metadata["arxiv_id"] = arxiv_match.group(1)
        
        self.metadata = metadata
        return metadata
    
    def extract_sections(self, doc: fitz.Document) -> List[Dict]:
        """提取论文章节"""
        sections = []
        current_section = {"title": "Introduction", "content": [], "page": 1}
        
        section_patterns = [
            r'^(\d+\.)\s+(.+)$',  # 1. Introduction
            r'^(I+\.?)\s+(.+)$',  # I. Introduction
            r'^(Introduction|Methods|Results|Discussion|Conclusion|References)$',  # 无编号
        ]
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            lines = text.split("\n")
            
            for line in lines:
                line = line.strip()
                is_section = False
                
                for pattern in section_patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        # 保存当前章节
                        if current_section["content"]:
                            sections.append(current_section)
                        
                        # 开始新章节
                        groups = match.groups()
                        if len(groups) >= 2:
                            section_title = match.group(2)
                        else:
                            section_title = match.group(0)
                        current_section = {
                            "title": section_title,
                            "content": [],
                            "page": page_num + 1
                        }
                        is_section = True
                        break
                
                if not is_section and line and len(line) > 5:
                    current_section["content"].append(line)
        
        # 保存最后一个章节
        if current_section["content"]:
            sections.append(current_section)
        
        self.sections = sections
        return sections
    
    def extract_references(self, doc: fitz.Document) -> List[Dict]:
        """提取参考文献"""
        references = []
        
        # 查找参考文献章节
        for section in self.sections:
            if "reference" in section["title"].lower() or "bibliography" in section["title"].lower():
                ref_text = "\n".join(section["content"])
                
                # 匹配参考文献格式
                ref_patterns = [
                    r'\[(\d+)\]\s+(.+?)(?=\[\d+\]|$)',  # [1] Author. Title.
                    r'^(\d+)\.\s+(.+?)(?=\n\d+\.|$)',  # 1. Author. Title.
                ]
                
                for pattern in ref_patterns:
                    matches = re.findall(pattern, ref_text, re.DOTALL | re.MULTILINE)
                    for match in matches:
                        ref_id = match[0]
                        ref_content = match[1].strip()
                        
                        references.append({
                            "id": ref_id,
                            "content": ref_content,
                            "verified": False,
                            "verification_status": "pending",  # pending/verified/invalid/manual
                            "verification_details": {}
                        })
                
                break
        
        self.references = references
        return references
    
    def validate_references(self, show_progress: bool = True, use_concurrent: bool = True) -> Dict:
        """验证所有参考文献 (支持并发，返回统计报告)"""
        stats = {
            "total": len(self.references),
            "verified": 0,
            "manual": 0,
            "invalid": 0,
            "cache_hits": 0,
            "api_calls": 0
        }
        
        if use_concurrent and len(self.references) > 1:
            stats = self._validate_references_concurrent(show_progress)
        else:
            # 串行验证 (向后兼容)
            for i, ref in enumerate(self.references):
                if show_progress:
                    print(f"   验证参考文献 [{ref['id']}]: {i+1}/{len(self.references)}...")
                
                result = self.validator.validate_reference(ref["content"])
                
                # 统计缓存命中
                if result.get("from_cache"):
                    stats["cache_hits"] += 1
                else:
                    stats["api_calls"] += 1
                
                ref["verification_details"] = result
                stats["total"] += 0  # 已计数
                
                if result.get("valid"):
                    ref["verified"] = True
                    ref["verification_status"] = "verified"
                    stats["verified"] += 1
                elif result.get("needs_manual_check"):
                    ref["verification_status"] = "manual"
                    stats["manual"] += 1
                else:
                    ref["verification_status"] = "invalid"
                    stats["invalid"] += 1
        
        return stats
    
    def _validate_references_concurrent(self, show_progress: bool = True) -> Dict:
        """并发验证参考文献 (多线程，返回统计报告)"""
        from tqdm import tqdm
        
        stats = {
            "total": len(self.references),
            "verified": 0,
            "manual": 0,
            "invalid": 0,
            "cache_hits": 0,
            "api_calls": 0
        }
        
        total = len(self.references)
        
        # 创建进度条
        if show_progress:
            print(f"   并发验证中 (线程数：{self.validator.max_workers})...")
            pbar = tqdm(total=total, desc="   验证进度", unit="篇", ncols=80)
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=self.validator.max_workers) as executor:
            future_to_ref = {
                executor.submit(self.validator.validate_reference, ref["content"]): ref
                for ref in self.references
            }
            
            for future in as_completed(future_to_ref):
                ref = future_to_ref[future]
                try:
                    result = future.result()
                    ref["verification_details"] = result
                    
                    # 统计缓存命中
                    if result.get("from_cache"):
                        stats["cache_hits"] += 1
                    else:
                        stats["api_calls"] += 1
                    
                    if result.get("valid"):
                        ref["verified"] = True
                        ref["verification_status"] = "verified"
                        stats["verified"] += 1
                    elif result.get("needs_manual_check"):
                        ref["verification_status"] = "manual"
                        stats["manual"] += 1
                    else:
                        ref["verification_status"] = "invalid"
                        stats["invalid"] += 1
                    
                except Exception as e:
                    self.validator._log(f"参考文献 [{ref['id']}] 验证异常：{e}", "ERROR")
                    ref["verification_status"] = "invalid"
                    ref["verification_details"] = {"valid": False, "error": str(e)}
                    stats["invalid"] += 1
                
                if show_progress:
                    pbar.update(1)
        
        if show_progress:
            pbar.close()
        
        return stats
    
    def detect_figures_tables(self, doc: fitz.Document) -> tuple:
        """检测图表"""
        figures = []
        tables = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            
            for img_index, img in enumerate(images):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    figures.append({
                        "page": page_num + 1,
                        "index": len(figures) + 1,
                        "caption": f"Figure {len(figures) + 1}",
                        "image_data": image_bytes,
                        "width": base_image["width"],
                        "height": base_image["height"]
                    })
                except:
                    pass
        
        self.figures = figures
        return figures, tables
    
    def export_bibtex(self) -> str:
        """导出参考文献为 BibTeX 格式"""
        bibtex_entries = []
        
        for ref in self.references:
            details = ref.get("verification_details", {})
            
            if not details.get("valid"):
                continue
            
            # 生成 BibTeX key
            year = details.get("year", "noyear")
            first_author = details.get("author", "unknown").split(",")[0].replace(" ", "").lower()[:8]
            bibtex_key = f"{year}{first_author}"
            
            # 确定条目类型
            entry_type = "article"
            if "book" in details.get("publisher", "").lower() or "[M]" in ref["content"]:
                entry_type = "book"
            elif "arXiv" in details.get("journal", ""):
                entry_type = "misc"
            
            # 生成 BibTeX
            entry = f"@{entry_type}{{{bibtex_key},\n"
            entry += f"  title={{{details.get('title', '')}}},\n"
            entry += f"  author={{{details.get('author', '')}}},\n"
            
            if entry_type == "article":
                entry += f"  journal={{{details.get('journal', '')}}},\n"
                entry += f"  year={{{year}}},\n"
                if details.get("cited_by", 0) > 0:
                    entry += f"  cited_by={{{details.get('cited_by')}}},\n"
            elif entry_type == "book":
                entry += f"  publisher={{{details.get('publisher', '')}}},\n"
                entry += f"  year={{{year}}},\n"
            else:  # misc
                entry += f"  howpublished={{arXiv preprint}},\n"
                entry += f"  year={{{year}}},\n"
            
            entry += f"  verified={{{ref.get('verified', False)}}},\n"
            entry += "}"
            
            bibtex_entries.append(entry)
        
        return "\n\n".join(bibtex_entries)
    
    def generate_html_card(self) -> str:
        """生成 HTML 知识卡片"""
        title = self.metadata.get("title", "Untitled")
        authors = ", ".join(self.metadata.get("authors", []))
        abstract = self.metadata.get("abstract", "")
        arxiv_id = self.metadata.get("arxiv_id", "")
        year = self.metadata.get("year", "")
        
        # 生成章节 HTML
        sections_html = ""
        for section in self.sections[:5]:  # 限制前 5 个章节
            content = "\n".join(section["content"][:500])  # 限制内容长度
            sections_html += f"""
            <div class="section">
                <h3>{section['title']}</h3>
                <p class="content">{content[:500]}...</p>
            </div>
            """
        
        # 生成参考文献 HTML
        refs_html = ""
        for ref in self.references[:10]:  # 限制前 10 篇
            status = ref.get("verification_status", "pending")
            details = ref.get("verification_details", {})
            
            # 状态图标和样式
            if status == "verified":
                icon = "✅"
                status_class = "verified"
                status_text = "已验证"
            elif status == "manual":
                icon = "🔍"
                status_class = "manual"
                status_text = "需人工核实"
            else:
                icon = "⚠️"
                status_class = "unverified"
                status_text = "待验证"
            
            # 验证详情
            details_html = ""
            if details.get("valid"):
                details_html = f"""
                <div class="ref-details">
                    <div><strong>标题:</strong> {details.get('title', 'N/A')}</div>
                    <div><strong>作者:</strong> {details.get('author', 'N/A')}</div>
                    <div><strong>期刊:</strong> {details.get('journal', 'N/A')}</div>
                    <div><strong>年份:</strong> {details.get('year', 'N/A')}</div>
                    {f"<div><strong>引用数:</strong> {details.get('cited_by', 0)}</div>" if details.get('cited_by', 0) > 0 else ''}
                </div>
                """
            
            refs_html += f"""
            <div class="reference {status_class}">
                <div class="ref-header">
                    <span class="ref-id">[{ref['id']}]</span>
                    <span class="ref-status">{icon} {status_text}</span>
                </div>
                <div class="ref-content">{ref['content']}</div>
                {details_html}
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .header {{
            border-bottom: 3px solid #4a9eff;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #1a1a1a;
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin: 5px 0;
        }}
        .abstract {{
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #4a9eff;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
        }}
        .section h3 {{
            color: #4a9eff;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        .section .content {{
            color: #333;
            font-size: 14px;
            white-space: pre-wrap;
        }}
        .references {{
            margin-top: 30px;
        }}
        .reference {{
            padding: 12px;
            margin: 10px 0;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            font-size: 13px;
        }}
        .reference.unverified {{
            border-left: 3px solid #ff9800;
            background: #fff8e1;
        }}
        .reference.verified {{
            border-left: 3px solid #4caf50;
            background: #e8f5e9;
        }}
        .reference.manual {{
            border-left: 3px solid #2196f3;
            background: #e3f2fd;
        }}
        .ref-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .ref-id {{
            font-weight: bold;
            color: #4a9eff;
            margin-right: 8px;
        }}
        .ref-status {{
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 12px;
            background: #f0f0f0;
        }}
        .ref-content {{
            color: #333;
            line-height: 1.5;
            margin-bottom: 8px;
        }}
        .ref-details {{
            margin-top: 10px;
            padding: 8px;
            background: #f5f5f5;
            border-radius: 4px;
            font-size: 12px;
        }}
        .ref-details div {{
            margin: 4px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            background: #4a9eff;
            color: white;
            border-radius: 12px;
            font-size: 12px;
            margin: 5px 5px 5px 0;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .integrity-notice {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>{title}</h1>
            <div class="meta">作者：{authors if authors else '未知'}</div>
            <div class="meta">年份：{year if year else '未知'}</div>
            {f'<div class="meta">arXiv: <span class="badge">{arxiv_id}</span></div>' if arxiv_id else ''}
        </div>
        
        <div class="abstract">
            <strong>📖 摘要</strong>
            <p style="margin-top: 10px;">{abstract if abstract else '无摘要'}</p>
        </div>
        
        <div class="integrity-notice">
            <strong>🔒 学术诚信声明：</strong>
            本卡片内容由 AI 辅助生成，所有参考文献需人工核实真实性。
            请勿直接引用未验证的文献信息。
        </div>
        
        <h2 style="margin: 30px 0 20px; color: #1a1a1a;">📑 核心章节</h2>
        {sections_html}
        
        <div class="references">
            <h2 style="margin: 30px 0 20px; color: #1a1a1a;">📚 参考文献</h2>
            {refs_html if refs_html else '<p style="color: #999;">未检测到参考文献</p>'}
        </div>
        
        <div class="footer">
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>知识卡片生成器 v1.0 | AI Research OS</p>
            <p style="margin-top: 10px; color: #ff9800;">
                ⚠️ 所有参考文献必须人工核实真实性 - 严禁虚构文献信息
            </p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def process_pdf(self, pdf_path: Path) -> str:
        """处理单个 PDF"""
        print(f"📄 处理：{pdf_path.name}")
        
        doc = fitz.open(pdf_path)
        
        # 提取内容
        print("   提取元数据...")
        self.extract_metadata(doc)
        
        print("   提取章节...")
        self.extract_sections(doc)
        
        print("   提取参考文献...")
        self.extract_references(doc)
        
        print("   检测图表...")
        self.detect_figures_tables(doc)
        
        doc.close()
        
        # 生成 HTML
        print("   生成知识卡片...")
        html = self.generate_html_card()
        
        return html
    
    def generate_batch(self, input_folder: Path, output_folder: Path) -> Dict:
        """批量处理"""
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "cards": []
        }
        
        pdf_files = list(input_folder.glob("*.pdf"))
        results["total"] = len(pdf_files)
        
        output_folder.mkdir(parents=True, exist_ok=True)
        
        for pdf_file in pdf_files:
            try:
                html = self.process_pdf(pdf_file)
                output_file = output_folder / f"{pdf_file.stem}.html"
                output_file.write_text(html, encoding='utf-8')
                
                results["success"] += 1
                results["cards"].append({
                    "file": pdf_file.name,
                    "output": output_file.name,
                    "status": "success"
                })
                print(f"   ✅ 完成：{output_file.name}")
                
            except Exception as e:
                results["failed"] += 1
                results["cards"].append({
                    "file": pdf_file.name,
                    "error": str(e),
                    "status": "failed"
                })
                print(f"   ❌ 失败：{pdf_file.name} - {e}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="学术论文知识卡片生成器 v2.4")
    parser.add_argument("pdf_file", type=str, nargs="?", help="PDF 文件路径")
    parser.add_argument("--output", "-o", type=str, help="输出目录")
    parser.add_argument("--batch", "-b", type=str, help="批量处理文件夹")
    parser.add_argument("--preview", "-p", action="store_true", help="预览 HTML")
    parser.add_argument("--validate", "-v", action="store_true", help="验证参考文献 (CrossRef/arXiv API)")
    parser.add_argument("--no-validate", action="store_true", help="跳过参考文献验证 (默认)")
    parser.add_argument("--export-bibtex", action="store_true", help="导出 BibTeX 文件")
    parser.add_argument("--cache", type=str, help="缓存文件路径 (默认：.ref-cache.json)")
    parser.add_argument("--no-concurrent", action="store_true", help="禁用并发验证 (串行模式)")
    parser.add_argument("--workers", type=int, default=5, help="并发线程数 (默认：5)")
    parser.add_argument("--max-cache-size", type=int, default=1000, help="缓存最大条目数 (默认：1000)")
    parser.add_argument("--view-cache", action="store_true", help="查看缓存统计")
    parser.add_argument("--cleanup-cache", action="store_true", help="清理缓存")
    parser.add_argument("--export-cache", type=str, help="导出缓存到文件")
    parser.add_argument("--import-cache", type=str, help="从文件导入缓存")
    parser.add_argument("--batch-report", action="store_true", help="生成批量处理汇总报告 (HTML+JSON)")
    
    args = parser.parse_args()
    
    # 缓存管理命令
    if args.view_cache or args.cleanup_cache or args.export_cache or args.import_cache:
        cache_file = Path(args.cache) if args.cache else Path(".ref-cache.json")
        
        if args.import_cache:
            # 导入缓存
            import_file = Path(args.import_cache)
            if not import_file.exists():
                print(f"❌ 导入文件不存在：{import_file}")
                return
            
            import_data = json.loads(import_file.read_text(encoding='utf-8'))
            existing_cache = {}
            if cache_file.exists():
                existing_cache = json.loads(cache_file.read_text(encoding='utf-8'))
            
            # 合并缓存 (导入的优先)
            existing_cache.update(import_data)
            cache_file.write_text(json.dumps(existing_cache, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"✅ 导入完成：{len(import_data)} 条记录")
            print(f"   总缓存：{len(existing_cache)} 条")
            return
        
        if args.export_cache:
            # 导出缓存
            if not cache_file.exists():
                print(f"❌ 缓存文件不存在：{cache_file}")
                return
            
            export_file = Path(args.export_cache)
            cache_data = json.loads(cache_file.read_text(encoding='utf-8'))
            export_file.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"✅ 导出完成：{len(cache_data)} 条记录")
            print(f"   导出文件：{export_file}")
            return
        
        if not cache_file.exists():
            print(f"❌ 缓存文件不存在：{cache_file}")
            return
        
        cache_data = json.loads(cache_file.read_text(encoding='utf-8'))
        
        if args.cleanup_cache:
            # 清理过期缓存
            now = datetime.now()
            expired_keys = [
                key for key, value in cache_data.items()
                if datetime.fromisoformat(value.get("cached_at", "2000-01-01")) < now - timedelta(hours=24)
            ]
            for key in expired_keys:
                del cache_data[key]
            cache_file.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"✅ 清理完成：删除 {len(expired_keys)} 条过期记录")
            print(f"   剩余缓存：{len(cache_data)} 条")
            return
        
        if args.view_cache:
            print(f"\n📊 缓存统计")
            print(f"   缓存文件：{cache_file}")
            print(f"   缓存大小：{len(cache_data)} 条")
            print(f"   文件大小：{cache_file.stat().st_size / 1024:.2f} KB")
            
            # 统计验证状态
            verified = sum(1 for v in cache_data.values() if v.get("valid"))
            invalid = sum(1 for v in cache_data.values() if not v.get("valid"))
            print(f"\n   验证状态:")
            print(f"   ✅ 已验证：{verified} 条")
            print(f"   ❌ 验证失败：{invalid} 条")
            
            # 显示最近 5 条
            sorted_items = sorted(
                cache_data.items(),
                key=lambda x: x[1].get("cached_at", "2000-01-01"),
                reverse=True
            )[:5]
            print(f"\n   最近缓存 (前 5 条):")
            for key, value in sorted_items:
                status = "✅" if value.get("valid") else "❌"
                title = value.get("title", "N/A")[:50]
                cached_at = value.get("cached_at", "unknown")[:10]
                print(f"   {status} [{cached_at}] {title}...")
            return
    
    # 初始化验证器 (带缓存和并发配置)
    cache_file = args.cache if args.cache else ".ref-cache.json"
    generator = KnowledgeCardGenerator()
    generator.validator = ReferenceValidator(
        cache_file=cache_file,
        max_cache_size=args.max_cache_size,
        max_workers=args.workers
    )
    
    # 批量模式
    if args.batch:
        batch_folder = Path(args.batch)
        if not batch_folder.exists():
            print(f"❌ 文件夹不存在：{batch_folder}")
            sys.exit(1)
        
        output_folder = Path(args.output) if args.output else batch_folder / "knowledge-cards"
        output_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 批量处理：{batch_folder}")
        print(f"   输出目录：{output_folder}")
        
        # 批量处理 + 统计
        batch_results = {
            "total": 0,
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
        
        pdf_files = list(batch_folder.glob("*.pdf"))
        batch_results["total"] = len(pdf_files)
        
        from tqdm import tqdm
        
        for pdf_file in tqdm(pdf_files, desc="   处理进度", unit="篇"):
            try:
                # 处理 PDF
                html_gen = KnowledgeCardGenerator()
                html_gen.validator = generator.validator
                
                html = html_gen.process_pdf(pdf_file)
                
                # 验证参考文献
                if args.validate:
                    stats = html_gen.validate_references(show_progress=False, use_concurrent=not args.no_concurrent)
                    batch_results["stats"]["total_refs"] += stats["total"]
                    batch_results["stats"]["verified"] += stats["verified"]
                    batch_results["stats"]["manual"] += stats["manual"]
                    batch_results["stats"]["invalid"] += stats["invalid"]
                    batch_results["stats"]["cache_hits"] += stats["cache_hits"]
                    batch_results["stats"]["api_calls"] += stats["api_calls"]
                    html = html_gen.generate_html_card()
                    
                    # 导出 BibTeX
                    if args.export_bibtex:
                        bibtex = html_gen.export_bibtex()
                        bibtex_file = output_folder / f"{pdf_file.stem}.bib"
                        bibtex_file.write_text(bibtex, encoding='utf-8')
                
                # 保存 HTML
                output_file = output_folder / f"{pdf_file.stem}.html"
                output_file.write_text(html, encoding='utf-8')
                
                batch_results["success"] += 1
                batch_results["files"].append({
                    "file": pdf_file.name,
                    "output": output_file.name,
                    "status": "success",
                    "refs": len(html_gen.references)
                })
                
            except Exception as e:
                batch_results["failed"] += 1
                batch_results["files"].append({
                    "file": pdf_file.name,
                    "error": str(e),
                    "status": "failed"
                })
        
        # 保存统计
        stats_file = output_folder / "batch-stats.json"
        stats_file.write_text(json.dumps(batch_results, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # 生成汇总报告
        if args.batch_report:
            report_html = generate_batch_report(batch_results)
            report_file = output_folder / "batch-report.html"
            report_file.write_text(report_html, encoding='utf-8')
            print(f"\n📊 批量汇总报告：{report_file}")
        
        print(f"\n{'='*60}")
        print(f"处理完成：{batch_results['success']}/{batch_results['total']} 成功")
        print(f"输出目录：{output_folder}")
        
        # 打印汇总统计
        if args.validate:
            print(f"\n📊 验证汇总统计")
            total = batch_results["stats"]["total_refs"]
            if total > 0:
                print(f"   总参考文献：{total} 篇")
                print(f"   ✅ 已验证：{batch_results['stats']['verified']} 篇 ({batch_results['stats']['verified']/total*100:.1f}%)")
                print(f"   🔍 需人工：{batch_results['stats']['manual']} 篇 ({batch_results['stats']['manual']/total*100:.1f}%)")
                print(f"   ❌ 验证失败：{batch_results['stats']['invalid']} 篇 ({batch_results['stats']['invalid']/total*100:.1f}%)")
                print(f"   📦 缓存命中：{batch_results['stats']['cache_hits']} 篇")
                print(f"   🌐 API 调用：{batch_results['stats']['api_calls']} 篇")
        
        return
    
    # 单文件模式
    if not args.pdf_file:
        print("❌ 请提供 PDF 文件路径或使用 --batch 参数")
        sys.exit(1)
    
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"❌ 文件不存在：{pdf_path}")
        sys.exit(1)
    
    # 处理
    html = generator.process_pdf(pdf_path)
    
    # 验证参考文献
    if args.validate:
        print("\n🔍 验证参考文献...")
        print(f"   并发模式：{'✅ 启用' if not args.no_concurrent else '❌ 禁用'} (线程数：{args.workers})")
        print(f"   缓存限制：{args.max_cache_size} 条")
        print("   (注意：CrossRef API 限速 10 请求/分钟，已启用缓存)")
        
        # 检查 tqdm 是否安装
        use_concurrent = not args.no_concurrent and len(generator.references) > 1
        if use_concurrent:
            try:
                from tqdm import tqdm
            except ImportError:
                print("   ⚠️ tqdm 未安装，降级为串行模式 (pip install tqdm)")
                use_concurrent = False
        
        stats = generator.validate_references(show_progress=True, use_concurrent=use_concurrent)
        
        # 打印统计报告
        print(f"\n📊 验证统计报告")
        print(f"   总参考文献：{stats['total']} 篇")
        print(f"   ✅ 已验证：{stats['verified']} 篇 ({stats['verified']/stats['total']*100:.1f}%)")
        print(f"   🔍 需人工：{stats['manual']} 篇 ({stats['manual']/stats['total']*100:.1f}%)")
        print(f"   ❌ 验证失败：{stats['invalid']} 篇 ({stats['invalid']/stats['total']*100:.1f}%)")
        print(f"\n   性能统计:")
        print(f"   📦 缓存命中：{stats['cache_hits']} 篇 ({stats['cache_hits']/stats['total']*100:.1f}%)")
        print(f"   🌐 API 调用：{stats['api_calls']} 篇")
        if stats['api_calls'] > 0:
            print(f"   ⏱️  平均耗时：{stats['api_calls'] * 6.0:.1f} 秒 (理论值)")
        
        html = generator.generate_html_card()  # 重新生成带验证结果的 HTML
        
        # 导出 BibTeX
        if args.export_bibtex:
            bibtex = generator.export_bibtex()
            bibtex_file = pdf_path.parent / f"{pdf_path.stem}.bib"
            bibtex_file.write_text(bibtex, encoding='utf-8')
            print(f"\n   📚 BibTeX 已导出：{bibtex_file}")
    
    # 输出
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{pdf_path.stem}.html"
        output_file.write_text(html, encoding='utf-8')
        print(f"\n📁 已保存：{output_file}")
    elif args.preview:
        print("\n" + "="*60)
        print("📖 HTML 预览 (前 2000 字符):")
        print("="*60)
        print(html[:2000])
        print(f"\n... (共{len(html)}字符)")
    else:
        # 默认保存到同目录
        output_file = pdf_path.parent / f"{pdf_path.stem}.card.html"
        output_file.write_text(html, encoding='utf-8')
        print(f"\n📁 已保存：{output_file}")


def generate_batch_report(results: Dict) -> str:
    """生成批量处理汇总报告 (HTML)"""
    total = results["total"]
    success = results["success"]
    failed = results["failed"]
    stats = results.get("stats", {})
    
    # 计算百分比
    success_rate = success / total * 100 if total > 0 else 0
    
    # 验证统计
    total_refs = stats.get("total_refs", 0)
    verified = stats.get("verified", 0)
    manual = stats.get("manual", 0)
    invalid = stats.get("invalid", 0)
    cache_hits = stats.get("cache_hits", 0)
    api_calls = stats.get("api_calls", 0)
    
    # 生成文件列表 HTML
    files_html = ""
    for f in results["files"]:
        status_class = "success" if f["status"] == "success" else "failed"
        status_icon = "✅" if f["status"] == "success" else "❌"
        files_html += f"""
        <tr class="{status_class}">
            <td>{status_icon}</td>
            <td>{f['file']}</td>
            <td>{f.get('refs', 'N/A')}</td>
            <td>{f.get('output', f.get('error', 'N/A'))}</td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>批量处理汇总报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        h1, h2 {{
            color: #1a1a1a;
            margin-bottom: 20px;
        }}
        h1 {{
            border-bottom: 3px solid #4a9eff;
            padding-bottom: 15px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #4a9eff;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            margin: 20px 0;
            height: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr.success {{
            background: #e8f5e9;
        }}
        tr.failed {{
            background: #ffebee;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 批量处理汇总报告</h1>
        <p style="color: #666;">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2 style="margin-top: 30px;">处理概览</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value">{total}</div>
                <div class="stat-label">总文件数</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #4caf50;">{success}</div>
                <div class="stat-label">成功 ({success_rate:.1f}%)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #f44336;">{failed}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{total_refs}</div>
                <div class="stat-label">参考文献总数</div>
            </div>
        </div>
        
        <h2 style="margin-top: 30px;">验证统计</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value" style="color: #4caf50;">{verified}</div>
                <div class="stat-label">✅ 已验证</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #ff9800;">{manual}</div>
                <div class="stat-label">🔍 需人工</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #f44336;">{invalid}</div>
                <div class="stat-label">❌ 验证失败</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #2196f3;">{cache_hits}</div>
                <div class="stat-label">📦 缓存命中</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="validationChart"></canvas>
        </div>
        
        <h2 style="margin-top: 30px;">处理详情</h2>
        <table>
            <thead>
                <tr>
                    <th>状态</th>
                    <th>文件名</th>
                    <th>参考文献数</th>
                    <th>输出/错误</th>
                </tr>
            </thead>
            <tbody>
                {files_html}
            </tbody>
        </table>
        
        <div class="footer">
            <p>知识卡片生成器 v2.4 | AI Research OS</p>
        </div>
    </div>
    
    <script>
        const ctx = document.getElementById('validationChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['已验证', '需人工', '验证失败'],
                datasets: [{{
                    data: [{verified}, {manual}, {invalid}],
                    backgroundColor: ['#4caf50', '#ff9800', '#f44336']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '参考文献验证分布',
                        font: {{ size: 16 }}
                    }},
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    main()
