#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS->SQLite 代码知识图谱系统 (Fixed Version)
基于第一性原理设计：将代码视为实体-关系系统，实现极简、高效、零成本的代码知识图谱

版本: v4.2 (Fixed)
修复内容:
1. 外键约束问题 - 自动插入文件记录
2. 箭头函数解析增强 - 支持更多格式
3. 内置标识符过滤增强
4. 新增循环依赖检测 (CircularDependencyDetector)
5. 新增错误恢复机制 (@error_recovery装饰器)
6. 性能优化 - 批量插入、缓存正则表达式

核心设计原则：
1. 确定性原则：所有实体和关系通过静态分析100%确定
2. 最小化原则：只存储必要的结构信息
3. 零依赖原则：尽可能少地依赖外部服务
4. 可验证原则：所有数据可追溯到源代码位置
5. 零成本原则：使用免费工具和服务
"""

import os
import re
import sqlite3
import json
import logging
import functools
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Callable, Any
from collections import defaultdict

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

# ============================================================================
# 日志配置
# ============================================================================

# 全局调试日志
_logger = logging.getLogger('arkts_kg')
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('[%(levelname)s %(funcName)s:%(lineno)d] %(message)s'))
_logger.addHandler(_handler)
_logger.setLevel(logging.WARNING)  # 默认WARNING，通过 --debug 开启DEBUG


def setup_logging(debug: bool = False) -> None:
    """设置日志级别"""
    if debug:
        _logger.setLevel(logging.DEBUG)
        _logger.info("调试日志已开启")
    else:
        _logger.setLevel(logging.WARNING)


# ============================================================================
# 错误恢复装饰器
# ============================================================================

def error_recovery(default_return: Any = None, log_level: int = logging.ERROR):
    """
    错误恢复装饰器
    
    遇到异常时记录错误并返回默认值，不中断整个解析流程
    
    Args:
        default_return: 发生异常时的默认返回值
        log_level: 日志级别
    
    Example:
        @error_recovery(default_return=[])
        def parse_something(content: str) -> List[str]:
            # 解析逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_name = func.__name__
                _logger.log(log_level, f"[错误恢复] 函数 '{func_name}' 执行失败: {str(e)}")
                return default_return
        return wrapper
    return decorator


# ============================================================================
# 循环依赖检测器
# ============================================================================

