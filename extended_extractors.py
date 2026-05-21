#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展提取器 - Phase 4 & 5
装饰器、接口、枚举、类型别名、import依赖、状态管理关系提取
"""

import re
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class InterfaceInfo:
    name: str
    file: str
    methods: str = ""  # JSON list
    line_number: int = 0

@dataclass
class EnumInfo:
    name: str
    file: str
    values: str = ""  # JSON list
    line_number: int = 0

@dataclass
class TypeAliasInfo:
    name: str
    file: str
    target_type: str = ""
    line_number: int = 0

@dataclass
class DecoratorInfo:
    name: str          # "@State", "@Provide"
    dec_type: str      # "state", "provide", "component_def" ...
    target_type: str   # "class", "method", "property"
    target_name: str   # 被装饰的实体名
    target_class: str  # 所属类名
    argument: str      # @Watch('onChange') 的参数
    file: str
    line_number: int = 0

@dataclass
class ImportInfo:
    source_file: str
    imported_names: str  # JSON list
    module_path: str
    is_relative: int = 0

@dataclass
class StateRelationInfo:
    relation_type: str   # "prop", "link", "provide", "consume", "watch", ...
    source_class: str
    source_property: str
    property_type: str
    key: str
    file: str
    line_number: int = 0


# ============================================================================
# ArkTS 装饰器完整定义
# ============================================================================

ARKTS_DECORATORS = {
    # 组件定义
    'Component': 'component_def',
    'Entry': 'entry_def',
    'CustomDialog': 'dialog_def',
    'Reusable': 'reusable_def',
    # 状态管理
    'State': 'state',
    'Prop': 'prop',
    'Link': 'link',
    'Provide': 'provide',
    'Consume': 'consume',
    'StorageLink': 'storage_link',
    'StorageProp': 'storage_prop',
    'LocalStorageLink': 'local_storage_link',
    'LocalStorageProp': 'local_storage_prop',
    'Observed': 'observed',
    'ObjectLink': 'object_link',
    # 监听
    'Watch': 'watch',
    # UI构建
    'Builder': 'builder',
    'Styles': 'styles',
    'Extend': 'extend',
    # 其他
    'Inject': 'inject',
    'Volatile': 'volatile',
}

# 状态管理装饰器（携带数据流语义）
STATE_DECORATORS = {'Prop', 'Link', 'Provide', 'Consume', 'StorageLink',
                     'StorageProp', 'LocalStorageLink', 'LocalStorageProp', 'ObjectLink'}


# ============================================================================
# 装饰器提取器
# ============================================================================

class DecoratorExtractor:
    """装饰器完整提取器"""

    # 匹配 @Name 或 @Name('arg') 或 @Name(VarName)
    DECORATOR_RE = re.compile(
        r'@(\w+)\s*(?:\(\s*(?:[\'"]([^\'")\s]*)[\'"]|(\w+))\s*\))?'
    )

    def extract_from_file(self, stripped: str, content: str, file_path: str) -> List[DecoratorInfo]:
        """提取文件中所有 ArkTS 装饰器"""
        results = []
        for match in self.DECORATOR_RE.finditer(stripped):
            dec_name = match.group(1)
            dec_arg = match.group(2) or match.group(3) or ""
            line_number = content[:match.start()].count('\n') + 1

            if dec_name in ARKTS_DECORATORS:
                results.append(DecoratorInfo(
                    name=f'@{dec_name}',
                    dec_type=ARKTS_DECORATORS[dec_name],
                    target_type='',      # 由调用方填充
                    target_name='',      # 由调用方填充
                    target_class='',     # 由调用方填充
                    argument=dec_arg,
                    file=file_path,
                    line_number=line_number,
                ))
        return results

    def extract_from_class(self, stripped_body: str, class_name: str,
                            file_path: str, class_line: int) -> List[DecoratorInfo]:
        """提取类体中的装饰器（绑定到方法和属性）"""
        results = []
        # 找到每个装饰器及其后面的方法/属性定义
        # 策略: 找装饰器，然后找紧跟其后的方法名或属性名

        for match in self.DECORATOR_RE.finditer(stripped_body):
            dec_name = match.group(1)
            if dec_name not in ARKTS_DECORATORS:
                continue

            dec_arg = match.group(2) or match.group(3) or ""
            dec_line = class_line + stripped_body[:match.start()].count('\n')

            # 向后查找被装饰的目标（方法或属性）
            after = stripped_body[match.end():]
            target_match = re.match(
                r'\s*(?:private\s+|public\s+|protected\s+)?(?:static\s+)?(?:async\s+)?'
                r'(?:abstract\s+|override\s+)?'
                r'(?:get\s+|set\s+)?'
                r'(\w+)',
                after
            )
            target_name = target_match.group(1) if target_match else ""

            # 判断目标类型
            target_type = 'property'
            if target_name in ('get', 'set'):
                target_type = 'accessor'
            elif re.match(r'\s*(?:private\s+|public\s+|protected\s+)?(?:static\s+)?(?:async\s+)?\w+\s*\(', after):
                target_type = 'method'

            results.append(DecoratorInfo(
                name=f'@{dec_name}',
                dec_type=ARKTS_DECORATORS[dec_name],
                target_type=target_type,
                target_name=target_name,
                target_class=class_name,
                argument=dec_arg,
                file=file_path,
                line_number=dec_line,
            ))

        return results


# ============================================================================
# 接口/枚举/类型别名提取器
# ============================================================================

class EntityTypeExtractor:
    """接口、枚举、类型别名提取器"""

    # 接口正则
    INTERFACE_RE = re.compile(
        r'(?:export\s+)?(?:default\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{',
        re.MULTILINE
    )

    # 枚举正则
    ENUM_RE = re.compile(
        r'(?:export\s+)?(?:default\s+)?enum\s+(\w+)\s*\{([^}]*)\}',
        re.MULTILINE
    )

    # 类型别名正则
    TYPE_ALIAS_RE = re.compile(
        r'(?:export\s+)?(?:default\s+)?type\s+(\w+)\s*(?:<[^>]*>)?\s*=\s*([^;]+);',
        re.MULTILINE
    )

    def extract_interfaces(self, stripped: str, content: str, file_path: str) -> List[InterfaceInfo]:
        results = []
        for match in self.INTERFACE_RE.finditer(stripped):
            name = match.group(1)
            extends_str = match.group(2) or ""
            line = content[:match.start()].count('\n') + 1

            # 提取接口中的方法签名
            body = stripped[match.start():]
            brace_start = body.index('{')
            body_text = self._extract_brace_block(body, brace_start)
            methods = re.findall(r'(\w+)\s*\(', body_text) if body_text else []

            results.append(InterfaceInfo(
                name=name, file=file_path,
                methods=json.dumps(methods),
                line_number=line,
            ))
        return results

    def extract_enums(self, stripped: str, content: str, file_path: str) -> List[EnumInfo]:
        results = []
        for match in self.ENUM_RE.finditer(stripped):
            name = match.group(1)
            body = match.group(2)
            line = content[:match.start()].count('\n') + 1

            # 提取枚举值
            values = re.findall(r'(\w+)', body)
            # 过滤掉关键字
            values = [v for v in values if v not in ('export', 'default', 'const')]

            results.append(EnumInfo(
                name=name, file=file_path,
                values=json.dumps(values),
                line_number=line,
            ))
        return results

    def extract_type_aliases(self, stripped: str, content: str, file_path: str) -> List[TypeAliasInfo]:
        results = []
        for match in self.TYPE_ALIAS_RE.finditer(stripped):
            name = match.group(1)
            target = match.group(2).strip()
            line = content[:match.start()].count('\n') + 1

            results.append(TypeAliasInfo(
                name=name, file=file_path,
                target_type=target,
                line_number=line,
            ))
        return results

    @staticmethod
    def _extract_brace_block(text: str, open_pos: int) -> Optional[str]:
        if open_pos >= len(text) or text[open_pos] != '{':
            return None
        depth = 0
        for i in range(open_pos, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[open_pos:i + 1]
        return None


# ============================================================================
# Import 依赖提取器
# ============================================================================

class ImportExtractor:
    """Import 依赖图提取器"""

    IMPORT_RE = re.compile(
        r"import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
        re.MULTILINE
    )

    def extract(self, content: str, file_path: str) -> List[ImportInfo]:
        results = []
        for match in self.IMPORT_RE.finditer(content):
            named = match.group(1)       # "{ A, B, C }"
            default = match.group(2)     # default import
            module = match.group(3)      # "../service/UserService"

            names = []
            if named:
                names = [n.strip() for n in named.split(',')]
            if default:
                names.append(default)

            is_relative = int(module.startswith('.') or module.startswith('/'))

            results.append(ImportInfo(
                source_file=file_path,
                imported_names=json.dumps(names),
                module_path=module,
                is_relative=is_relative,
            ))
        return results


# ============================================================================
# 状态管理关系提取器
# ============================================================================

class StateRelationExtractor:
    """提取 @Prop/@Link/@Provide/@Consume 等数据流关系"""

    # 匹配: @Prop title: string  或  @Link('key') isVisible: boolean
    STATE_DECORATOR_RE = re.compile(
        r'@(Prop|Link|Provide|Consume|StorageLink|StorageProp|ObjectLink)'
        r'\s*(?:\(\s*[\'"]?([^\'")\s]*)[\'"]?\s*\))?\s+'
        r'(\w+)\s*:\s*([^=;\n]+)'
    )

    def extract_from_class(self, stripped_body: str, class_name: str,
                            file_path: str, class_line: int) -> List[StateRelationInfo]:
        results = []
        for match in self.STATE_DECORATOR_RE.finditer(stripped_body):
            dec_type = match.group(1).lower()
            key = match.group(2) or ""
            prop_name = match.group(3)
            prop_type = match.group(4).strip()
            line = class_line + stripped_body[:match.start()].count('\n')

            results.append(StateRelationInfo(
                relation_type=dec_type,
                source_class=class_name,
                source_property=prop_name,
                property_type=prop_type,
                key=key,
                file=file_path,
                line_number=line,
            ))
        return results
