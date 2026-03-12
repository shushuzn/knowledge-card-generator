#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv API 客户端 - 搜索和下载论文
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import time


class ArXivClient:
    """arXiv API 客户端"""
    
    def __init__(self, max_results: int = 10):
        self.base_url = "http://export.arxiv.org/api/query"
        self.max_results = max_results
    
    def search(self, query: str, max_results: int = None) -> List[Dict]:
        """
        搜索 arXiv 论文
        
        Args:
            query: 搜索关键词 (标题/作者/摘要)
            max_results: 返回结果数量
            
        Returns:
            论文列表
        """
        if max_results is None:
            max_results = self.max_results
        
        # 构建搜索 URL
        search_query = urllib.parse.quote(query)
        url = f"{self.base_url}?search_query=all:{search_query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
        
        try:
            # 发送请求
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read().decode('utf-8')
            
            # 解析 XML
            return self._parse_response(xml_data)
        
        except Exception as e:
            print(f"arXiv API 错误：{e}")
            return []
    
    def _parse_response(self, xml_data: str) -> List[Dict]:
        """解析 arXiv XML 响应"""
        papers = []
        
        # 解析 XML
        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        
        for entry in root.findall('atom:entry', namespace):
            paper = {
                'title': self._get_text(entry, 'atom:title', namespace),
                'authors': [a.text for a in entry.findall('atom:author/atom:name', namespace)],
                'summary': self._get_text(entry, 'atom:summary', namespace),
                'published': self._get_text(entry, 'atom:published', namespace),
                'arxiv_id': self._get_arxiv_id(entry, namespace),
                'pdf_url': self._get_pdf_url(entry, namespace),
                'categories': [c.get('term') for c in entry.findall('atom:category', namespace)]
            }
            papers.append(paper)
        
        return papers
    
    def _get_text(self, entry: ET.Element, path: str, namespace: dict) -> str:
        """获取 XML 节点文本"""
        elem = entry.find(path, namespace)
        return elem.text.strip() if elem is not None and elem.text else ''
    
    def _get_arxiv_id(self, entry: ET.Element, namespace: dict) -> str:
        """获取 arXiv ID"""
        id_elem = entry.find('atom:id', namespace)
        if id_elem is not None and id_elem.text:
            # 从 URL 中提取 arXiv ID
            url = id_elem.text
            if 'arxiv.org/abs/' in url:
                return url.split('arxiv.org/abs/')[-1]
        return ''
    
    def _get_pdf_url(self, entry: ET.Element, namespace: dict) -> str:
        """获取 PDF 下载 URL"""
        arxiv_id = self._get_arxiv_id(entry, namespace)
        if arxiv_id:
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return ''
    
    def download_pdf(self, pdf_url: str, save_path: str) -> bool:
        """
        下载 PDF 文件
        
        Args:
            pdf_url: PDF 下载 URL
            save_path: 保存路径
            
        Returns:
            是否成功
        """
        try:
            urllib.request.urlretrieve(pdf_url, save_path)
            return True
        except Exception as e:
            print(f"下载 PDF 失败：{e}")
            return False
    
    def search_by_author(self, author: str, max_results: int = 10) -> List[Dict]:
        """按作者搜索"""
        return self.search(f"au:{author}", max_results)
    
    def search_by_title(self, title: str, max_results: int = 10) -> List[Dict]:
        """按标题搜索"""
        return self.search(f"ti:{title}", max_results)
    
    def search_by_category(self, category: str, max_results: int = 10) -> List[Dict]:
        """按分类搜索 (如 cs.AI, physics, etc.)"""
        query = f"cat:{category}"
        return self.search(query, max_results)


# 测试
if __name__ == '__main__':
    client = ArXivClient()
    
    print("测试 1: 搜索 'transformer'")
    papers = client.search('transformer', max_results=3)
    for i, paper in enumerate(papers):
        print(f"{i+1}. {paper['title'][:60]}...")
        print(f"   作者：{', '.join(paper['authors'][:3])}")
        print(f"   arXiv: {paper['arxiv_id']}")
        print()
