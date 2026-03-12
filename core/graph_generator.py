#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱生成器 - 从 PDF 生成三种图谱
"""

import re
from pathlib import Path
from typing import Dict, List
from collections import Counter

# 导入知识卡片生成器
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from knowledge_card_generator import KnowledgeCardGenerator
    from keyword_extractor import KeywordExtractor
except ImportError:
    # 测试模式
    KnowledgeCardGenerator = None
    KeywordExtractor = None


class GraphGenerator:
    """知识图谱生成器"""
    
    def __init__(self):
        if KnowledgeCardGenerator:
            self.generator = KnowledgeCardGenerator()
        if KeywordExtractor:
            self.extractor = KeywordExtractor()
    
    def extract_keywords(self, text: str, top_n: int = 50) -> List[str]:
        """提取关键词 (TF-IDF + TextRank)"""
        return self.extractor.extract_combined(text, top_n=top_n)
    
    def generate_keyword_graph(self, papers: List[Dict]) -> Dict:
        """
        生成关键词共现图谱
        
        Args:
            papers: 论文列表，每篇包含 keywords 字段
            
        Returns:
            图谱数据 {nodes, links, categories}
        """
        # 收集所有关键词
        all_keywords = set()
        paper_keywords = []
        
        for paper in papers:
            keywords = paper.get('keywords', [])
            all_keywords.update(keywords)
            paper_keywords.append(keywords)
        
        # 创建节点
        nodes = [
            {"name": kw, "symbolSize": 20 + len(kw) * 2, "category": 0}
            for kw in all_keywords
        ]
        
        # 创建边 (共现关系)
        links = []
        for i, kw1 in enumerate(all_keywords):
            for kw2 in list(all_keywords)[i+1:]:
                # 计算共现次数
                cooccurrence = sum(
                    1 for kws in paper_keywords 
                    if kw1 in kws and kw2 in kws
                )
                if cooccurrence > 0:
                    links.append({
                        "source": kw1,
                        "target": kw2,
                        "value": cooccurrence
                    })
        
        return {
            "nodes": nodes,
            "links": links,
            "categories": [{"name": "关键词"}],
            "stats": {
                "nodes": len(nodes),
                "links": len(links),
                "papers": len(papers)
            }
        }
    
    def generate_citation_graph(self, papers: List[Dict]) -> Dict:
        """
        生成论文引用图谱 (DOI 匹配 + 标题模糊匹配)
        
        Args:
            papers: 论文列表，每篇包含 references 字段
            
        Returns:
            图谱数据 {nodes, links, categories}
        """
        # 1. 创建论文索引 (DOI 和标题)
        doi_index = {}  # DOI → paper_id
        title_index = {}  # 标题简化 → paper_id
        
        for i, paper in enumerate(papers):
            # DOI 索引
            doi = paper.get('doi', '')
            if doi:
                doi_index[doi.lower()] = i
            
            # 标题索引 (简化版)
            title = paper.get('title', '')
            if title:
                simplified = self._simplify_title(title)
                title_index[simplified] = i
        
        # 2. 创建论文节点
        nodes = []
        for i, paper in enumerate(papers):
            title = paper.get('title', f'Paper {i}')
            nodes.append({
                "name": title[:50] + '...' if len(title) > 50 else title,
                "symbolSize": 30,
                "category": 0,
                "paper_id": i,
                "year": paper.get('year', 'Unknown')
            })
        
        # 3. 创建引用边 (DOI 匹配 + 标题匹配)
        links = []
        link_set = set()  # 避免重复
        
        for i, paper in enumerate(papers):
            references = paper.get('references', [])
            
            for ref in references:
                target_id = None
                
                # 尝试 DOI 匹配
                ref_doi = ref.get('doi', '')
                if ref_doi:
                    target_id = doi_index.get(ref_doi.lower())
                
                # 尝试标题匹配
                if target_id is None:
                    ref_title = ref.get('title', '')
                    if ref_title:
                        simplified = self._simplify_title(ref_title)
                        target_id = title_index.get(simplified)
                
                # 找到匹配的引用
                if target_id is not None and target_id != i:
                    link_key = f"{i}->{target_id}"
                    if link_key not in link_set:
                        links.append({
                            "source": i,
                            "target": target_id,
                            "value": 1
                        })
                        link_set.add(link_key)
        
        # 确保节点有 name 字段
        for node in nodes:
            if "name" not in node:
                node["name"] = f"Paper {node.get('paper_id', 'Unknown')}"
            if "symbolSize" not in node:
                node["symbolSize"] = 30
        
        return {
            "nodes": nodes,
            "links": links,
            "categories": [{"name": "论文"}],
            "stats": {
                "nodes": len(nodes),
                "links": len(links),
                "papers": len(papers)
            }
        }
    
    def _simplify_title(self, title: str) -> str:
        """
        简化标题用于匹配
        
        Args:
            title: 原始标题
            
        Returns:
            简化后的标题
        """
        # 转小写
        simplified = title.lower()
        # 移除标点
        simplified = re.sub(r'[^\w\s]', '', simplified)
        # 移除多余空格
        simplified = ' '.join(simplified.split())
        # 移除常见前缀
        for prefix in ['a ', 'an ', 'the ']:
            if simplified.startswith(prefix):
                simplified = simplified[len(prefix):]
        return simplified
    
    def generate_domain_graph(self, papers: List[Dict]) -> Dict:
        """
        生成领域知识图谱 (概念 + 关系)
        
        Args:
            papers: 论文列表
            
        Returns:
            图谱数据 {nodes, links, categories}
        """
        # 简单实现：提取领域相关概念
        domain_concepts = {
            "machine learning": 0,
            "deep learning": 0,
            "neural network": 0,
            "optimization": 0,
            "classification": 0,
            "regression": 0,
            "clustering": 0,
            "feature extraction": 0,
        }
        
        # 统计概念出现
        for paper in papers:
            text = (paper.get('title', '') + ' ' + 
                   paper.get('abstract', '')).lower()
            
            for concept in domain_concepts:
                if concept in text:
                    domain_concepts[concept] += 1
        
        # 创建节点
        nodes = [
            {"name": concept, "symbolSize": 20 + count * 5, "category": 0}
            for concept, count in domain_concepts.items() if count > 0
        ]
        
        # 创建关系 (预定义)
        relations = [
            ("machine learning", "deep learning"),
            ("machine learning", "optimization"),
            ("machine learning", "classification"),
            ("machine learning", "regression"),
            ("machine learning", "clustering"),
            ("deep learning", "neural network"),
            ("neural network", "optimization"),
            ("classification", "feature extraction"),
            ("regression", "feature extraction"),
        ]
        
        links = [
            {"source": s, "target": t, "value": 1}
            for s, t in relations
            if any(n["name"] == s for n in nodes) and 
               any(n["name"] == t for n in nodes)
        ]
        
        return {
            "nodes": nodes,
            "links": links,
            "categories": [{"name": "领域概念"}],
            "stats": {
                "nodes": len(nodes),
                "links": len(links),
                "papers": len(papers)
            }
        }
