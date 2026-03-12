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
from knowledge_card_generator import KnowledgeCardGenerator


class GraphGenerator:
    """知识图谱生成器"""
    
    def __init__(self):
        self.generator = KnowledgeCardGenerator()
        # 常见停用词 (中文 + 英文)
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            '的', '了', '和', '与', '及', '或', '在', '是', '有', '等', '一个'
        }
    
    def extract_keywords(self, text: str, top_n: int = 50) -> List[str]:
        """提取关键词"""
        # 简单分词 (按空格和标点)
        words = re.findall(r'\b\w+\b|\w+', text.lower())
        
        # 过滤停用词和短词
        keywords = [
            w for w in words 
            if w not in self.stopwords 
            and len(w) > 2
        ]
        
        # 词频统计
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(top_n)]
    
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
        生成论文引用图谱
        
        Args:
            papers: 论文列表，每篇包含 references 字段
            
        Returns:
            图谱数据 {nodes, links, categories}
        """
        # 创建论文节点
        paper_nodes = {}
        for i, paper in enumerate(papers):
            title = paper.get('title', f'Paper {i}')
            paper_nodes[title] = {
                "name": title[:50] + '...' if len(title) > 50 else title,
                "symbolSize": 30,
                "category": 0,
                "paper_id": i
            }
        
        # 创建引用边
        links = []
        for i, paper in enumerate(papers):
            paper_title = paper.get('title', f'Paper {i}')
            references = paper.get('references', [])
            
            for ref in references:
                ref_title = ref.get('title', '')
                if ref_title in paper_nodes:
                    links.append({
                        "source": paper_title[:50] + '...' if len(paper_title) > 50 else paper_title,
                        "target": ref_title[:50] + '...' if len(ref_title) > 50 else ref_title,
                        "value": 1
                    })
        
        return {
            "nodes": list(paper_nodes.values()),
            "links": links,
            "categories": [{"name": "论文"}],
            "stats": {
                "nodes": len(paper_nodes),
                "links": len(links),
                "papers": len(papers)
            }
        }
    
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
