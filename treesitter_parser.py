#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tree-sitter 解析器 - Phase 6
基于 tree-sitter 的精准 AST 解析，替代正则匹配
"""

import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

# tree-sitter 导入（可选依赖）
TREE_SITTER_AVAILABLE = False
Parser = None
get_parser = None

try:
    from tree_sitter_languages import get_parser as _get_parser
    get_parser = _get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    pass

if not TREE_SITTER_AVAILABLE:
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser as _Parser
        Parser = _Parser
        TREE_SITTER_AVAILABLE = True
    except ImportError:
        pass


@dataclass
class ASTNode:
    """AST 节点简化表示"""
    type: str
    text: str
    start_byte: int
    end_byte: int
    start_point: Tuple[int, int]  # (row, col)
    end_point: Tuple[int, int]
    children: List['ASTNode']


class TreeSitterArkTSParser:
    """基于 tree-sitter 的 ArkTS 解析器
    
    使用 TypeScript 语法作为 ArkTS 的近似（ArkTS 是 TypeScript 超集）
    """

    def __init__(self):
        self.parser = None
        self.ts_language = None
        self._init_parser()

    def _init_parser(self):
        """初始化 tree-sitter 解析器"""
        if not TREE_SITTER_AVAILABLE:
            return

        try:
            if get_parser is not None:
                # 使用 tree-sitter-languages 的 get_parser
                # 尝试 TypeScript（ArkTS 是 TS 超集），回退到 Python
                try:
                    self.parser = get_parser('typescript')
                except Exception:
                    self.parser = get_parser('python')
            elif Parser is not None:
                # 使用 tree-sitter-python
                import tree_sitter_python as tspython
                from tree_sitter import Language
                self.parser = Parser()
                self.ts_language = Language(tspython.language())
                self.parser.set_language(self.ts_language)
        except Exception as e:
            print(f"tree-sitter 初始化失败: {e}")
            self.parser = None

    def is_available(self) -> bool:
        """检查 tree-sitter 是否可用"""
        return self.parser is not None

    def parse(self, content: str) -> Optional[Any]:
        """解析源码，返回 AST"""
        if not self.parser:
            return None

        try:
            tree = self.parser.parse(bytes(content, 'utf8'))
            return tree
        except Exception:
            return None

    def extract_classes(self, tree, source: bytes) -> List[Dict]:
        """从 AST 提取类定义"""
        if not tree:
            return []

        classes = []

        def walk(node, depth=0):
            # TypeScript: class_declaration
            # Python: class_definition
            if node.type in ('class_declaration', 'class_definition'):
                class_info = self._extract_class_info(node, source)
                if class_info:
                    classes.append(class_info)

            for child in node.children:
                walk(child, depth + 1)

        walk(tree.root_node)
        return classes

    def _extract_class_info(self, node, source: bytes) -> Optional[Dict]:
        """提取单个类的信息"""
        name = None
        bases = []
        methods = []

        for child in node.children:
            # TypeScript: type_identifier
            # Python: identifier
            if child.type in ('type_identifier', 'identifier'):
                name = source[child.start_byte:child.end_byte].decode('utf8')
            # TypeScript: class_heritage (extends/implements)
            elif child.type == 'class_heritage':
                for hc in child.children:
                    if hc.type in ('type_identifier', 'identifier'):
                        bases.append(source[hc.start_byte:hc.end_byte].decode('utf8'))
            # Python: argument_list (base classes)
            elif child.type == 'argument_list':
                for arg in child.children:
                    if arg.type == 'identifier':
                        bases.append(source[arg.start_byte:arg.end_byte].decode('utf8'))
            # TypeScript: class_body
            elif child.type == 'class_body':
                for bc in child.children:
                    # TypeScript: method_definition
                    if bc.type == 'method_definition':
                        for mc in bc.children:
                            if mc.type in ('property_identifier', 'identifier'):
                                methods.append(source[mc.start_byte:mc.end_byte].decode('utf8'))
                                break
            # Python: function_definition (methods)
            elif child.type == 'function_definition':
                method_name = None
                for mc in child.children:
                    if mc.type == 'identifier':
                        method_name = source[mc.start_byte:mc.end_byte].decode('utf8')
                        break
                if method_name:
                    methods.append(method_name)

        if name:
            return {
                'name': name,
                'bases': bases,
                'methods': methods,
                'start_point': node.start_point,
                'end_point': node.end_point,
            }
        return None

    def extract_functions(self, tree, source: bytes) -> List[Dict]:
        """从 AST 提取函数定义"""
        if not tree:
            return []

        functions = []

        def walk(node):
            if node.type == 'function_definition':
                name = None
                params = []
                for child in node.children:
                    if child.type == 'identifier':
                        name = source[child.start_byte:child.end_byte].decode('utf8')
                    elif child.type == 'parameters':
                        for param in child.children:
                            if param.type == 'identifier':
                                params.append(source[param.start_byte:param.end_byte].decode('utf8'))

                if name:
                    functions.append({
                        'name': name,
                        'params': params,
                        'start_point': node.start_point,
                    })

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return functions

    def extract_imports(self, tree, source: bytes) -> List[Dict]:
        """从 AST 提取 import 语句"""
        if not tree:
            return []

        imports = []

        def walk(node):
            if node.type == 'import_statement':
                # import X from 'module'
                module = None
                names = []

                for child in node.children:
                    if child.type == 'string':
                        # 去掉引号
                        module = source[child.start_byte:child.end_byte].decode('utf8').strip('\'"')
                    elif child.type == 'dotted_name' or child.type == 'identifier':
                        names.append(source[child.start_byte:child.end_byte].decode('utf8'))
                    elif child.type == 'import_from_statement':
                        # from X import Y
                        for sub in child.children:
                            if sub.type == 'dotted_name':
                                module = source[sub.start_byte:sub.end_byte].decode('utf8')

                if module:
                    imports.append({
                        'module': module,
                        'names': names,
                    })

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return imports

    def build_scope_tree(self, tree) -> Dict[int, Dict]:
        """构建作用域树"""
        if not tree:
            return {}

        scopes = {}

        def walk(node, parent_scope=None):
            scope_id = id(node)
            scopes[scope_id] = {
                'node': node,
                'parent': parent_scope,
                'variables': {},  # name -> type
                'children': [],
            }

            # 判断是否创建新作用域
            creates_scope = node.type in (
                'class_definition', 'function_definition',
                'block', 'for_statement', 'with_statement',
                'try_statement', 'except_clause',
            )

            current_scope = scope_id if creates_scope else parent_scope

            for child in node.children:
                child_scope = walk(child, current_scope)
                if creates_scope:
                    scopes[scope_id]['children'].append(child_scope)

            return scope_id

        walk(tree.root_node)
        return scopes

    def resolve_name_in_scope(self, scopes: Dict, scope_id: int, name: str) -> Optional[str]:
        """在作用域链中查找名称定义"""
        current = scope_id
        while current:
            scope = scopes.get(current)
            if not scope:
                break
            if name in scope['variables']:
                return scope['variables'][name]
            current = scope.get('parent')
        return None

    def to_ast_node(self, node, source: bytes) -> ASTNode:
        """将 tree-sitter 节点转换为简化 ASTNode"""
        return ASTNode(
            type=node.type,
            text=source[node.start_byte:node.end_byte].decode('utf8'),
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            start_point=node.start_point,
            end_point=node.end_point,
            children=[self.to_ast_node(c, source) for c in node.children],
        )


# ============================================================================
# 双模式解析器工厂
# ============================================================================

class ParserFactory:
    """解析器工厂：根据可用性选择 tree-sitter 或正则"""

    @staticmethod
    def get_parser():
        """获取最佳可用解析器"""
        ts_parser = TreeSitterArkTSParser()
        if ts_parser.is_available():
            return ('tree-sitter', ts_parser)
        else:
            return ('regex', None)  # 正则解析器已内置在 ArkTSParser 中

    @staticmethod
    def compare_results(content: str, regex_result: Dict) -> Dict:
        """对比 tree-sitter 和正则解析结果（调试用）"""
        ts_parser = TreeSitterArkTSParser()
        if not ts_parser.is_available():
            return {'error': 'tree-sitter 不可用'}

        tree = ts_parser.parse(content)
        if not tree:
            return {'error': '解析失败'}

        source = bytes(content, 'utf8')
        ts_classes = ts_parser.extract_classes(tree, source)

        return {
            'tree_sitter': {
                'classes': len(ts_classes),
                'class_names': [c['name'] for c in ts_classes],
            },
            'regex': {
                'classes': len(regex_result.get('classes', [])),
                'class_names': [c.name for c in regex_result.get('classes', [])],
            },
        }
