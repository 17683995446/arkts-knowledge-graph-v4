# -*- coding: utf-8 -*-
"""
ArkTS 代码质量分析器
提供代码质量评分、坏味道检测、复杂度分析等功能
"""

import re
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class QualityMetrics:
    """代码质量指标"""
    file_path: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    class_count: int
    method_count: int
    avg_method_length: float
    max_method_length: int
    complexity_score: float  # 圈复杂度
    maintainability_index: float  # 可维护性指数
    duplicate_score: float  # 重复代码评分
    naming_score: float  # 命名规范评分
    overall_score: float  # 综合评分
    issues: List[Dict]  # 发现的问题


class CodeQualityAnalyzer:
    """代码质量分析器"""

    # 代码坏味道规则
    CODE_SMELLS = {
        'long_method': {'threshold': 50, 'weight': -5, 'name': '方法过长'},
        'long_class': {'threshold': 300, 'weight': -5, 'name': '类过大'},
        'too_many_params': {'threshold': 5, 'weight': -3, 'name': '参数过多'},
        'deep_nesting': {'threshold': 4, 'weight': -4, 'name': '嵌套过深'},
        'missing_comments': {'threshold': 0.1, 'weight': -2, 'name': '缺少注释'},
        'todo_fixme': {'weight': -1, 'name': '待办事项'},
        'magic_number': {'weight': -2, 'name': '魔法数字'},
        'empty_catch': {'weight': -5, 'name': '空异常处理'},
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def analyze_file(self, file_path: str) -> QualityMetrics:
        """分析单个文件的质量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return None

        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = self._count_comment_lines(lines)
        code_lines = total_lines - blank_lines - comment_lines

        # 获取类和方法信息
        classes = self._get_classes_in_file(file_path)
        methods = self._get_methods_in_file(file_path)

        class_count = len(classes)
        method_count = len(methods)

        # 计算方法长度统计
        method_lengths = [m.get('line_count', 0) for m in methods]
        avg_method_length = sum(method_lengths) / max(len(method_lengths), 1)
        max_method_length = max(method_lengths) if method_lengths else 0

        # 检测问题
        issues = []
        issues.extend(self._detect_long_methods(methods))
        issues.extend(self._detect_long_classes(classes))
        issues.extend(self._detect_todo_fixme(content, file_path))
        issues.extend(self._detect_deep_nesting(content, file_path))
        issues.extend(self._detect_magic_numbers(content, file_path))
        issues.extend(self._detect_empty_catch(content, file_path))

        # 计算各项评分
        complexity_score = self._calculate_complexity(methods, classes)
        maintainability_index = self._calculate_maintainability(
            code_lines, comment_lines, complexity_score, method_count
        )
        duplicate_score = 100  # 简化处理
        naming_score = self._check_naming_conventions(classes, methods)

        # 计算综合评分
        overall_score = self._calculate_overall_score(
            maintainability_index, complexity_score, duplicate_score,
            naming_score, issues
        )

        return QualityMetrics(
            file_path=file_path,
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            class_count=class_count,
            method_count=method_count,
            avg_method_length=avg_method_length,
            max_method_length=max_method_length,
            complexity_score=complexity_score,
            maintainability_index=maintainability_index,
            duplicate_score=duplicate_score,
            naming_score=naming_score,
            overall_score=overall_score,
            issues=issues
        )

    def _count_comment_lines(self, lines: List[str]) -> int:
        """统计注释行数"""
        comment_lines = 0
        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if in_block_comment:
                comment_lines += 1
                if '*/' in stripped:
                    in_block_comment = False
            elif stripped.startswith('//'):
                comment_lines += 1
            elif stripped.startswith('/*'):
                comment_lines += 1
                if '*/' not in stripped:
                    in_block_comment = True

        return comment_lines

    def _get_classes_in_file(self, file_path: str) -> List[Dict]:
        """获取文件中的类"""
        cursor = self.conn.execute(
            "SELECT name, line_number FROM classes WHERE file = ?",
            (file_path,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def _get_methods_in_file(self, file_path: str) -> List[Dict]:
        """获取文件中的方法"""
        cursor = self.conn.execute(
            """SELECT name, class_name, line_number,
                      (SELECT COUNT(*) FROM calls WHERE caller = methods.name) as call_count
               FROM methods WHERE file = ?""",
            (file_path,)
        )
        methods = [dict(row) for row in cursor.fetchall()]

        # 估算方法长度
        for method in methods:
            method['line_count'] = self._estimate_method_length(file_path, method['line_number'])

        return methods

    def _estimate_method_length(self, file_path: str, start_line: int) -> int:
        """估算方法长度"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if start_line > len(lines):
                return 0

            # 从方法开始行查找结束
            brace_count = 0
            line_count = 0
            started = False

            for i in range(start_line - 1, min(len(lines), start_line + 200)):
                line = lines[i]
                line_count += 1

                if '{' in line:
                    brace_count += line.count('{')
                    started = True
                if '}' in line:
                    brace_count -= line.count('}')

                if started and brace_count == 0:
                    break

            return line_count
        except Exception:
            return 0

    def _detect_long_methods(self, methods: List[Dict]) -> List[Dict]:
        """检测过长方法"""
        issues = []
        threshold = self.CODE_SMELLS['long_method']['threshold']

        for method in methods:
            if method.get('line_count', 0) > threshold:
                issues.append({
                    'type': 'long_method',
                    'severity': 'warning',
                    'message': f"方法 '{method['name']}' 过长 ({method['line_count']} 行)",
                    'location': f"{method.get('class_name', 'global')}.{method['name']}",
                    'line': method.get('line_number', 0)
                })

        return issues

    def _detect_long_classes(self, classes: List[Dict]) -> List[Dict]:
        """检测过大类"""
        issues = []
        # 简化处理：假设每个类平均方法数超过20为过大
        for cls in classes:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM methods WHERE class_name = ?",
                (cls['name'],)
            )
            method_count = cursor.fetchone()[0]

            if method_count > 20:
                issues.append({
                    'type': 'long_class',
                    'severity': 'warning',
                    'message': f"类 '{cls['name']}' 方法过多 ({method_count} 个)",
                    'location': cls['name'],
                    'line': cls.get('line_number', 0)
                })

        return issues

    def _detect_todo_fixme(self, content: str, file_path: str) -> List[Dict]:
        """检测TODO/FIXME标记"""
        issues = []
        pattern = r'(?:TODO|FIXME|XXX|HACK)[\s:]*(.*)'

        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            issues.append({
                'type': 'todo_fixme',
                'severity': 'info',
                'message': f"待办: {match.group(1).strip()}",
                'location': file_path,
                'line': line_num
            })

        return issues

    def _detect_deep_nesting(self, content: str, file_path: str) -> List[Dict]:
        """检测过深嵌套"""
        issues = []
        lines = content.split('\n')
        max_depth = self.CODE_SMELLS['deep_nesting']['threshold']

        for i, line in enumerate(lines):
            depth = len(re.match(r'^(\s*)', line).group(1)) // 2
            if depth > max_depth:
                issues.append({
                    'type': 'deep_nesting',
                    'severity': 'warning',
                    'message': f"嵌套层级过深 ({depth} 层)",
                    'location': file_path,
                    'line': i + 1
                })

        return issues

    def _detect_magic_numbers(self, content: str, file_path: str) -> List[Dict]:
        """检测魔法数字"""
        issues = []
        # 匹配数字但排除常见情况
        pattern = r'[^\w](\d{2,})[^\w]'
        excluded = {'0', '1', '10', '100', '1000', '2', '3', '4', '5'}

        for match in re.finditer(pattern, content):
            num = match.group(1)
            if num not in excluded:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'magic_number',
                    'severity': 'info',
                    'message': f"魔法数字: {num}",
                    'location': file_path,
                    'line': line_num
                })

        return issues[:10]  # 限制数量

    def _detect_empty_catch(self, content: str, file_path: str) -> List[Dict]:
        """检测空异常处理"""
        issues = []
        pattern = r'catch\s*\([^)]*\)\s*\{\s*\}'

        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            issues.append({
                'type': 'empty_catch',
                'severity': 'error',
                'message': "空异常处理块",
                'location': file_path,
                'line': line_num
            })

        return issues

    def _calculate_complexity(self, methods: List[Dict], classes: List[Dict]) -> float:
        """计算复杂度评分"""
        if not methods:
            return 100

        # 基于方法调用关系计算复杂度
        total_complexity = 0
        for method in methods:
            # 基础复杂度 + 调用复杂度
            base = 1
            calls = method.get('call_count', 0)
            complexity = base + min(calls * 0.5, 10)
            total_complexity += complexity

        avg_complexity = total_complexity / len(methods)
        # 转换为评分 (0-100)
        score = max(0, 100 - avg_complexity * 5)
        return round(score, 2)

    def _calculate_maintainability(self, code_lines: int, comment_lines: int,
                                   complexity_score: float, method_count: int) -> float:
        """计算可维护性指数 (简化版)"""
        if code_lines == 0:
            return 100

        # 注释率
        comment_ratio = comment_lines / code_lines if code_lines > 0 else 0

        # 方法密度
        method_density = method_count / code_lines * 100 if code_lines > 0 else 0

        # 综合计算
        score = (
            complexity_score * 0.4 +  # 复杂度权重
            min(comment_ratio * 200, 30) +  # 注释权重
            min(method_density * 10, 30)  # 方法密度权重
        )

        return round(min(100, score), 2)

    def _check_naming_conventions(self, classes: List[Dict], methods: List[Dict]) -> float:
        """检查命名规范"""
        issues = 0
        total = len(classes) + len(methods)

        if total == 0:
            return 100

        # 检查类名 (PascalCase)
        for cls in classes:
            name = cls['name']
            if name and not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
                issues += 1

        # 检查方法名 (camelCase)
        for method in methods:
            name = method['name']
            if name and not re.match(r'^[a-z][a-zA-Z0-9]*$', name):
                issues += 1

        return round(max(0, 100 - issues / total * 20), 2)

    def _calculate_overall_score(self, maintainability: float, complexity: float,
                                  duplicate: float, naming: float,
                                  issues: List[Dict]) -> float:
        """计算综合评分"""
        base_score = (
            maintainability * 0.35 +
            complexity * 0.25 +
            duplicate * 0.20 +
            naming * 0.20
        )

        # 根据问题扣分
        deduction = sum(
            self.CODE_SMELLS.get(issue['type'], {}).get('weight', -1)
            for issue in issues
        )

        return round(max(0, min(100, base_score + deduction)), 2)

    def analyze_all_files(self) -> Dict:
        """分析所有文件"""
        cursor = self.conn.execute("SELECT path FROM files")
        files = [row[0] for row in cursor.fetchall()]

        results = []
        total_issues = defaultdict(int)

        for file_path in files:
            metrics = self.analyze_file(file_path)
            if metrics:
                results.append(metrics)
                for issue in metrics.issues:
                    total_issues[issue['type']] += 1

        # 计算项目级统计
        if results:
            avg_score = sum(r.overall_score for r in results) / len(results)
            total_lines = sum(r.total_lines for r in results)
            total_methods = sum(r.method_count for r in results)
        else:
            avg_score = 0
            total_lines = 0
            total_methods = 0

        return {
            'file_count': len(results),
            'total_lines': total_lines,
            'total_methods': total_methods,
            'average_score': round(avg_score, 2),
            'grade': self._score_to_grade(avg_score),
            'issue_summary': dict(total_issues),
            'files': [
                {
                    'path': r.file_path,
                    'score': r.overall_score,
                    'grade': self._score_to_grade(r.overall_score),
                    'lines': r.total_lines,
                    'methods': r.method_count,
                    'issues': len(r.issues)
                }
                for r in sorted(results, key=lambda x: x.overall_score)
            ]
        }

    def _score_to_grade(self, score: float) -> str:
        """分数转等级"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# 便捷函数
def analyze_quality(db_path: str) -> Dict:
    """分析代码质量并返回报告"""
    analyzer = CodeQualityAnalyzer(db_path)
    try:
        return analyzer.analyze_all_files()
    finally:
        analyzer.close()


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quality_analyzer.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    report = analyze_quality(db_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
