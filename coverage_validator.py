#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
覆盖率验证器 - Phase 1
独立于解析器，通过正则扫描源码与数据库对比，量化知识图谱完整性。
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class CoverageValidator:
    """知识图谱覆盖率验证器
    
    通过独立扫描源码并与数据库对比，量化实体和关系的提取完整性。
    """

    def __init__(self, db_path: str = "code.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def close(self):
        if self.conn:
            self.conn.close()

    # ========================================================================
    # 文件覆盖率
    # ========================================================================

    def check_file_coverage(self, project_path: str) -> Dict:
        """检查文件是否全部入库"""
        source_files = set()
        for ext in ['*.ets', '*.ts']:
            for f in Path(project_path).rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                source_files.add(fp)

        db_files = set()
        if self.conn:
            try:
                rows = self.conn.execute("SELECT path FROM files").fetchall()
                db_files = {row[0] for row in rows}
            except sqlite3.OperationalError:
                pass

        matched = source_files & db_files
        missing = source_files - db_files
        extra = db_files - source_files

        coverage = len(matched) / max(len(source_files), 1) * 100

        return {
            'label': '文件覆盖率',
            'source_count': len(source_files),
            'db_count': len(db_files),
            'matched': len(matched),
            'coverage': round(coverage, 1),
            'missing': sorted(missing)[:20],
            'extra': sorted(extra)[:20],
            'status': 'PASS' if coverage >= 95 else 'WARN' if coverage >= 80 else 'FAIL',
        }

    # ========================================================================
    # 类/struct 覆盖率
    # ========================================================================

    def check_class_coverage(self, project_path: str) -> Dict:
        """用独立正则扫描源码，与数据库对比"""
        source_classes = set()
        # 匹配 struct/class 定义（含 export/default/abstract 修饰符）
        class_re = re.compile(
            r'(?:export\s+)?(?:default\s+)?(?:abstract\s+)?'
            r'(?:struct|class)\s+(\w+)',
            re.MULTILINE
        )

        for ext in ['*.ets', '*.ts']:
            for f in Path(project_path).rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    for m in class_re.finditer(content):
                        source_classes.add((m.group(1), fp))
                except Exception:
                    pass

        db_classes = set()
        if self.conn:
            try:
                rows = self.conn.execute(
                    "SELECT name, file FROM classes"
                ).fetchall()
                db_classes = {(row[0], row[1]) for row in rows}
            except sqlite3.OperationalError:
                pass

        matched = source_classes & db_classes
        missing = source_classes - db_classes

        coverage = len(matched) / max(len(source_classes), 1) * 100

        return {
            'label': '类/struct覆盖率',
            'source_count': len(source_classes),
            'db_count': len(db_classes),
            'matched': len(matched),
            'coverage': round(coverage, 1),
            'missing': sorted(missing)[:20],
            'status': 'PASS' if coverage >= 95 else 'WARN' if coverage >= 80 else 'FAIL',
        }

    # ========================================================================
    # 方法覆盖率
    # ========================================================================

    def check_method_coverage(self, project_path: str) -> Dict:
        """检查每个类中的方法是否全部提取"""
        # 从数据库获取 (class_name, file) -> {method_names}
        db_class_methods: Dict[Tuple[str, str], Set[str]] = {}
        if self.conn:
            try:
                rows = self.conn.execute(
                    "SELECT name, class_name, file FROM methods"
                ).fetchall()
                for name, cls, fp in rows:
                    key = (cls, fp)
                    db_class_methods.setdefault(key, set()).add(name)
            except sqlite3.OperationalError:
                pass

        # 独立扫描源码中的方法定义
        source_class_methods: Dict[Tuple[str, str], Set[str]] = {}
        method_re = re.compile(
            r'(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:struct|class)\s+(\w+)'
            r'[^{]*\{',
            re.MULTILINE | re.DOTALL
        )

        for ext in ['*.ets', '*.ts']:
            for f in Path(project_path).rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    # 先找到类定义
                    for cm in method_re.finditer(content):
                        cls_name = cm.group(1)
                        # 提取类体
                        body = self._extract_brace_block(content, cm.end() - 1)
                        if body is None:
                            continue
                        # 在类体中找方法
                        methods = self._scan_methods_in_body(body)
                        if methods:
                            source_class_methods[(cls_name, fp)] = methods
                except Exception:
                    pass

        # 对比
        total_source = 0
        total_matched = 0
        missing_methods = []

        for key, methods in source_class_methods.items():
            total_source += len(methods)
            db_methods = db_class_methods.get(key, set())
            for m in methods:
                if m in db_methods:
                    total_matched += 1
                else:
                    missing_methods.append(f"{key[0]}.{m} ({Path(key[1]).name})")

        coverage = total_matched / max(total_source, 1) * 100

        return {
            'label': '方法覆盖率',
            'source_count': total_source,
            'db_count': sum(len(v) for v in db_class_methods.values()),
            'matched': total_matched,
            'coverage': round(coverage, 1),
            'missing': sorted(missing_methods)[:20],
            'status': 'PASS' if coverage >= 95 else 'WARN' if coverage >= 80 else 'FAIL',
        }

    # ========================================================================
    # 装饰器覆盖率
    # ========================================================================

    def check_decorator_coverage(self, project_path: str) -> Dict:
        """检查装饰器是否全部提取（当前系统不提取装饰器，预期覆盖率0%）"""
        source_dec_count = 0
        dec_re = re.compile(r'@(\w+)')

        for ext in ['*.ets', '*.ts']:
            for f in Path(project_path).rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        source_dec_count += len(dec_re.findall(fh.read()))
                except Exception:
                    pass

        db_dec_count = 0
        if self.conn:
            try:
                rows = self.conn.execute(
                    "SELECT COUNT(*) FROM decorators"
                ).fetchall()
                db_dec_count = rows[0][0]
            except sqlite3.OperationalError:
                # decorators 表不存在
                pass

        coverage = db_dec_count / max(source_dec_count, 1) * 100

        return {
            'label': '装饰器覆盖率',
            'source_count': source_dec_count,
            'db_count': db_dec_count,
            'matched': min(db_dec_count, source_dec_count),
            'coverage': round(coverage, 1),
            'missing': [],
            'status': 'N/A' if source_dec_count == 0 else ('PASS' if coverage >= 95 else 'WARN' if coverage >= 80 else 'FAIL'),
            'note': '装饰器已提取 (Phase 4)',
        }

    # ========================================================================
    # Import 覆盖率
    # ========================================================================

    def check_import_coverage(self, project_path: str) -> Dict:
        """检查 import 语句是否全部提取"""
        source_import_count = 0
        import_re = re.compile(
            r"import\s+(?:\{[^}]+\}|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )

        for ext in ['*.ets', '*.ts']:
            for f in Path(project_path).rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        source_import_count += len(import_re.findall(fh.read()))
                except Exception:
                    pass

        db_import_count = 0
        if self.conn:
            try:
                rows = self.conn.execute(
                    "SELECT COUNT(*) FROM imports"
                ).fetchall()
                db_import_count = rows[0][0]
            except sqlite3.OperationalError:
                pass

        coverage = db_import_count / max(source_import_count, 1) * 100

        return {
            'label': 'Import覆盖率',
            'source_count': source_import_count,
            'db_count': db_import_count,
            'matched': min(db_import_count, source_import_count),
            'coverage': round(coverage, 1),
            'missing': [],
            'status': 'N/A' if source_import_count == 0 else ('PASS' if coverage >= 95 else 'WARN' if coverage >= 80 else 'FAIL'),
            'note': 'Import已提取 (Phase 5)',
        }

    # ========================================================================
    # 关系完整性
    # ========================================================================

    def check_relation_integrity(self) -> Dict:
        """检查关系引用完整性（外键有效性）"""
        issues = []

        if not self.conn:
            return {'label': '关系完整性', 'is_valid': False, 'issues': ['数据库未连接'], 'status': 'FAIL'}

        # calls 表中 callee_class 应该存在于 classes 表
        try:
            rows = self.conn.execute("""
                SELECT DISTINCT callee_class FROM calls
                WHERE callee_class != ''
                AND callee_class NOT IN (SELECT name FROM classes)
            """).fetchall()
            if rows:
                names = [r[0] for r in rows[:10]]
                issues.append(f"calls中引用了{len(rows)}个不存在的类: {names}")
        except sqlite3.OperationalError:
            pass

        # inherits 表中 parent_class 应该存在
        try:
            rows = self.conn.execute("""
                SELECT DISTINCT parent_class FROM inherits
                WHERE parent_class NOT IN (SELECT name FROM classes)
            """).fetchall()
            if rows:
                names = [r[0] for r in rows[:10]]
                issues.append(f"inherits中引用了{len(rows)}个不存在的父类: {names}")
        except sqlite3.OperationalError:
            pass

        # components 表中 parent/child 应该存在于 classes 表
        try:
            rows = self.conn.execute("""
                SELECT DISTINCT parent FROM components
                WHERE parent NOT IN (SELECT name FROM classes)
            """).fetchall()
            if rows:
                names = [r[0] for r in rows[:10]]
                issues.append(f"components中引用了{len(rows)}个不存在的父组件: {names}")
        except sqlite3.OperationalError:
            pass

        return {
            'label': '关系完整性',
            'is_valid': len(issues) == 0,
            'issues': issues,
            'status': 'PASS' if len(issues) == 0 else 'FAIL',
        }

    # ========================================================================
    # 孤立节点检测
    # ========================================================================

    def check_orphan_nodes(self) -> Dict:
        """检测没有被任何关系引用的类"""
        if not self.conn:
            return {'label': '孤立节点', 'orphan_count': 0, 'orphans': [], 'status': 'N/A'}

        try:
            rows = self.conn.execute("""
                SELECT c.name, c.file FROM classes c
                WHERE c.name NOT IN (
                    SELECT DISTINCT caller_class FROM calls
                    UNION
                    SELECT DISTINCT callee_class FROM calls WHERE callee_class != ''
                    UNION
                    SELECT DISTINCT parent FROM components
                    UNION
                    SELECT DISTINCT child FROM components
                    UNION
                    SELECT DISTINCT child_class FROM inherits
                    UNION
                    SELECT DISTINCT parent_class FROM inherits
                )
            """).fetchall()

            orphans = [f"{r[0]} ({Path(r[1]).name})" for r in rows]
        except sqlite3.OperationalError:
            orphans = []

        return {
            'label': '孤立节点',
            'orphan_count': len(orphans),
            'orphans': sorted(orphans)[:20],
            'status': 'INFO',
        }

    # ========================================================================
    # 综合验证
    # ========================================================================

    def validate_all(self, project_path: str) -> Dict:
        """运行全部验证"""
        report = {
            'project_path': str(project_path),
            'checks': [],
            'summary': {'pass': 0, 'warn': 0, 'fail': 0, 'na': 0},
        }

        checks = [
            ('file_coverage', lambda: self.check_file_coverage(project_path)),
            ('class_coverage', lambda: self.check_class_coverage(project_path)),
            ('method_coverage', lambda: self.check_method_coverage(project_path)),
            ('decorator_coverage', lambda: self.check_decorator_coverage(project_path)),
            ('import_coverage', lambda: self.check_import_coverage(project_path)),
            ('relation_integrity', lambda: self.check_relation_integrity()),
            ('orphan_nodes', lambda: self.check_orphan_nodes()),
        ]

        for name, fn in checks:
            try:
                result = fn()
                result['name'] = name
                report['checks'].append(result)
                status = result.get('status', 'N/A')
                if status == 'PASS':
                    report['summary']['pass'] += 1
                elif status == 'WARN':
                    report['summary']['warn'] += 1
                elif status == 'FAIL':
                    report['summary']['fail'] += 1
                else:
                    report['summary']['na'] += 1
            except Exception as e:
                report['checks'].append({
                    'name': name,
                    'status': 'ERROR',
                    'error': str(e),
                })
                report['summary']['fail'] += 1

        return report

    # ========================================================================
    # 打印报告
    # ========================================================================

    def print_report(self, report: Dict):
        """打印验证报告"""
        print("\n" + "=" * 70)
        print(f"  知识图谱覆盖率验证报告")
        print(f"  项目: {report['project_path']}")
        print("=" * 70)

        for check in report['checks']:
            status = check.get('status', 'N/A')
            icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌', 'N/A': '⬜', 'INFO': 'ℹ️', 'ERROR': '💥'}.get(status, '?')
            label = check.get('label', check.get('name', ''))

            print(f"\n{icon} {label}: ", end='')

            if 'coverage' in check:
                cov = check['coverage']
                print(f"{cov}%  (源码: {check['source_count']}, 图谱: {check['db_count']}, 匹配: {check['matched']})")
                if check.get('missing'):
                    for m in check['missing'][:5]:
                        print(f"   缺失: {m}")
                    if len(check['missing']) > 5:
                        print(f"   ... 还有 {len(check['missing']) - 5} 项")
                if check.get('note'):
                    print(f"   📝 {check['note']}")
            elif 'is_valid' in check:
                print('通过' if check['is_valid'] else '有问题')
                for issue in check.get('issues', []):
                    print(f"   ⚠ {issue}")
            elif 'orphan_count' in check:
                print(f"{check['orphan_count']} 个孤立类")
                for o in check.get('orphans', [])[:5]:
                    print(f"   孤立: {o}")
            elif 'error' in check:
                print(f"错误: {check['error']}")

        # 摘要
        s = report['summary']
        total = s['pass'] + s['warn'] + s['fail'] + s['na']
        print("\n" + "-" * 70)
        print(f"  摘要: ✅ {s['pass']} 通过 | ⚠️ {s['warn']} 警告 | ❌ {s['fail']} 失败 | ⬜ {s['na']} 待实现")
        print(f"  总计: {total} 项检查")
        print("=" * 70)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    @staticmethod
    def _is_excluded(file_path: str) -> bool:
        """排除非业务文件"""
        excluded = {'node_modules', 'oh_modules', '.git', '.ohos', 'build', 'dist', '.preview'}
        parts = Path(file_path).parts
        return any(p.lower() in excluded for p in parts)

    @staticmethod
    def _extract_brace_block(content: str, open_pos: int) -> Optional[str]:
        """提取花括号内的内容"""
        if open_pos >= len(content) or content[open_pos] != '{':
            return None
        depth = 0
        for i in range(open_pos, len(content)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    return content[open_pos:i + 1]
        return None

    @staticmethod
    def _scan_methods_in_body(body: str) -> Set[str]:
        """在类体中扫描方法名（简化版，只做顶层匹配）"""
        methods = set()
        # 匹配方法定义: [modifiers] name(
        method_re = re.compile(
            r'^[ \t]*(?:private\s+|public\s+|protected\s+)?'
            r'(?:static\s+)?(?:async\s+)?(?:abstract\s+|override\s+)?'
            r'(\w+)\s*(?:<[^>]*>\s*)?\(',
            re.MULTILINE
        )

        skip = {
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'return',
            'constructor', 'super', 'new', 'typeof', 'instanceof',
            'Text', 'Row', 'Column', 'List', 'Image', 'Button', 'Stack',
            'Scroll', 'Grid', 'Tabs', 'ForEach', 'LazyForEach',
            'fontSize', 'fontWeight', 'width', 'height', 'margin', 'padding',
            'onClick', 'onChange', 'onAppear', 'onDisappear',
        }

        # 计算花括号深度
        depth_at = {}
        depth = 0
        for i, ch in enumerate(body):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            depth_at[i] = depth

        for m in method_re.finditer(body):
            name = m.group(1)
            if name in skip:
                continue
            # 只取顶层方法（深度=1）
            if depth_at.get(m.start(), 0) == 1:
                methods.add(name)

        return methods