class CircularDependencyDetector:
    """
    循环依赖检测器
    
    使用DFS算法检测继承关系中的循环依赖
    
    Example:
        detector = CircularDependencyDetector()
        detector.add_edge('A', 'B')  # A extends B
        detector.add_edge('B', 'C')  # B extends C
        detector.add_edge('C', 'A')  # C extends A (循环)
        
        cycles = detector.detect_cycles()
        # 返回: [['A', 'B', 'C', 'A']]
    """
    
    def __init__(self):
        # 邻接表表示的图: {child: [parent1, parent2, ...]}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        # 所有节点
        self.nodes: Set[str] = set()
    
    def add_edge(self, child: str, parent: str) -> None:
        """
        添加继承关系边
        
        Args:
            child: 子类名
            parent: 父类名
        """
        if child and parent and child != parent:
            self.graph[child].append(parent)
            self.nodes.add(child)
            self.nodes.add(parent)
            _logger.debug(f"[循环依赖检测] 添加边: {child} -> {parent}")
    
    def add_edges_from_relations(self, inherits: List[Any]) -> None:
        """
        从继承关系列表批量添加边
        
        Args:
            inherits: 继承关系对象列表，每个对象需有 child_class 和 parent_class 属性
        """
        for inherit in inherits:
            self.add_edge(inherit.child_class, inherit.parent_class)
    
    def detect_cycles(self) -> List[List[str]]:
        """
        使用DFS检测所有循环依赖
        
        Returns:
            循环路径列表，每个路径是一个类名列表
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # 发现循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    _logger.warning(f"[循环依赖检测] 发现循环: {' -> '.join(cycle)}")
            
            path.pop()
            rec_stack.remove(node)
        
        for node in self.nodes:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def has_cycle(self) -> bool:
        """
        检查是否存在循环依赖
        
        Returns:
            是否存在循环
        """
        return len(self.detect_cycles()) > 0
    
    def get_cycle_report(self) -> str:
        """
        生成循环依赖报告
        
        Returns:
            格式化的报告字符串
        """
        cycles = self.detect_cycles()
        if not cycles:
            return "未发现循环依赖"
        
        report = ["=" * 60, "循环依赖检测报告", "=" * 60]
        report.append(f"\n发现 {len(cycles)} 个循环依赖:\n")
        
        for i, cycle in enumerate(cycles, 1):
            report.append(f"  {i}. {' -> '.join(cycle)}")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report)


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class FileInfo:
    """文件实体"""
    path: str


@dataclass
class ClassInfo:
    """类/组件实体"""
    name: str
    file: str
    is_component: bool = False
    is_entry: bool = False
    line_number: int = 0


@dataclass
class MethodInfo:
    """方法/函数实体"""
    name: str
    class_name: str
    file: str
    line_number: int = 0
    is_static: bool = False
    is_private: bool = False


@dataclass
class CallRelation:
    """函数调用关系"""
    caller: str
    caller_class: str
    callee: str
    callee_class: str
    file: str
    line_number: int = 0


@dataclass
class ComponentRelation:
    """组件嵌套关系"""
    parent: str
    child: str
    file: str
    line_number: int = 0


@dataclass
class InheritRelation:
    """继承关系"""
    child_class: str
    parent_class: str
    file: str
    line_number: int = 0


# ============================================================================
# 数据库管理 (修复版)
# ============================================================================

class DatabaseManager:
    """
    SQLite数据库管理器 (Fixed Version)
    
    修复内容:
    1. 外键约束问题 - insert_class 和 insert_method 自动检查并插入文件记录
    2. 性能优化 - 支持批量插入和事务
    """
    
    def __init__(self, db_path: str = "code.db"):
        self.db_path = db_path
        self.conn = None
        # 缓存已存在的文件，避免重复查询
        self._file_cache: Set[str] = set()
        # 批量插入缓冲区
        self._batch_buffer: Dict[str, List[tuple]] = {
            'files': [],
            'classes': [],
            'methods': [],
            'calls': [],
            'components': [],
            'inherits': []
        }
        self._batch_size: int = 100  # 批量插入阈值
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        # 预加载文件缓存
        self._load_file_cache()
    
    def _load_file_cache(self):
        """加载已有文件到缓存"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT path FROM files")
            self._file_cache = {row[0] for row in cursor.fetchall()}
            _logger.debug(f"[数据库] 已加载 {len(self._file_cache)} 个文件到缓存")
        except sqlite3.OperationalError:
            # 表不存在，缓存为空
            self._file_cache = set()
            _logger.debug("[数据库] 文件表不存在，缓存为空")
    
    def close(self):
        """关闭数据库连接"""
        # 刷新剩余批量数据
        self._flush_all_batches()
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """创建数据库表结构"""
        cursor = self.conn.cursor()
        
        # 实体表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                line_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                name TEXT NOT NULL,
                file TEXT NOT NULL,
                is_component INTEGER DEFAULT 0,
                is_entry INTEGER DEFAULT 0,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (name, file),
                FOREIGN KEY (file) REFERENCES files(path)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS methods (
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                is_static INTEGER DEFAULT 0,
                is_private INTEGER DEFAULT 0,
                PRIMARY KEY (name, class_name, file),
                FOREIGN KEY (file) REFERENCES files(path)
            )
        """)
        
        # 关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                caller TEXT NOT NULL,
                caller_class TEXT NOT NULL,
                callee TEXT NOT NULL,
                callee_class TEXT NOT NULL,
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (caller, caller_class, callee, callee_class, file, line_number)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                parent TEXT NOT NULL,
                child TEXT NOT NULL,
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (parent, child, file)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inherits (
                child_class TEXT NOT NULL,
                parent_class TEXT NOT NULL,
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (child_class, parent_class, file)
            )
        """)
        
        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_child ON components(child)")
        
        self.conn.commit()
    
    def clear_tables(self):
        """清空所有表数据"""
        cursor = self.conn.cursor()
        tables = ['calls', 'components', 'inherits', 'methods', 'classes', 'files']
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()
        # 清空缓存
        self._file_cache.clear()
        for key in self._batch_buffer:
            self._batch_buffer[key].clear()
    
    def _ensure_file_exists(self, file_path: str, immediate: bool = False):
        """
        确保文件记录存在，不存在则自动插入
        
        这是修复外键约束问题的核心方法
        
        Args:
            file_path: 文件路径
            immediate: 是否立即提交（用于批量插入场景）
        """
        if file_path not in self._file_cache:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO files (path) VALUES (?)",
                (file_path,)
            )
            if immediate:
                self.conn.commit()
            self._file_cache.add(file_path)
            _logger.debug(f"[数据库] 自动插入文件记录: {file_path}")
    
    def insert_file(self, file_info: FileInfo):
        """插入文件记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO files (path) VALUES (?)",
            (file_info.path,)
        )
        self._file_cache.add(file_info.path)
    
    def insert_class(self, class_info: ClassInfo):
        """
        插入类/组件记录 (修复版)
        
        修复: 先检查文件是否存在，不存在则自动插入文件记录
        """
        # 修复外键约束问题：确保文件存在
        self._ensure_file_exists(class_info.file)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO classes 
               (name, file, is_component, is_entry, line_number) 
               VALUES (?, ?, ?, ?, ?)""",
            (class_info.name, class_info.file, 
             int(class_info.is_component), int(class_info.is_entry),
             class_info.line_number)
        )
    
    def insert_method(self, method_info: MethodInfo):
        """
        插入方法记录 (修复版)
        
        修复: 先检查文件是否存在，不存在则自动插入文件记录
        """
        # 修复外键约束问题：确保文件存在
        self._ensure_file_exists(method_info.file)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO methods 
               (name, class_name, file, line_number, is_static, is_private) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (method_info.name, method_info.class_name, method_info.file,
             method_info.line_number, int(method_info.is_static or False), 
             int(method_info.is_private or False))
        )
    
    def insert_call(self, call: CallRelation):
        """插入调用关系"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO calls 
               (caller, caller_class, callee, callee_class, file, line_number) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (call.caller, call.caller_class, call.callee, call.callee_class,
             call.file, call.line_number)
        )
    
    def insert_component_relation(self, comp: ComponentRelation):
        """插入组件嵌套关系"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO components 
               (parent, child, file, line_number) 
               VALUES (?, ?, ?, ?)""",
            (comp.parent, comp.child, comp.file, comp.line_number)
        )
    
    def insert_inherit(self, inherit: InheritRelation):
        """插入继承关系"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO inherits 
               (child_class, parent_class, file, line_number) 
               VALUES (?, ?, ?, ?)""",
            (inherit.child_class, inherit.parent_class, inherit.file, inherit.line_number)
        )
    
    # ========== 批量插入方法 (性能优化) ==========
    
    def batch_insert_file(self, file_info: FileInfo):
        """批量插入文件记录"""
        if file_info.path not in self._file_cache:
            self._batch_buffer['files'].append((file_info.path,))
            self._file_cache.add(file_info.path)
            self._check_batch('files')
    
    def batch_insert_class(self, class_info: ClassInfo):
        """批量插入类记录"""
        self._ensure_file_exists(class_info.file, immediate=True)
        self._batch_buffer['classes'].append((
            class_info.name, class_info.file,
            int(class_info.is_component), int(class_info.is_entry),
            class_info.line_number
        ))
        self._check_batch('classes')
    
    def batch_insert_method(self, method_info: MethodInfo):
        """批量插入方法记录"""
        self._ensure_file_exists(method_info.file, immediate=True)
        self._batch_buffer['methods'].append((
            method_info.name, method_info.class_name, method_info.file,
            method_info.line_number, int(method_info.is_static or False),
            int(method_info.is_private or False)
        ))
        self._check_batch('methods')
    
    def batch_insert_call(self, call: CallRelation):
        """批量插入调用关系"""
        self._batch_buffer['calls'].append((
            call.caller, call.caller_class, call.callee, call.callee_class,
            call.file, call.line_number
        ))
        self._check_batch('calls')
    
    def batch_insert_component(self, comp: ComponentRelation):
        """批量插入组件关系"""
        self._batch_buffer['components'].append((
            comp.parent, comp.child, comp.file, comp.line_number
        ))
        self._check_batch('components')
    
    def batch_insert_inherit(self, inherit: InheritRelation):
        """批量插入继承关系"""
        self._batch_buffer['inherits'].append((
            inherit.child_class, inherit.parent_class, inherit.file, inherit.line_number
        ))
        self._check_batch('inherits')
    
    def _check_batch(self, table: str):
        """检查是否需要刷新批量缓冲区"""
        if len(self._batch_buffer[table]) >= self._batch_size:
            self._flush_batch(table)
    
    def _flush_batch(self, table: str):
        """刷新指定表的批量缓冲区"""
        if not self._batch_buffer[table]:
            return
        
        cursor = self.conn.cursor()
        
        if table == 'files':
            cursor.executemany(
                "INSERT OR IGNORE INTO files (path) VALUES (?)",
                self._batch_buffer[table]
            )
        elif table == 'classes':
            cursor.executemany(
                """INSERT OR IGNORE INTO classes 
                   (name, file, is_component, is_entry, line_number) 
                   VALUES (?, ?, ?, ?, ?)""",
                self._batch_buffer[table]
            )
        elif table == 'methods':
            cursor.executemany(
                """INSERT OR IGNORE INTO methods 
                   (name, class_name, file, line_number, is_static, is_private) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                self._batch_buffer[table]
            )
        elif table == 'calls':
            cursor.executemany(
                """INSERT OR IGNORE INTO calls 
                   (caller, caller_class, callee, callee_class, file, line_number) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                self._batch_buffer[table]
            )
        elif table == 'components':
            cursor.executemany(
                """INSERT OR IGNORE INTO components 
                   (parent, child, file, line_number) 
                   VALUES (?, ?, ?, ?)""",
                self._batch_buffer[table]
            )
        elif table == 'inherits':
            cursor.executemany(
                """INSERT OR IGNORE INTO inherits 
                   (child_class, parent_class, file, line_number) 
                   VALUES (?, ?, ?, ?)""",
                self._batch_buffer[table]
            )
        
        self.conn.commit()
        _logger.debug(f"[数据库] 批量插入 {len(self._batch_buffer[table])} 条记录到 {table}")
        self._batch_buffer[table].clear()
    
    def _flush_all_batches(self):
        """刷新所有批量缓冲区"""
        for table in self._batch_buffer:
            self._flush_batch(table)
    
    def get_schema_description(self) -> str:
        """获取数据库schema描述，用于AI查询"""
        return """
数据库表结构：

1. files - 文件表
   - path: 文件路径 (主键)

2. classes - 类/组件表
   - name: 类名
   - file: 所属文件
   - is_component: 是否为组件 (0/1)
   - is_entry: 是否为入口组件 (0/1)
   - line_number: 行号

3. methods - 方法表
   - name: 方法名
   - class_name: 所属类名
   - file: 所属文件
   - line_number: 行号
   - is_static: 是否静态方法 (0/1)
   - is_private: 是否私有方法 (0/1)

4. calls - 函数调用关系表
   - caller: 调用者方法名
   - caller_class: 调用者所属类
   - callee: 被调用方法名
   - callee_class: 被调用方法所属类
   - file: 文件路径
   - line_number: 行号

5. components - 组件嵌套关系表
   - parent: 父组件名
   - child: 子组件名
   - file: 文件路径
   - line_number: 行号

6. inherits - 继承关系表
   - child_class: 子类名
   - parent_class: 父类名
   - file: 文件路径
   - line_number: 行号
"""
    
    def execute_query(self, sql: str) -> List[Tuple]:
        """执行SQL查询"""
        cursor = self.conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM files")
        stats['files'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM classes")
        stats['classes'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM classes WHERE is_component = 1")
        stats['components'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM classes WHERE is_entry = 1")
        stats['entry_components'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM methods")
        stats['methods'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM calls")
        stats['call_relations'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM components")
        stats['component_relations'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inherits")
        stats['inherit_relations'] = cursor.fetchone()[0]
        
        return stats


# ============================================================================
# ArkTS代码解析器 (Fixed Version)
# ============================================================================

# Unicode标识符模式（支持中文、日文、韩文、$符号）
_ID_PATTERN = r'[\w$\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]+'


class ArkTSParser:
    """
    ArkTS代码静态解析器 V4 (Fixed)
    
    修复内容:
    1. 增强箭头函数正则表达式，支持更多格式
    2. 增强内置标识符过滤逻辑
    3. 添加错误恢复机制
    4. 缓存正则表达式以提高性能
    
    核心设计变更：所有解析都在stripped内容上操作（stripped = 移除注释和字符串后的内容），
    避免原始内容和stripped内容之间的位置映射问题。行号通过 content[:pos].count('\n')
    从原始内容获取。
    """

    # === 过滤器集合 (增强版) ===

    # ArkTS内置UI组件名 (扩展列表)
    UI_COMPONENTS = frozenset({
        'Text', 'Row', 'Column', 'List', 'ListItem', 'Image', 'Button',
        'Stack', 'Badge', 'TextInput', 'TextArea', 'LoadingProgress',
        'Blank', 'Scroll', 'Grid', 'GridItem', 'Tabs', 'TabContent',
        'Swiper', 'Dialog', 'Alert', 'Navigation', 'Web', 'Video',
        'Slider', 'Toggle', 'Radio', 'Checkbox', 'Select', 'Marquee',
        'Progress', 'QRCode', 'RichText', 'Span', 'Container',
        'Panel', 'Overlay', 'Shape', 'Circle', 'Ellipse', 'Line',
        'Polyline', 'Polygon', 'Path', 'Rect', 'Form', 'Stepper',
        'StepperItem', 'MenuItem', 'Search', 'Toolbar', 'TitleBar',
        'NavDestination', 'NavRouter', 'WaterFlow', 'FlowItem',
        'Counter', 'Gauge', 'DataPanel', 'Rating',
        'TimePicker', 'DatePicker', 'Canvas', 'XComponent',
        'ForEach', 'LazyForEach',
        # 新增组件
        'Flex', 'Divider', 'Refresh', 'LoadMore', 'ListItemGroup',
        'GridRow', 'GridCol', 'SideBar', 'SideBarContainer',
        'AlphabetIndexer', 'TextPicker', 'DatePickerDialog',
        'TimePickerDialog', 'TextClock', 'TextTimer', 'PatternLock',
        'Particle', 'PluginComponent', 'AtomicServiceContainer',
    })

    # ArkTS链式属性设置方法 (扩展列表)
    UI_CHAIN_PROPERTIES = frozenset({
        'fontSize', 'fontWeight', 'fontColor', 'fontStyle', 'fontFamily',
        'backgroundColor', 'backgroundBlurStyle', 'backgroundImage',
        'width', 'height', 'size', 'constraintSize', 'layoutWeight',
        'margin', 'padding', 'border', 'borderWidth', 'borderColor',
        'borderRadius', 'borderStyle',
        'objectFit', 'imageRenderMode', 'interpolation',
        'textAlign', 'textOverflow', 'maxLines', 'minFontSize', 'maxFontSize',
        'decoration', 'letterSpacing', 'lineHeight', 'baselineOffset',
        'textCase', 'copyOption', 'textShadow', 'heightAdaptive',
        'fillColor', 'strokeColor', 'strokeWidth',
        'type', 'stateEffect', 'enabled', 'opacity',
        'rotate', 'scale', 'translate', 'offset', 'position',
        'align', 'direction', 'justifyContent', 'alignItems',
        'shadow', 'blur', 'grayscale', 'brightness', 'saturate',
        'contrast', 'invert', 'colorBlend', 'linearGradient',
        'clip', 'renderFit',
        'onClick', 'onChange', 'onSubmit', 'onEditChange', 'onFocus',
        'onBlur', 'onAppear', 'onDisappear', 'onReachEnd',
        'onGesture', 'onTouch', 'onAreaChange', 'onKeyEvent',
        'onSizeChange', 'onDidBuild',
        'onPageShow', 'onPageHide', 'onBackPress', 'onQuery',
        'onShare', 'onSaveForm', 'responseRegion', 'hitTestBehavior',
        'overlay', 'transition', 'animation', 'geometryTransition',
        'id', 'tag', 'name', 'style', 'show', 'visibility',
        'zIndex', 'markAnchor', 'anchor',
        # 新增属性
        'aspectRatio', 'flexBasis', 'flexGrow', 'flexShrink', 'alignSelf',
        'gridRowStart', 'gridRowEnd', 'gridColumnStart', 'gridColumnEnd',
        'displayPriority', 'expandSafeArea', 'draggable', 'enabled',
        'focusable', 'tabIndex', 'key', 'restoreId', 'systemBarEffect',
        'backgroundEffect', 'foregroundEffect', 'pixelStretchEffect',
        'lightUpEffect', 'spotlightEffect', 'disappearBadge',
    })

    # JS全局对象
    JS_GLOBALS = frozenset({
        'console', 'Math', 'Array', 'Object', 'String', 'Number',
        'Boolean', 'Promise', 'JSON', 'Date', 'RegExp', 'Error',
        'TypeError', 'RangeError', 'SyntaxError', 'ReferenceError',
        'Map', 'Set', 'Symbol', 'Proxy', 'Reflect', 'WeakMap', 'WeakSet',
        'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURI',
        'decodeURI', 'encodeURIComponent', 'decodeURIComponent',
        'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
        'requestAnimationFrame', 'cancelAnimationFrame',
        'fetch', 'import', 'require', 'module', 'exports', 'globalThis',
        'ArrayBuffer', 'Uint8Array', 'Float32Array', 'Int32Array',
        'DataView', 'SharedArrayBuffer', 'atob', 'btoa',
        'structuredClone', 'queueMicrotask', 'Infinity', 'NaN', 'undefined',
    })

    # JS关键字
    JS_KEYWORDS = frozenset({
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break',
        'continue', 'return', 'throw', 'try', 'catch', 'finally',
        'new', 'delete', 'typeof', 'instanceof', 'in', 'of',
        'void', 'this', 'super', 'class', 'function', 'var', 'let',
        'const', 'import', 'export', 'default', 'from', 'as',
        'async', 'await', 'yield', 'true', 'false', 'null', 'undefined',
        'static', 'get', 'set', 'extends', 'implements', 'interface',
        'type', 'enum', 'abstract', 'readonly', 'override',
    })

    # ArkTS关键字
    ARKTS_KEYWORDS = frozenset({
        'struct', 'declare', 'namespace', 'module', 'entry', 'component',
        'customdialog', 'reusable', 'state', 'prop', 'link', 'provide',
        'consume', 'storageprop', 'storagelink', 'watch', 'builder',
        'build', 'styles', 'extend', 'animator', 'keyframes',
    })

    # 所有应跳过的标识符 (合并所有集合)
    SKIP_IDENTIFIERS = JS_GLOBALS | JS_KEYWORDS | ARKTS_KEYWORDS | UI_COMPONENTS | UI_CHAIN_PROPERTIES

    def __init__(self):
        # ========== 缓存正则表达式 (性能优化) ==========
        self._init_regex_patterns()
        
        # 存储列表
        self.files: List[FileInfo] = []
        self.classes: List[ClassInfo] = []
        self.methods: List[MethodInfo] = []
        self.calls: List[CallRelation] = []
        self.component_relations: List[ComponentRelation] = []
        self.inherits: List[InheritRelation] = []

        # _component_names, _all_class_names
        self._component_names: Set[str] = set()
        self._all_class_names: Set[str] = set()
    
    def _init_regex_patterns(self):
        """初始化并缓存所有正则表达式"""
        # 装饰器正则（支持嵌套括号如 @StorageLink(StorageKeys.THEME)）
        self.decorator_pattern = re.compile(r'@\w+\s*\([^()]*\)')
        # 组件装饰器（@Component, @CustomDialog, @Reusable 都标记为组件）
        self.component_decorator = re.compile(r'@(?:Component|CustomDialog|Reusable)\s*(?:\([^()]*\))?\s*')
        self.entry_decorator = re.compile(r'@Entry\s*(?:\([^()]*\))?\s*')

        # struct正则（支持extends和implements）
        self.struct_pattern = re.compile(
            r'(export\s+)?(default\s+)?struct\s+(' + _ID_PATTERN + r')\s*(?:<[^>]*>)?\s*(?:extends\s+(' + _ID_PATTERN + r'))?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # class正则
        self.class_pattern = re.compile(
            r'(export\s+)?(default\s+)?(abstract\s+)?class\s+(' + _ID_PATTERN + r')\s*(?:<[^>]*>)?\s*(?:extends\s+(\w+)(?:\s*<[^>]*>)?)?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # method正则（行首锚定，支持abstract/override关键字）
        # 注意：不包含装饰器匹配，装饰器在 _parse_methods 中预先移除
        self.method_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(async\s+)?(abstract\s+|override\s+)?(' + _ID_PATTERN + r')\s*(?:<[^>]*>\s*)?\(',
            re.MULTILINE
        )

        # 装饰器行移除正则（保留行号，用于方法解析前的预处理）
        self.decorator_line_pattern = re.compile(
            r'^([ \t]*)@\w+[ \t]*\([^()]*\)[ \t]*',
            re.MULTILINE
        )
        self.decorator_line_noarg_pattern = re.compile(
            r'^([ \t]*)@\w+[ \t]+',
            re.MULTILINE
        )

        # ========== 修复: 增强箭头函数正则表达式 ==========
        # 支持更多格式的箭头函数:
        # - `const fn = () => {}`
        # - `const fn = (a, b) => {}`
        # - `const fn = a => {}`
        # - `private callback = () => {}`
        # - `public handler = (e: Event) => {}`
        # - `onClick = (event: ClickEvent) => {}`
        # - `handler = (e) => {}`
        self.arrow_property_pattern = re.compile(
            r'^[ \t]*'  # 行首空白
            r'(?:(private|public|protected)\s+)?'  # 可选访问修饰符 (捕获组1)
            r'(?:(static)\s+)?'  # 可选static (捕获组2)
            r'(?:(readonly)\s+)?'  # 可选readonly (捕获组3)
            r'(' + _ID_PATTERN + r')'  # 属性名 (捕获组4)
            r'\s*'  # 可选空白
            r'(?:<[^>]*>)?'  # 可选泛型
            r'\s*'  # 可选空白
            r'=\s*'  # 等号
            r'(?:\([^)]*\)|\w+)'  # 参数: 括号形式或单参数
            r'\s*'  # 可选空白
            r'(?:<[^>]*>)?'  # 可选泛型返回类型
            r'\s*'  # 可选空白
            r'=>',  # 箭头
            re.MULTILINE
        )
        
        # 简化的箭头函数模式（用于快速匹配）
        self.arrow_simple_pattern = re.compile(
            r'^[ \t]*'  # 行首空白
            r'(?:(private|public|protected)\s+)?'  # 可选访问修饰符 (捕获组1)
            r'(?:(static)\s+)?'  # 可选static (捕获组2)
            r'(' + _ID_PATTERN + r')'  # 属性名 (捕获组3)
            r'\s*=\s*\(',  # 等号和左括号
            re.MULTILINE
        )

        # call正则 (支持泛型方法调用如 get<T>())
        # 注意: <[^>]*> 不能处理嵌套泛型如 <ApiResponse<Product[]>>，改用 <[^{;]*?>
        self.call_pattern = re.compile(
            r'(?:(\w+)\s*\.\s*)?(\w+)\s*(?:<[^{;]*?>\s*)?\(',
            re.MULTILINE
        )

        # import正则
        self.import_pattern = re.compile(
            r'import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
            re.MULTILINE
        )

        # 顶层函数正则（支持复杂泛型如 <T extends (...args: any[]) => Promise<any>>）
        self.top_func_pattern = re.compile(
            r'(export\s+)?(async\s+)?function\s+(' + _ID_PATTERN + r')\s*(?:<[^{]*?>\s*)?\(',
            re.MULTILINE
        )

    @error_recovery(default_return="")
    def _strip_comments_and_strings(self, content: str) -> str:
        """移除注释和字符串，保留换行符"""
        result = []
        i = 0
        n = len(content)
        while i < n:
            c = content[i]
            # 单行注释
            if c == '/' and i + 1 < n and content[i + 1] == '/':
                while i < n and content[i] != '\n':
                    i += 1
                result.append(' ')
            # 多行注释
            elif c == '/' and i + 1 < n and content[i + 1] == '*':
                i += 2
                while i + 1 < n and not (content[i] == '*' and content[i + 1] == '/'):
                    if content[i] == '\n':
                        result.append('\n')
                    i += 1
                i += 2
                result.append(' ')
            # 模板字符串 `...`
            elif c == '`':
                result.append(' ')
                i += 1
                while i < n and content[i] != '`':
                    if content[i] == '\\':
                        i += 1
                    if content[i] == '\n':
                        result.append('\n')
                    i += 1
                if i < n:
                    i += 1
                result.append(' ')
            # 双引号字符串
            elif c == '"':
                result.append(' ')
                i += 1
                while i < n and content[i] != '"':
                    if content[i] == '\\':
                        i += 1
                    i += 1
                if i < n:
                    i += 1
                result.append(' ')
            # 单引号字符串
            elif c == "'":
                result.append(' ')
                i += 1
                while i < n and content[i] != "'":
                    if content[i] == '\\':
                        i += 1
                    i += 1
                if i < n:
                    i += 1
                result.append(' ')
            else:
                result.append(c)
                i += 1
        return ''.join(result)

    @error_recovery(default_return=-1)
    def _find_matching_brace(self, stripped: str, start: int) -> int:
        """在stripped内容中找到匹配的}"""
        brace_count = 0
        i = start
        while i < len(stripped):
            if stripped[i] == '{':
                brace_count += 1
            elif stripped[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
            i += 1
        return len(stripped) - 1

    @error_recovery(default_return={
        'files': [], 'classes': [], 'methods': [],
        'calls': [], 'component_relations': [], 'inherits': []
    })
    def parse_project(self, project_path: str) -> Dict:
        """解析整个项目 - 两遍解析"""
        project_path = Path(project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {project_path}")

        arkts_files = list(project_path.rglob("*.ets")) + \
                      list(project_path.rglob("*.ts"))

        print(f"找到 {len(arkts_files)} 个ArkTS文件")
        _logger.info(f"开始解析项目: {project_path}, 共 {len(arkts_files)} 个文件")

        # 第一遍：收集所有类/组件名（不解析方法）
        for file_path in arkts_files:
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            self._scan_declarations(str(file_path))

        # 第二遍：完整解析（包括方法，可利用第一遍收集的名称）
        for file_path in arkts_files:
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            self._full_parse(str(file_path))

        # 后处理
        self._resolve_callee_classes()
        self._extract_component_relations()

        return self._get_result()

    @error_recovery()
    def _scan_declarations(self, file_path: str):
        """第一遍：只收集类/组件声明"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            _logger.warning(f"[扫描] 无法读取文件 {file_path}: {e}")
            return

        self.files.append(FileInfo(path=file_path))
        stripped = self._strip_comments_and_strings(content)
        _logger.debug(f"[SCAN] {file_path}: stripped {len(content)} -> {len(stripped)} chars")

        for match in self.struct_pattern.finditer(stripped):
            name = match.group(3)
            before = stripped[:match.start()]
            last_brace = before.rfind('}')
            region = before[last_brace:] if last_brace != -1 else before
            if self.component_decorator.search(region):
                self._component_names.add(name)
                _logger.debug(f"[SCAN] struct '{name}' -> component (decorator found)")
            self._all_class_names.add(name)
            _logger.debug(f"[SCAN] struct '{name}' declared at line {content[:match.start()].count(chr(10))+1}")

        for match in self.class_pattern.finditer(stripped):
            name = match.group(4)
            self._all_class_names.add(name)
            _logger.debug(f"[SCAN] class '{name}' declared at line {content[:match.start()].count(chr(10))+1}")

    @error_recovery()
    def _full_parse(self, file_path: str):
        """第二遍：完整解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            _logger.warning(f"[解析] 无法读取文件 {file_path}: {e}")
            return

        stripped = self._strip_comments_and_strings(content)
        _logger.debug(f"[PARSE] {file_path}: starting full parse")

        # struct
        for match in self.struct_pattern.finditer(stripped):
            name = match.group(3)
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1

            before = stripped[:start_pos]
            last_brace = before.rfind('}')
            region = before[last_brace:] if last_brace != -1 else before
            is_component = bool(self.component_decorator.search(region))
            is_entry = bool(self.entry_decorator.search(region))

            self.classes.append(ClassInfo(
                name=name, file=file_path,
                is_component=is_component, is_entry=is_entry,
                line_number=line_number
            ))
            _logger.debug(f"[PARSE] struct '{name}' L{line_number} component={is_component} entry={is_entry}")

            # 提取struct的extends继承关系
            parent_class = match.group(4)
            if parent_class and parent_class not in self.JS_KEYWORDS:
                self.inherits.append(InheritRelation(
                    child_class=name, parent_class=parent_class,
                    file=file_path, line_number=line_number
                ))
                _logger.debug(f"[PARSE] struct '{name}' extends '{parent_class}'")

            # 提取struct的implements接口关系
            implements_str = match.group(5)
            if implements_str:
                for iface_name in re.findall(r'\b(\w+)\b', implements_str):
                    if iface_name not in self.JS_KEYWORDS and iface_name != name:
                        self.inherits.append(InheritRelation(
                            child_class=name, parent_class=iface_name,
                            file=file_path, line_number=line_number
                        ))
                        _logger.debug(f"[PARSE] struct '{name}' implements '{iface_name}'")

            body = self._extract_body(stripped, match.end() - 1)
            _logger.debug(f"[PARSE] struct '{name}' body extracted: {len(body)} chars")
            self._parse_methods(body, name, file_path, line_number)

        # class
        for match in self.class_pattern.finditer(stripped):
            name = match.group(4)
            parent = match.group(5)
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1

            if any(c.name == name and c.file == file_path for c in self.classes):
                continue

            before = stripped[:start_pos]
            last_brace = before.rfind('}')
            region = before[last_brace:] if last_brace != -1 else before
            is_component = bool(self.component_decorator.search(region))
            is_entry = bool(self.entry_decorator.search(region))

            self.classes.append(ClassInfo(
                name=name, file=file_path,
                is_component=is_component, is_entry=is_entry,
                line_number=line_number
            ))

            if parent:
                self.inherits.append(InheritRelation(
                    child_class=name, parent_class=parent,
                    file=file_path, line_number=line_number
                ))

            # 提取implements接口关系
            implements_str = match.group(6)
            if implements_str:
                for iface_name in re.findall(r'\b(\w+)\b', implements_str):
                    if iface_name not in self.JS_KEYWORDS and iface_name != name:
                        self.inherits.append(InheritRelation(
                            child_class=name, parent_class=iface_name,
                            file=file_path, line_number=line_number
                        ))

            body = self._extract_body(stripped, match.end() - 1)
            self._parse_methods(body, name, file_path, line_number)

        self._parse_top_level_functions(stripped, content, file_path)

    def _extract_body(self, stripped: str, open_brace: int) -> str:
        """在stripped上提取类体"""
        close = self._find_matching_brace(stripped, open_brace)
        return stripped[open_brace:close + 1]

    @error_recovery()
    def _parse_methods(self, body_stripped: str, class_name: str, file_path: str,
                       class_line: int):
        """
        在stripped类体上解析方法（包括箭头函数属性）
        
        修复: 增强箭头函数识别和内置标识符过滤
        """
        # 在类方法上下文中，以下关键字是合法的方法名
        METHOD_SAFE_KEYWORDS = {'get', 'set', 'delete', 'has', 'of'}
        # ArkTS组件生命周期方法 — 即使与UI_CHAIN_PROPERTIES重名也应识别
        ARKTS_LIFECYCLE = frozenset({
            'aboutToAppear', 'aboutToDisappear', 'aboutToRecycle', 'aboutToReuse',
            'onPageShow', 'onPageHide', 'onBackPress', 'onQuery',
            'onWindowStageCreate', 'onWindowStageDestroy',
            'onForeground', 'onBackground',
            'onDidBuild', 'onSizeChange', 'onAreaChange',
        })

        # 预处理：移除装饰器（保留行号，避免正则回溯问题）
        # 先移除带参数的装饰器（如 @Watch('onThemeChange') -> @Watch(...) 在stripped中变为 @Watch(  )）
        body_no_dec = self.decorator_line_pattern.sub(r'\1', body_stripped)
        # 再移除无参数的装饰器（如 @Component）
        body_no_dec = self.decorator_line_noarg_pattern.sub(r'\1', body_no_dec)
        
        # 计算每个位置的花括号深度（只在顶层深度=1时匹配方法）
        brace_depth = 0
        depth_at_pos = {}
        for idx, ch in enumerate(body_no_dec):
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            depth_at_pos[idx] = brace_depth
        
        # 收集所有已匹配的位置，避免箭头函数属性和普通方法重复
        matched_positions = set()

        # 1. 匹配普通方法（含abstract方法）
        for match in self.method_pattern.finditer(body_no_dec):
            method_name = match.group(5)  # group(5) = 方法名（新增了abstract为group(4)）

            # 只匹配类体顶层的方法定义（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            # 修复: 增强过滤逻辑，确保所有内置标识符都被正确过滤
            if not self._is_valid_method_name(method_name, class_name, METHOD_SAFE_KEYWORDS, ARKTS_LIFECYCLE):
                continue

            matched_positions.add(match.start())

            # 行号用 class_line + body_no_dec[:match.start()].count('\n')
            line_number = class_line + body_no_dec[:match.start()].count('\n')

            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)
            is_abstract = match.group(4) is not None and 'abstract' in match.group(4)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private
            ))
            _logger.debug(f"[METHOD] '{class_name}.{method_name}' L{line_number} static={is_static} private={is_private} abstract={is_abstract}")

            # abstract方法没有方法体
            if is_abstract:
                continue

            # 提取方法体
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
            if brace_pos == -1:
                _logger.debug(f"[METHOD] '{class_name}.{method_name}' -> no body found (brace_pos=-1)")
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            _logger.debug(f"[METHOD] '{class_name}.{method_name}' body: {len(method_body_stripped)} chars")
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

        # 2. 匹配箭头函数属性（修复: 使用增强的正则表达式）
        self._parse_arrow_functions(
            body_no_dec, depth_at_pos, matched_positions,
            class_name, file_path, class_line,
            METHOD_SAFE_KEYWORDS, ARKTS_LIFECYCLE
        )

    def _is_valid_method_name(self, method_name: str, class_name: str,
                              safe_keywords: Set[str], lifecycle: Set[str]) -> bool:
        """
        检查方法名是否有效（不是内置标识符）
        
        修复: 增强过滤逻辑，确保所有内置标识符都被正确过滤
        """
        # 跳过: JS_KEYWORDS, ARKTS_KEYWORDS (但保留安全关键字)
        if method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS:
            if method_name not in safe_keywords:
                return False
        
        # 跳过 constructor
        if method_name == 'constructor':
            return False
        
        # 修复: 确保所有 UI_COMPONENTS 都被正确过滤
        if method_name in self.UI_COMPONENTS:
            return False
        
        # 修复: 确保所有 UI_CHAIN_PROPERTIES 都被正确过滤（但保留生命周期方法）
        if method_name in self.UI_CHAIN_PROPERTIES and method_name not in lifecycle:
            return False
        
        # 跳过已知组件名（在build体中使用的组件不是方法定义）
        if method_name in self._component_names and method_name != class_name:
            return False
        
        # 跳过已知类名（同理）
        if method_name in self._all_class_names and method_name != class_name:
            return False
        
        return True

    def _parse_arrow_functions(self, body_no_dec: str, depth_at_pos: Dict[int, int],
                               matched_positions: Set[int], class_name: str,
                               file_path: str, class_line: int,
                               safe_keywords: Set[str], lifecycle: Set[str]):
        """
        解析箭头函数属性
        
        修复: 支持更多箭头函数格式
        """
        # 使用增强的正则表达式匹配箭头函数
        for match in self.arrow_property_pattern.finditer(body_no_dec):
            # 跳过已匹配的位置
            if match.start() in matched_positions:
                continue

            # 获取属性名（在增强正则中是第4组）
            method_name = match.group(4)
            if not method_name:
                continue

            # 只匹配类体顶层（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            # 检查是否为有效方法名
            if not self._is_valid_method_name(method_name, class_name, safe_keywords, lifecycle):
                continue

            line_number = class_line + body_no_dec[:match.start()].count('\n')
            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private
            ))
            _logger.debug(f"[ARROW] '{class_name}.{method_name}' L{line_number} static={is_static} private={is_private}")

            # 提取箭头函数体
            # 找到 => 后的位置
            arrow_match = re.search(r'=>\s*\{', body_no_dec[match.start():match.end() + 200])
            if arrow_match:
                brace_pos = match.start() + arrow_match.start() + arrow_match.group().index('{')
                close_pos = self._find_matching_brace(body_no_dec, brace_pos)
                method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
                self._parse_calls(method_body_stripped, method_name, class_name,
                                  file_path, line_number)

        # 使用简化正则作为备选（捕获组不同）
        for match in self.arrow_simple_pattern.finditer(body_no_dec):
            if match.start() in matched_positions:
                continue

            method_name = match.group(3)
            if not method_name:
                continue

            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            if not self._is_valid_method_name(method_name, class_name, safe_keywords, lifecycle):
                continue

            # 检查是否已被第一个正则匹配
            already_matched = False
            for pos in matched_positions:
                if abs(pos - match.start()) < 10:  # 接近的位置
                    already_matched = True
                    break
            if already_matched:
                continue

            line_number = class_line + body_no_dec[:match.start()].count('\n')
            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private
            ))
            _logger.debug(f"[ARROW_SIMPLE] '{class_name}.{method_name}' L{line_number}")

            # 提取方法体
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
            if brace_pos == -1:
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

    @error_recovery(default_return=-1)
    def _skip_params_and_return_type(self, stripped: str, paren_pos: int) -> int:
        """跳过参数列表和返回类型，返回方法体{的位置"""
        i = paren_pos
        n = len(stripped)

        # 括号匹配跳过参数
        paren_count = 0
        while i < n:
            if stripped[i] == '(':
                paren_count += 1
            elif stripped[i] == ')':
                paren_count -= 1
                if paren_count == 0:
                    i += 1
                    break
            i += 1

        # 跳过空格
        while i < n and stripped[i] in ' \t\n\r':
            i += 1

        if i >= n:
            return -1

        # 如果遇到':'，跳过返回类型(到'{'或';')
        if stripped[i] == ':':
            i += 1
            angle_count = 0
            brace_count = 0
            while i < n:
                if stripped[i] == '<':
                    angle_count += 1
                elif stripped[i] == '>':
                    angle_count -= 1
                elif stripped[i] == '{' and angle_count <= 0:
                    if brace_count == 0:
                        return i
                    brace_count += 1
                elif stripped[i] == '}' and angle_count <= 0:
                    brace_count -= 1
                elif stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
                    break
                elif stripped[i] == ';' and angle_count <= 0 and brace_count == 0:
                    return -1
                i += 1

        if i >= n:
            return -1

        # 如果遇到'=>'，跳过到'{'或表达式结束
        if stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
            i += 2
            while i < n and stripped[i] in ' \t\n\r':
                i += 1
            if i < n and stripped[i] == '{':
                return i
            else:
                # 箭头函数表达式体，没有花括号方法体
                return -1

        # 普通方法体
        if stripped[i] == '{':
            return i

        return -1

    @error_recovery()
    def _parse_calls(self, method_body_stripped: str, method_name: str,
                     class_name: str, file_path: str, line_number: int):
        """在stripped方法体上解析调用关系"""
        if not method_body_stripped:
            return

        for match in self.call_pattern.finditer(method_body_stripped):
            obj_name = match.group(1)  # 可能是None
            callee = match.group(2)

            # 跳过SKIP_IDENTIFIERS（但如果obj_name存在，保留get/set/delete等）
            if callee in self.SKIP_IDENTIFIERS:
                # 如果是 obj.method() 形式，保留常见方法名
                if obj_name and callee in {'get', 'set', 'delete', 'has', 'of', 'entries', 'keys', 'values', 'forEach', 'map', 'filter', 'reduce', 'find', 'some', 'every', 'includes', 'indexOf', 'slice', 'splice', 'push', 'pop', 'shift', 'unshift', 'join', 'split', 'trim', 'toString', 'toFixed', 'stringify', 'parse', 'json', 'then', 'catch', 'finally', 'next', 'done', 'value', 'ok', 'status', 'length', 'count', 'round', 'min', 'max', 'abs', 'floor', 'ceil', 'random', 'sort', 'reverse', 'concat', 'flat', 'fill', 'copyWithin', 'entries'}:
                    pass  # 保留
                else:
                    continue

            # 跳过数字开头的obj_name
            if obj_name and re.match(r'^\d', obj_name):
                continue

            # 跳过单字母变量
            if obj_name and len(obj_name) == 1 and obj_name.islower():
                continue

            # 行号用 method_line + method_body_stripped[:match.start()].count('\n')
            call_line = line_number + method_body_stripped[:match.start()].count('\n')

            self.calls.append(CallRelation(
                caller=method_name,
                caller_class=class_name,
                callee=callee,
                callee_class=obj_name if obj_name and obj_name != 'this' else '',
                file=file_path,
                line_number=call_line
            ))
            _logger.debug(f"[CALL] '{class_name}.{method_name}' -> '{callee}' (obj={obj_name})")

    @error_recovery()
    def _parse_top_level_functions(self, stripped: str, content: str, file_path: str):
        """解析顶层函数"""
        for match in self.top_func_pattern.finditer(stripped):
            func_name = match.group(3)
            line_number = content[:match.start()].count('\n') + 1
            self.methods.append(MethodInfo(
                name=func_name, class_name='',
                file=file_path, line_number=line_number
            ))

    @error_recovery()
    def _resolve_callee_classes(self):
        """后处理：推断callee_class"""
        # 构建类→方法映射
        class_methods = {}
        for cls in self.classes:
            methods = set()
            for m in self.methods:
                if m.class_name == cls.name:
                    methods.add(m.name)
            class_methods[cls.name] = methods
        
        # 提取成员变量类型
        member_types = self._extract_member_types()
        
        for call in self.calls:
            if call.callee_class:
                # 已有推断，验证并优化
                if call.callee_class not in self._all_class_names:
                    # obj_name不是类名，尝试通过成员变量推断
                    resolved = member_types.get(call.caller_class, {}).get(call.callee_class, '')
                    if resolved and resolved in self._all_class_names:
                        call.callee_class = resolved
                    elif not call.callee_class[0].isupper():
                        call.callee_class = ''
                continue

            # 规则1: callee本身是类名
            if call.callee in self._all_class_names:
                call.callee_class = call.callee
                continue

            # 规则3: callee是当前类的已知方法 → 同类调用
            if call.callee in class_methods.get(call.caller_class, set()):
                call.callee_class = call.caller_class
                continue
            
            # 规则4: callee是当前类的成员变量名 → 推断为变量类型
            var_type = member_types.get(call.caller_class, {}).get(call.callee, '')
            if var_type and var_type in self._all_class_names:
                call.callee_class = var_type
                continue
    
    @error_recovery(default_return={})
    def _extract_member_types(self) -> Dict[str, Dict[str, str]]:
        """从类体中提取成员变量的类型信息"""
        result = {}
        
        for cls in self.classes:
            member_map = {}
            
            try:
                with open(cls.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                continue
            
            stripped = self._strip_comments_and_strings(content)
            
            member_pattern = re.compile(
                r'(private|public|protected)?\s*'
                r'(?:static\s+)?'
                r'(\w+)\s*:\s*(\w+)'
            )
            
            # 在struct和class中查找
            for match in self.struct_pattern.finditer(stripped):
                if match.group(3) == cls.name:
                    body = self._extract_body(stripped, match.end() - 1)
                    self._scan_members_in_body(body, member_pattern, member_map)
                    break
            
            if cls.name not in member_map:
                for match in self.class_pattern.finditer(stripped):
                    if match.group(4) == cls.name:
                        body = self._extract_body(stripped, match.end() - 1)
                        self._scan_members_in_body(body, member_pattern, member_map)
                        break
            
            if member_map:
                result[cls.name] = member_map
        
        return result
    
    @error_recovery()
    def _scan_members_in_body(self, body: str, pattern, member_map: Dict):
        """在类体中扫描成员变量（只在花括号深度=1时）"""
        # 预计算每个位置的深度
        depths = []
        d = 0
        for ch in body:
            if ch == '{': d += 1
            elif ch == '}': d -= 1
            depths.append(d)
        
        for m in pattern.finditer(body):
            pos = m.start()
            if depths[pos] == 1:
                var_name = m.group(2)
                type_name = m.group(3)
                if var_name not in self.JS_KEYWORDS and type_name not in self.JS_KEYWORDS:
                    if type_name[0].isupper():
                        member_map[var_name] = type_name

    @error_recovery()
    def _extract_component_relations(self):
        """后处理：提取组件嵌套关系（去重）"""
        seen = set()

        for class_info in self.classes:
            if not class_info.is_component:
                continue

            build_calls = [
                c for c in self.calls
                if c.caller == 'build' and c.caller_class == class_info.name
            ]

            for call in build_calls:
                callee = call.callee
                is_component = (
                    callee in self._component_names or
                    any(c.name == callee and c.is_component for c in self.classes)
                )

                if is_component and callee != class_info.name:
                    key = (class_info.name, callee)
                    if key not in seen:
                        seen.add(key)
                        self.component_relations.append(ComponentRelation(
                            parent=class_info.name,
                            child=callee,
                            file=class_info.file,
                            line_number=call.line_number
                        ))

    def _get_result(self) -> Dict:
        return {
            'files': self.files,
            'classes': self.classes,
            'methods': self.methods,
            'calls': self.calls,
            'component_relations': self.component_relations,
            'inherits': self.inherits
        }


# ============================================================================
# AI查询接口
# ============================================================================

class AIQueryInterface:
    """AI查询接口
    
    使用硅基流动Qwen2.5-7B模型将自然语言转换为SQL
    """
    
    def __init__(self, api_key: str, db_manager: DatabaseManager):
        if not _HAS_OPENAI:
            raise ImportError("openai package is required for AIQueryInterface. Install with: pip install openai")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"
        )
        self.db = db_manager
        self.model = "Qwen/Qwen2.5-7B-Instruct"
    
    def text_to_sql(self, question: str) -> str:
        """将自然语言问题转换为SQL语句"""
        schema = self.db.get_schema_description()
        
        prompt = f"""你是一个SQL专家。根据以下数据库表结构，将用户的问题转换为准确的SQL查询语句。

{schema}

重要规则：
1. 只返回SQL语句，不要有任何解释
2. SQL语句必须以分号结尾
3. 使用正确的表名和字段名
4. 对于模糊查询使用LIKE和通配符%
5. 对于统计查询使用COUNT、GROUP BY等
6. 字段名使用下划线命名法（如is_component, line_number）

用户问题：{question}

SQL语句："""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            sql = response.choices[0].message.content.strip()
            
            # 清理SQL语句
            sql = self._clean_sql(sql)
            
            return sql
        except Exception as e:
            return f"-- 错误: {str(e)}"
    
    def _clean_sql(self, sql: str) -> str:
        """清理SQL语句"""
        # 移除markdown代码块标记
        sql = re.sub(r'^```sql\s*', '', sql)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql)
        
        # 移除多余空白
        sql = sql.strip()
        
        # 确保以分号结尾
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def ask(self, question: str) -> Dict:
        """执行自然语言查询"""
        # 转换为SQL
        sql = self.text_to_sql(question)
        
        # 执行查询
        try:
            results = self.db.execute_query(sql)
            columns = []
            
            # 获取列名
            cursor = self.db.conn.cursor()
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
            
            return {
                'question': question,
                'sql': sql,
                'columns': columns,
                'results': results,
                'row_count': len(results),
                'success': True
            }
        except Exception as e:
            return {
                'question': question,
                'sql': sql,
                'error': str(e),
                'success': False
            }
    
    def format_result(self, result: Dict) -> str:
        """格式化查询结果"""
        if not result['success']:
            return f"查询失败: {result.get('error', '未知错误')}\nSQL: {result['sql']}"
        
        output = []
        output.append(f"问题: {result['question']}")
        output.append(f"SQL: {result['sql']}")
        output.append(f"结果 ({result['row_count']} 行):")
        output.append("-" * 60)
        
        if result['columns']:
            # 表头
            header = " | ".join(result['columns'])
            output.append(header)
            output.append("-" * len(header))
            
            # 数据行
            for row in result['results']:
                row_str = " | ".join(str(v) if v is not None else "NULL" for v in row)
                output.append(row_str)
        else:
            for row in result['results']:
                output.append(str(row))
        
        return "\n".join(output)


# ============================================================================
# 知识图谱构建器 (Fixed Version)
# ============================================================================

class KnowledgeGraphBuilder:
    """
    知识图谱构建器 (Fixed Version)
    
    新增功能:
    1. 循环依赖检测
    2. 性能优化（批量插入）
    3. 详细的构建报告
    """
    
    def __init__(self, db_path: str = "code.db"):
        self.db = DatabaseManager(db_path)
        self.parser = ArkTSParser()
        self.circular_detector = CircularDependencyDetector()
        self.build_time: float = 0.0
    
    def build(self, project_path: str, detect_cycles: bool = True) -> Dict:
        """
        构建知识图谱
        
        Args:
            project_path: 项目路径
            detect_cycles: 是否检测循环依赖
        
        Returns:
            构建统计信息
        """
        start_time = time.time()
        
        print(f"开始构建知识图谱: {project_path}")
        _logger.info(f"开始构建知识图谱: {project_path}")
        
        # 连接数据库
        self.db.connect()
        self.db.create_tables()
        self.db.clear_tables()
        
        # 解析项目
        print("正在解析项目...")
        result = self.parser.parse_project(project_path)
        
        # 循环依赖检测
        if detect_cycles:
            print("检测循环依赖...")
            self.circular_detector.add_edges_from_relations(result['inherits'])
            if self.circular_detector.has_cycle():
                print(self.circular_detector.get_cycle_report())
            else:
                print("未发现循环依赖")
        
        # 存储到数据库
        print("正在存储到数据库...")
        self._store_result(result)
        
        # 获取统计信息
        stats = self.db.get_statistics()
        
        self.build_time = time.time() - start_time
        
        print("\n构建完成！统计信息:")
        print(f"  文件数: {stats['files']}")
        print(f"  类数: {stats['classes']}")
        print(f"  组件数: {stats['components']}")
        print(f"  入口组件数: {stats['entry_components']}")
        print(f"  方法数: {stats['methods']}")
        print(f"  调用关系数: {stats['call_relations']}")
        print(f"  组件嵌套关系数: {stats['component_relations']}")
        print(f"  继承关系数: {stats['inherit_relations']}")
        print(f"  构建耗时: {self.build_time:.2f}秒")
        
        _logger.info(f"知识图谱构建完成，耗时: {self.build_time:.2f}秒")
        
        return stats
    
    def _store_result(self, result: Dict):
        """
        存储解析结果到数据库 (使用批量插入优化)
        """
        _logger.info("开始存储解析结果到数据库...")
        
        # 存储文件（立即提交，确保外键约束）
        for file_info in result['files']:
            self.db.insert_file(file_info)
        self.db.conn.commit()
        _logger.info(f"已插入 {len(result['files'])} 个文件记录")
        
        # 存储类
        for class_info in result['classes']:
            self.db.batch_insert_class(class_info)
        
        # 存储方法
        for method_info in result['methods']:
            self.db.batch_insert_method(method_info)
        
        # 存储调用关系
        for call in result['calls']:
            self.db.batch_insert_call(call)
        
        # 存储组件关系
        for comp in result['component_relations']:
            self.db.batch_insert_component(comp)
        
        # 存储继承关系
        for inherit in result['inherits']:
            self.db.batch_insert_inherit(inherit)
        
        # 刷新所有批量缓冲区
        self.db._flush_all_batches()
        
        _logger.info("解析结果存储完成")
    
    def get_circular_dependency_report(self) -> str:
        """获取循环依赖报告"""
        return self.circular_detector.get_cycle_report()
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


# ============================================================================
# 主程序
# ============================================================================

def build_knowledge_graph(project_path: str, db_path: str = "code.db", 
                          detect_cycles: bool = True) -> KnowledgeGraphBuilder:
    """构建知识图谱的便捷函数"""
    builder = KnowledgeGraphBuilder(db_path)
    builder.build(project_path, detect_cycles=detect_cycles)
    return builder


def ask_ai(question: str, api_key: str, db_path: str = "code.db") -> Dict:
    """AI查询的便捷函数"""
    db = DatabaseManager(db_path)
    db.connect()
    
    ai = AIQueryInterface(api_key, db)
    result = ai.ask(question)
    
    db.close()
    return result


# ============================================================================
# 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ArkTS代码知识图谱系统 (Fixed Version)")
    parser.add_argument("command", choices=["build", "query", "stats", "cycles"],
                       help="命令: build构建图谱, query查询, stats统计, cycles检测循环依赖")
    parser.add_argument("--project", "-p", help="项目路径")
    parser.add_argument("--db", "-d", default="code.db", help="数据库路径")
    parser.add_argument("--question", "-q", help="查询问题")
    parser.add_argument("--api-key", "-k", help="硅基流动API密钥")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    parser.add_argument("--no-cycle-check", action="store_true", help="跳过循环依赖检测")

    args = parser.parse_args()

    if args.debug:
        setup_logging(debug=True)
    
    if args.command == "build":
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        builder = KnowledgeGraphBuilder(args.db)
        builder.build(args.project, detect_cycles=not args.no_cycle_check)
        builder.close()
        
    elif args.command == "query":
        if not args.question:
            print("错误: 需要指定查询问题 --question")
            exit(1)
        if not args.api_key:
            print("错误: 需要指定API密钥 --api-key")
            exit(1)
        
        result = ask_ai(args.question, args.api_key, args.db)
        
        db = DatabaseManager(args.db)
        db.connect()
        ai = AIQueryInterface(args.api_key, db)
        print(ai.format_result(result))
        db.close()
        
    elif args.command == "stats":
        db = DatabaseManager(args.db)
        db.connect()
        stats = db.get_statistics()
        
        print("\n知识图谱统计信息:")
        print("=" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        db.close()
    
    elif args.command == "cycles":
        # 检测循环依赖
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        print(f"检测项目循环依赖: {args.project}")
        parser = ArkTSParser()
        result = parser.parse_project(args.project)
        
        detector = CircularDependencyDetector()
        detector.add_edges_from_relations(result['inherits'])
        print(detector.get_cycle_report())
