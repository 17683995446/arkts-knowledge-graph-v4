#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能过滤器 - Phase 2
四层递进式第三方库过滤器 + 依赖图分析器
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple


# ============================================================================
# 第一层: 路径黑名单
# ============================================================================

class ThirdPartyFilter:
    """第三方库路径过滤器"""

    EXCLUDE_DIRS = frozenset({
        # 包管理器
        'node_modules', 'oh_modules', '.ohos',
        # 构建产物
        'build', 'dist', 'output', '.preview', 'intermediates',
        'gen', 'generated', 'auto_generated', '.cxx',
        # 版本控制 / IDE
        '.git', '.svn', '.hg', '.idea', '.vscode',
        # 第三方库常见目录
        'libs', 'lib', 'third_party', 'vendor', 'external',
        # 测试 / 覆盖率
        'coverage', '.nyc_output', '__mocks__',
        # HarmonyOS 特有
        'hap', '.arkui', 'resources-base',
        # 其他
        'docs', 'documentation', '.github',
    })

    EXCLUDE_PATTERNS = [
        re.compile(r'\.min\.(ets|ts|js)$'),
        re.compile(r'\.d\.ts$'),
        re.compile(r'[\\/]gen[\\/]'),
        re.compile(r'[\\/]__test__[\\/]'),
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self._package_json = self._load_json('package.json')
        self._oh_package = self._load_json('oh-package.json5')
        self._exclude_paths: Set[str] = set()
        self._build_exclude_paths()

    def _load_json(self, filename: str) -> Dict:
        for p in [self.project_path / filename]:
            if p.exists():
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        content = f.read().replace(',}', '}').replace(',]', ']')
                        return json.loads(content)
                except Exception:
                    pass
        return {}

    def _build_exclude_paths(self):
        """根据 package.json 的 dependencies 构建排除路径"""
        deps = set()
        for section in ['dependencies', 'devDependencies', 'peerDependencies']:
            deps.update(self._package_json.get(section, {}).keys())
            deps.update(self._oh_package.get(section, {}).keys())

        for dep in deps:
            for base in ['node_modules', 'oh_modules']:
                self._exclude_paths.add(str(self.project_path / base / dep))

    def should_exclude(self, file_path: str) -> bool:
        """判断文件是否应该被排除"""
        path = Path(file_path)
        rel = path.relative_to(self.project_path)
        parts = rel.parts

        # 规则1: 目录名匹配
        for part in parts:
            if part.lower() in self.EXCLUDE_DIRS:
                return True

        # 规则2: 路径匹配排除列表
        path_str = str(file_path)
        for excl in self._exclude_paths:
            if path_str.startswith(excl):
                return True

        # 规则3: 文件模式匹配
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern.search(path_str):
                return True

        return False

    def filter_files(self, all_files: List[str]) -> List[str]:
        """过滤文件列表"""
        result = []
        excluded = 0
        for f in all_files:
            if self.should_exclude(f):
                excluded += 1
            else:
                result.append(f)
        print(f"  第一层(路径黑名单): {len(all_files)} → {len(result)} (排除 {excluded} 个)")
        return result


# ============================================================================
# 第二层: 依赖图分析
# ============================================================================

class DependencyAnalyzer:
    """基于 import 语句的依赖图分析器"""

    SYSTEM_IMPORT_PREFIXES = (
        '@ohos/', '@kit.', '@system.', '@app.', '@hms.',
        '@arkui.', '@core.', '@base.',
    )

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.import_sources: Dict[str, str] = {}  # module -> 'business'|'third_party'|'system'|'unknown'
        self.file_exports: Dict[str, Set[str]] = {}

    def build_dependency_graph(self, business_files: List[str]):
        """构建完整的依赖图"""
        # 扫描所有业务文件的 import 和 export
        for fpath in business_files:
            self._scan_imports_exports(fpath)

        # 标记系统模块
        for mod_name in self.import_sources:
            if mod_name.startswith(self.SYSTEM_IMPORT_PREFIXES):
                self.import_sources[mod_name] = 'system'

        # 标记 oh_modules / node_modules 中的模块
        for mod_name in list(self.import_sources.keys()):
            if self.import_sources[mod_name] == 'unknown':
                for base in ['oh_modules', 'node_modules']:
                    mod_path = self.project_path / base / mod_name
                    if mod_path.exists():
                        self.import_sources[mod_name] = 'third_party'
                        break

        # 剩余 unknown 且不在业务文件 export 中的
        business_exports = set()
        for exports in self.file_exports.values():
            business_exports.update(exports)

        for mod_name, source_type in list(self.import_sources.items()):
            if source_type == 'unknown' and mod_name not in business_exports:
                self.import_sources[mod_name] = 'third_party'

    def _scan_imports_exports(self, file_path: str):
        """扫描单个文件的 import 和 export"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return

        exports = set()

        # import { Xxx } from 'module' 或 import Xxx from 'module'
        for m in re.finditer(
            r"import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
            content
        ):
            source = m.group(3)
            if source not in self.import_sources:
                self.import_sources[source] = 'unknown'

        # export class/struct/function/interface/enum/type Xxx
        for m in re.finditer(
            r"export\s+(?:default\s+)?(?:class|struct|function|interface|enum|type)\s+(\w+)",
            content
        ):
            exports.add(m.group(1))

        # export { A, B, C }
        for m in re.finditer(r"export\s*\{([^}]+)\}", content):
            for name in m.group(1).split(','):
                name = name.strip()
                if name:
                    exports.add(name)

        self.file_exports[file_path] = exports

    def get_third_party_modules(self) -> Set[str]:
        return {k for k, v in self.import_sources.items() if v == 'third_party'}

    def get_system_modules(self) -> Set[str]:
        return {k for k, v in self.import_sources.items() if v == 'system'}

    def get_summary(self) -> Dict[str, int]:
        summary = {'business': 0, 'third_party': 0, 'system': 0, 'unknown': 0}
        for v in self.import_sources.values():
            summary[v] = summary.get(v, 0) + 1
        return summary


# ============================================================================
# 第三层: 目录白名单
# ============================================================================

class SourceDirectoryConfig:
    """业务源码目录白名单配置"""

    DEFAULT_SOURCE_PATTERNS = [
        'entry/src/main/ets',
        'features/*/src/main/ets',
        'modules/*/src/main/ets',
        'commons/*/src/main/ets',
    ]

    @classmethod
    def resolve(cls, project_path: str,
                custom_dirs: List[str] = None) -> List[Path]:
        """解析出所有业务源码目录"""
        project = Path(project_path).resolve()
        dirs = custom_dirs or cls.DEFAULT_SOURCE_PATTERNS

        result = []
        for pattern in dirs:
            matched = list(project.glob(pattern))
            if not matched:
                p = project / pattern
                if p.exists():
                    matched = [p]
            result.extend(matched)

        return sorted(set(d for d in result if d.is_dir()))


# ============================================================================
# 第四层: 内容指纹检测
# ============================================================================

class ContentFingerprintDetector:
    """基于文件内容的第三方代码检测"""

    THIRD_PARTY_PATTERNS = [
        re.compile(r'@license\s+MIT', re.IGNORECASE),
        re.compile(r'Copyright\s+\(c\)\s+\d{4}\s+[\w\s]+(?:Inc\.|Corp\.|Foundation|Ltd\.)', re.IGNORECASE),
        re.compile(r'spun\s+up\s+from|generated\s+by|auto-generated', re.IGNORECASE),
    ]

    BUSINESS_PATTERNS = [
        re.compile(r'@Entry|@Component|@CustomDialog|@Reusable'),
        re.compile(r"import\s+.*from\s+['\"]\.\.?/"),
    ]

    @classmethod
    def is_likely_third_party(cls, file_path: str) -> Optional[bool]:
        """返回: True=第三方, False=业务代码, None=无法判断"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                header = ''.join(f.readline() for _ in range(50))
        except Exception:
            return None

        tp_score = sum(1 for p in cls.THIRD_PARTY_PATTERNS if p.search(header))
        biz_score = sum(1 for p in cls.BUSINESS_PATTERNS if p.search(header))

        if tp_score > 0 and biz_score == 0:
            return True
        if biz_score > 0:
            return False
        return None


# ============================================================================
# 整合: 四层协同
# ============================================================================

class SmartFilter:
    """四层递进式智能过滤器"""

    def __init__(self, project_path: str,
                 source_dirs: List[str] = None,
                 use_allowlist: bool = False):
        self.project_path = Path(project_path).resolve()
        self.use_allowlist = use_allowlist
        self.source_dirs = source_dirs

        self.path_filter = ThirdPartyFilter(str(project_path))
        self.dep_analyzer = DependencyAnalyzer(str(project_path))
        self.content_detector = ContentFingerprintDetector

        self._stats = {
            'layer1_path': 0, 'layer2_import': 0,
            'layer3_allowlist': 0, 'layer4_content': 0,
            'kept': 0,
        }

    def filter(self) -> List[str]:
        """执行四层过滤"""
        all_files = self._collect_all_files()
        print(f"  原始文件数: {len(all_files)}")

        # === 第一层: 路径黑名单 ===
        after_l1 = self.path_filter.filter_files(all_files)
        self._stats['layer1_path'] = len(all_files) - len(after_l1)

        # === 第二层: 依赖图分析 ===
        self.dep_analyzer.build_dependency_graph(after_l1)
        third_party_modules = self.dep_analyzer.get_third_party_modules()

        after_l2 = []
        for f in after_l1:
            if self._is_third_party_barrel(f, third_party_modules):
                self._stats['layer2_import'] += 1
            else:
                after_l2.append(f)
        if self._stats['layer2_import'] > 0:
            print(f"  第二层(依赖图): 排除 {self._stats['layer2_import']} 个")

        # === 第三层: 目录白名单（可选）===
        if self.use_allowlist:
            allowed_dirs = SourceDirectoryConfig.resolve(
                str(self.project_path), self.source_dirs)
            allowed_prefixes = [str(d) for d in allowed_dirs]
            after_l3 = [f for f in after_l2
                        if any(f.startswith(p) for p in allowed_prefixes)]
            self._stats['layer3_allowlist'] = len(after_l2) - len(after_l3)
            if self._stats['layer3_allowlist'] > 0:
                print(f"  第三层(白名单): 排除 {self._stats['layer3_allowlist']} 个")
            after_l2 = after_l3

        # === 第四层: 内容指纹 ===
        after_l4 = []
        for f in after_l2:
            result = self.content_detector.is_likely_third_party(f)
            if result is True:
                self._stats['layer4_content'] += 1
            else:
                after_l4.append(f)
        if self._stats['layer4_content'] > 0:
            print(f"  第四层(内容指纹): 排除 {self._stats['layer4_content']} 个")

        self._stats['kept'] = len(after_l4)

        # 打印依赖分析摘要
        dep_summary = self.dep_analyzer.get_summary()
        print(f"  依赖分析: 业务={dep_summary.get('business', 0)}, "
              f"第三方={dep_summary.get('third_party', 0)}, "
              f"系统={dep_summary.get('system', 0)}, "
              f"未知={dep_summary.get('unknown', 0)}")
        print(f"  最终保留: {self._stats['kept']} 个业务文件")

        return after_l4

    def _is_third_party_barrel(self, file_path: str,
                                third_party_modules: Set[str]) -> bool:
        """判断文件是否只 re-export 第三方模块"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return False

        for m in re.finditer(
            r"import\s+.+?\s+from\s+['\"]([^'\"]+)['\"]", content
        ):
            source = m.group(1)
            if source.startswith('./') or source.startswith('../'):
                return False  # 有相对import → 业务文件
            if source in third_party_modules:
                return True  # 只import第三方 → 排除
        return False

    def _collect_all_files(self) -> List[str]:
        """收集所有 .ets 和 .ts 文件"""
        files = []
        for ext in ['*.ets', '*.ts']:
            files.extend(str(f) for f in self.project_path.rglob(ext))
        return files

    def get_stats(self) -> Dict:
        return self._stats
