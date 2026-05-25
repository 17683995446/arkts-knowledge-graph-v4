# -*- coding: utf-8 -*-
"""
智能代码搜索模块
基于语义的代码搜索（非关键词匹配），支持相似代码推荐
"""

import sqlite3
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import math


@dataclass
class SearchResult:
    """搜索结果"""
    name: str
    entity_type: str  # class, method, component
    file_path: str
    line_number: int
    content: str
    relevance_score: float
    matched_terms: List[str]


class SmartSearcher:
    """智能代码搜索引擎"""

    # 同义词映射
    SYNONYMS = {
        'get': ['fetch', 'retrieve', 'load', 'read', 'query'],
        'set': ['update', 'write', 'save', 'modify', 'change'],
        'create': ['make', 'build', 'generate', 'new', 'init'],
        'delete': ['remove', 'clear', 'destroy', 'drop'],
        'check': ['validate', 'verify', 'test', 'is', 'has'],
        'find': ['search', 'lookup', 'locate', 'get'],
        'handle': ['process', 'manage', 'deal', 'on'],
        'show': ['display', 'render', 'present', 'visible'],
        'hide': ['conceal', 'invisible', 'dismiss'],
        'start': ['begin', 'launch', 'open', 'init'],
        'stop': ['end', 'close', 'finish', 'terminate'],
    }

    # 命名模式权重
    PATTERN_WEIGHTS = {
        'on_': 1.2,      # 事件处理
        'get_': 1.1,     # 获取器
        'set_': 1.1,     # 设置器
        'is_': 1.1,      # 布尔判断
        'has_': 1.1,     # 存在判断
        'build_': 1.05,  # 构建
        'create_': 1.05, # 创建
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._build_index()

    def _build_index(self):
        """构建搜索索引"""
        self.entity_index = []

        # 索引类
        for row in self.conn.execute(
            "SELECT name, file, line_number, is_component FROM classes"
        ).fetchall():
            self.entity_index.append({
                'name': row['name'],
                'type': 'component' if row['is_component'] else 'class',
                'file': row['file'],
                'line': row['line_number'],
                'tokens': self._tokenize(row['name'])
            })

        # 索引方法
        for row in self.conn.execute(
            "SELECT name, class_name, file, line_number FROM methods"
        ).fetchall():
            full_name = f"{row['class_name']}.{row['name']}"
            self.entity_index.append({
                'name': full_name,
                'type': 'method',
                'file': row['file'],
                'line': row['line_number'],
                'tokens': self._tokenize(row['name']) + self._tokenize(row['class_name'])
            })

    def _tokenize(self, text: str) -> List[str]:
        """将文本分词"""
        # 驼峰命名拆分
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', text)
        # 下划线拆分
        words = [w for word in words for w in word.lower().split('_') if w]
        return words

    def _expand_query(self, query: str) -> List[str]:
        """扩展查询词（同义词扩展）"""
        tokens = self._tokenize(query)
        expanded = set(tokens)

        for token in tokens:
            # 添加同义词
            for word, synonyms in self.SYNONYMS.items():
                if token == word or token in synonyms:
                    expanded.add(word)
                    expanded.update(synonyms)

        return list(expanded)

    def _calculate_similarity(self, query_tokens: List[str], entity_tokens: List[str]) -> float:
        """计算相似度分数"""
        if not query_tokens or not entity_tokens:
            return 0.0

        # 精确匹配加分
        exact_matches = sum(1 for t in query_tokens if t in entity_tokens)

        # 部分匹配
        partial_matches = 0
        for qt in query_tokens:
            for et in entity_tokens:
                if qt in et or et in qt:
                    partial_matches += 0.5

        # TF-IDF风格加权
        query_set = set(query_tokens)
        entity_set = set(entity_tokens)

        # Jaccard相似度
        intersection = len(query_set & entity_set)
        union = len(query_set | entity_set)
        jaccard = intersection / union if union > 0 else 0

        # 综合分数
        score = (exact_matches * 2 + partial_matches + jaccard * 3) / max(len(query_tokens), 1)

        return min(100, score)

    def _apply_pattern_bonus(self, entity_name: str, base_score: float) -> float:
        """应用命名模式加分"""
        name_lower = entity_name.lower()

        for pattern, weight in self.PATTERN_WEIGHTS.items():
            if name_lower.startswith(pattern):
                return base_score * weight

        return base_score

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """执行智能搜索"""
        if not query or len(query.strip()) < 2:
            return []

        query_tokens = self._expand_query(query)
        results = []

        for entity in self.entity_index:
            # 计算相似度
            score = self._calculate_similarity(query_tokens, entity['tokens'])

            if score > 0:
                # 应用模式加分
                score = self._apply_pattern_bonus(entity['name'], score)

                # 找到匹配的词汇
                matched = [t for t in query_tokens if t in entity['tokens']]

                results.append(SearchResult(
                    name=entity['name'],
                    entity_type=entity['type'],
                    file_path=entity['file'],
                    line_number=entity['line'],
                    content=self._get_content(entity['file'], entity['line']),
                    relevance_score=round(score, 2),
                    matched_terms=matched
                ))

        # 按相关度排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    def _get_content(self, file_path: str, line_number: int) -> str:
        """获取代码内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if 0 < line_number <= len(lines):
                    return lines[line_number - 1].strip()
        except Exception:
            pass
        return ""

    def find_similar(self, entity_name: str, limit: int = 10) -> List[SearchResult]:
        """查找相似代码"""
        # 找到目标实体
        target = None
        for entity in self.entity_index:
            if entity['name'] == entity_name or entity['name'].endswith('.' + entity_name):
                target = entity
                break

        if not target:
            return []

        results = []
        for entity in self.entity_index:
            if entity['name'] == target['name']:
                continue

            # 计算相似度
            score = self._calculate_similarity(target['tokens'], entity['tokens'])

            if score > 5:  # 阈值
                results.append(SearchResult(
                    name=entity['name'],
                    entity_type=entity['type'],
                    file_path=entity['file'],
                    line_number=entity['line'],
                    content=self._get_content(entity['file'], entity['line']),
                    relevance_score=round(score, 2),
                    matched_terms=[]
                ))

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    def search_by_pattern(self, pattern_type: str) -> List[SearchResult]:
        """按模式搜索（如所有事件处理器）"""
        patterns = {
            'event_handler': r'^on[A-Z]',
            'getter': r'^get[A-Z]',
            'setter': r'^set[A-Z]',
            'boolean': r'^is[A-Z]|^has[A-Z]|^can[A-Z]',
            'factory': r'^create[A-Z]|^build[A-Z]|^make[A-Z]',
            'lifecycle': r'^aboutTo|^(on|did)[A-Z]',
        }

        regex = patterns.get(pattern_type, pattern_type)

        results = []
        for entity in self.entity_index:
            if re.search(regex, entity['name']):
                results.append(SearchResult(
                    name=entity['name'],
                    entity_type=entity['type'],
                    file_path=entity['file'],
                    line_number=entity['line'],
                    content=self._get_content(entity['file'], entity['line']),
                    relevance_score=100.0,
                    matched_terms=[pattern_type]
                ))

        return results

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def smart_search(db_path: str, query: str, limit: int = 20) -> List[Dict]:
    """便捷函数：执行智能搜索"""
    searcher = SmartSearcher(db_path)
    try:
        results = searcher.search(query, limit)
        return [
            {
                "name": r.name,
                "type": r.entity_type,
                "file": r.file_path,
                "line": r.line_number,
                "content": r.content[:100] if r.content else "",
                "score": r.relevance_score,
                "matched": r.matched_terms
            }
            for r in results
        ]
    finally:
        searcher.close()


def find_similar_code(db_path: str, entity_name: str, limit: int = 10) -> List[Dict]:
    """便捷函数：查找相似代码"""
    searcher = SmartSearcher(db_path)
    try:
        results = searcher.find_similar(entity_name, limit)
        return [
            {
                "name": r.name,
                "type": r.entity_type,
                "file": r.file_path,
                "line": r.line_number,
                "score": r.relevance_score
            }
            for r in results
        ]
    finally:
        searcher.close()


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage: python smart_search.py <db_path> <query>")
        sys.exit(1)

    db_path, query = sys.argv[1], sys.argv[2]
    results = smart_search(db_path, query)
    print(json.dumps(results, indent=2, ensure_ascii=False))
