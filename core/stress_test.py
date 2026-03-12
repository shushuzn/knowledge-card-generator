#!/usr/bin/env python3
# 压力测试 - 生成大规模测试数据

import json
import random
from pathlib import Path

def generate_large_dataset(n_papers=100):
    """生成大规模测试数据集"""
    
    # 领域关键词
    fields = {
        'NLP': ['BERT', 'transformer', 'attention', 'NLP', 'language model', 'pre-training'],
        'CV': ['CNN', 'ResNet', 'AlexNet', 'ImageNet', 'image classification', 'object detection'],
        'ML': ['deep learning', 'neural network', 'optimization', 'gradient', 'loss function']
    }
    
    papers = []
    for i in range(n_papers):
        # 随机生成论文
        field = random.choice(list(fields.keys()))
        keywords = random.sample(fields[field], min(4, len(fields[field])))
        
        year = random.randint(2010, 2024)
        
        # 生成引用 (引用更早的论文)
        references = []
        if i > 0:
            n_refs = random.randint(0, min(5, i))
            ref_indices = random.sample(range(i), n_refs)
            for idx in ref_indices:
                references.append({
                    "title": f"Paper {idx}",
                    "doi": f"10.1000/test{idx}"
                })
        
        papers.append({
            "id": i + 1,
            "title": f"Paper {i + 1}: A Study on {random.choice(keywords)}",
            "doi": f"10.1000/test{i}",
            "year": year,
            "keywords": keywords,
            "references": references
        })
    
    return {"papers": papers, "description": f"{n_papers} 篇测试论文"}

# 生成测试数据
print("生成 100 篇测试论文...")
data_100 = generate_large_dataset(100)

print("生成 500 篇测试论文...")
data_500 = generate_large_dataset(500)

# 保存
output_dir = Path(__file__).parent.parent / 'data'
output_dir.mkdir(exist_ok=True)

with open(output_dir / 'test_100_papers.json', 'w', encoding='utf-8') as f:
    json.dump(data_100, f, ensure_ascii=False, indent=2)

with open(output_dir / 'test_500_papers.json', 'w', encoding='utf-8') as f:
    json.dump(data_500, f, ensure_ascii=False, indent=2)

print(f"✅ 测试数据已保存到 {output_dir}")
print(f"   - test_100_papers.json (100 篇)")
print(f"   - test_500_papers.json (500 篇)")
