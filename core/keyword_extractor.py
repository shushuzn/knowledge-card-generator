#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词提取器 - TF-IDF + TextRank
"""

import re
from typing import List, Dict
from collections import Counter
import math


class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        # 停用词 (中英文)
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'this', 'that', 'these', 'those', 'it', 'its', 'as', 'also', 'can',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'than', 'then', 'so', 'if', 'when',
            'what', 'which', 'who', 'whom', 'whose', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'not', 'only', 'same', 'just', 'own', 's', 't', 'd', 'll', 've', 're',
            # 中文停用词
            '的', '了', '和', '与', '及', '或', '在', '是', '有', '等', '一个',
            '我们', '他们', '它们', '这个', '那个', '这些', '那些', '可以',
            '可能', '应该', '必须', '能够', '以及', '因此', '所以', '但是',
            '而且', '或者', '如果', '虽然', '因为', '所以', '然而', '尽管'
        }
        
        # 常见学术词汇 (应该保留)
        self.academic_keywords = {
            'machine learning', 'deep learning', 'neural network', 'artificial intelligence',
            'optimization', 'classification', 'regression', 'clustering', 'feature extraction',
            'convolutional', 'recurrent', 'transformer', 'attention', 'embedding',
            'gradient', 'backpropagation', 'loss function', 'activation function',
            'dataset', 'benchmark', 'evaluation', 'metric', 'accuracy', 'precision',
            'recall', 'f1-score', 'cross-validation', 'overfitting', 'underfitting',
            'regularization', 'dropout', 'batch normalization', 'residual', 'skip connection'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """分词 (简单实现)"""
        # 转小写
        text = text.lower()
        
        # 提取单词 (包括连字符)
        words = re.findall(r'\b[a-z][a-z-]*[a-z]\b|\b[a-z]\b', text)
        
        # 过滤停用词和短词
        filtered = [
            w for w in words 
            if w not in self.stopwords 
            and len(w) > 2
        ]
        
        return filtered
    
    def extract_tfidf(self, documents: List[str], top_n: int = 50) -> List[str]:
        """
        TF-IDF 关键词提取
        
        Args:
            documents: 文档列表
            top_n: 返回前 N 个关键词
            
        Returns:
            关键词列表
        """
        # 分词
        tokenized_docs = [self.tokenize(doc) for doc in documents]
        
        # 计算词频 (TF)
        all_words = [word for doc in tokenized_docs for word in doc]
        word_freq = Counter(all_words)
        
        # 计算文档频率 (DF)
        doc_freq = Counter()
        for doc in tokenized_docs:
            unique_words = set(doc)
            for word in unique_words:
                doc_freq[word] += 1
        
        # 计算 IDF
        n_docs = len(documents)
        idf = {
            word: math.log(n_docs / (1 + df)) 
            for word, df in doc_freq.items()
        }
        
        # 计算 TF-IDF
        tfidf_scores = {
            word: word_freq[word] * idf.get(word, 0)
            for word in word_freq
        }
        
        # 返回 top N
        sorted_words = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in sorted_words[:top_n]]
    
    def extract_textrank(self, text: str, top_n: int = 50) -> List[str]:
        """
        TextRank 关键词提取 (简化版)
        
        Args:
            text: 文本
            top_n: 返回前 N 个关键词
            
        Returns:
            关键词列表
        """
        # 分词
        words = self.tokenize(text)
        
        # 构建共现图 (窗口大小=4)
        window_size = 4
        cooccurrence = Counter()
        
        for i in range(len(words)):
            for j in range(i+1, min(i+window_size, len(words))):
                word1, word2 = words[i], words[j]
                if word1 != word2:
                    pair = tuple(sorted([word1, word2]))
                    cooccurrence[pair] += 1
        
        # 计算 PageRank (简化版：用共现次数代替)
        word_scores = Counter()
        for (word1, word2), count in cooccurrence.items():
            word_scores[word1] += count
            word_scores[word2] += count
        
        # 返回 top N
        sorted_words = word_scores.most_common(top_n)
        return [word for word, score in sorted_words]
    
    def extract_phrases(self, text: str, top_n: int = 30) -> List[str]:
        """
        提取关键短语 (2-3 词短语)
        
        Args:
            text: 文本
            top_n: 返回前 N 个短语
            
        Returns:
            短语列表
        """
        # 分词
        words = self.tokenize(text)
        
        # 提取双词短语
        bigrams = Counter()
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            # 过滤包含停用词的短语
            if words[i] not in self.stopwords and words[i+1] not in self.stopwords:
                bigrams[phrase] += 1
        
        # 提取三词短语
        trigrams = Counter()
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            if all(w not in self.stopwords for w in [words[i], words[i+1], words[i+2]]):
                trigrams[phrase] += 1
        
        # 合并排序
        all_phrases = Counter()
        for phrase, count in bigrams.most_common(20):
            all_phrases[phrase] = count * 1.5  # 双词权重高
        for phrase, count in trigrams.most_common(10):
            all_phrases[phrase] = count
        
        sorted_phrases = all_phrases.most_common(top_n)
        return [phrase for phrase, count in sorted_phrases]
    
    def extract_combined(self, text: str, documents: List[str] = None, top_n: int = 50) -> List[str]:
        """
        组合方法提取关键词
        
        Args:
            text: 单篇文本
            documents: 多篇文档 (用于 TF-IDF)
            top_n: 返回前 N 个关键词
            
        Returns:
            关键词列表
        """
        keywords = []
        
        # 1. TF-IDF (如果有多篇文档)
        if documents and len(documents) > 1:
            tfidf_kw = self.extract_tfidf(documents, top_n // 2)
            keywords.extend(tfidf_kw)
        
        # 2. TextRank
        textrank_kw = self.extract_textrank(text, top_n // 2)
        keywords.extend(textrank_kw)
        
        # 3. 关键短语
        phrases = self.extract_phrases(text, top_n // 3)
        keywords.extend(phrases)
        
        # 去重 (保留顺序)
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:top_n]


# 测试
if __name__ == '__main__':
    extractor = KeywordExtractor()
    
    # 测试文本
    test_text = """
    Machine learning is a subset of artificial intelligence that focuses on 
    developing algorithms and statistical models that enable computers to perform 
    tasks without explicit instructions. Deep learning, a type of machine learning, 
    uses neural networks with multiple layers to learn hierarchical representations.
    """
    
    keywords = extractor.extract_combined(test_text, top_n=10)
    print(f"关键词：{keywords}")
