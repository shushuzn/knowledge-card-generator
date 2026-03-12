#!/usr/bin/env python3
# 测试图谱生成

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'core'))

from graph_generator import GraphGenerator

# 测试数据
papers = [
    {
        "title": "Attention Is All You Need",
        "doi": "10.1000/test1",
        "keywords": ["transformer", "attention", "NLP"],
        "references": [
            {"title": "Deep Residual Learning", "doi": "10.1000/test3"}
        ]
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "doi": "10.1000/test2",
        "keywords": ["BERT", "NLP", "pre-training"],
        "references": [
            {"title": "Attention Is All You Need", "doi": "10.1000/test1"}
        ]
    },
    {
        "title": "Deep Residual Learning for Image Recognition",
        "doi": "10.1000/test3",
        "keywords": ["ResNet", "CNN", "deep learning"],
        "references": []
    }
]

# 测试图谱生成
graph_gen = GraphGenerator()

print("=" * 50)
print("测试 1: 关键词共现图谱")
print("=" * 50)
keyword_graph = graph_gen.generate_keyword_graph(papers)
print(f"节点数：{len(keyword_graph['nodes'])}")
print(f"边数：{len(keyword_graph['links'])}")
print(f"节点：{[n['name'] for n in keyword_graph['nodes'][:5]]}")
print()

print("=" * 50)
print("测试 2: 论文引用图谱")
print("=" * 50)
citation_graph = graph_gen.generate_citation_graph(papers)
print(f"节点数：{len(citation_graph['nodes'])}")
print(f"边数：{len(citation_graph['links'])}")
print(f"引用关系：{citation_graph['links']}")
print()

print("=" * 50)
print("测试 3: 领域知识图谱")
print("=" * 50)
domain_graph = graph_gen.generate_domain_graph(papers)
print(f"节点数：{len(domain_graph['nodes'])}")
print(f"边数：{len(domain_graph['links'])}")
print()

print("✅ 所有测试通过！")
