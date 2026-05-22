#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS->SQLite 代码知识图谱系统 (Logged Version)
基于第一性原理设计：将代码视为实体-关系系统，实现极简、高效、零成本的代码知识图谱

版本: v4.2-LOGGED
核心特性:
1. 逐行日志输出 - 每句代码后都有详细日志
2. 统一的日志格式，包含行号、函数名、操作类型
3. 完整的执行路径追踪

日志格式:
- [LINE {lineno}] 进入函数 {func_name}
- [LINE {lineno}] 变量 {var_name} = {value}
- [LINE {lineno}] 进入if分支: {condition}
- [LINE {lineno}] 进入for循环: {iterator}
- [LINE {lineno}] 异常捕获: {exception}
"""

import os
import re
import sqlite3
import json
import logging
import functools
import time
import inspect
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
# 日志配置 - 增强版
# ============================================================================

# 全局调试日志
_logger = logging.getLogger('arkts_kg')
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('[%(levelname)s %(funcName)s:%(lineno)d] %(message)s'))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG)  # 日志版本默认开启DEBUG

# 执行追踪日志
_trace_logger = logging.getLogger('arkts_kg_trace')
_trace_handler = logging.StreamHandler()
_trace_handler.setFormatter(logging.Formatter('%(message)s'))
_trace_logger.addHandler(_trace_handler)
_trace_logger.setLevel(logging.DEBUG)


def log_entry(func_name: str, lineno: int, **kwargs):
    """记录函数入口日志"""
    _trace_logger.debug(f"[LINE {lineno}] 进入函数 {func_name}")
    for key, value in kwargs.items():
        _trace_logger.debug(f"[LINE {lineno}] 参数 {key} = {value}")


def log_exit(func_name: str, lineno: int, return_value: Any = None):
    """记录函数出口日志"""
    if return_value is not None:
        _trace_logger.debug(f"[LINE {lineno}] 退出函数 {func_name}, 返回值 = {return_value}")
    else:
        _trace_logger.debug(f"[LINE {lineno}] 退出函数 {func_name}")


def log_var(var_name: str, value: Any, lineno: int):
    """记录变量值"""
    # 限制输出长度
    val_str = str(value)
    if len(val_str) > 100:
        val_str = val_str[:100] + '...'
    _trace_logger.debug(f"[LINE {lineno}] 变量 {var_name} = {val_str}")


def log_if(condition: str, result: bool, lineno: int):
    """记录if分支"""
    _trace_logger.debug(f"[LINE {lineno}] 进入if分支: {condition} = {result}")


def log_for(iterator: str, lineno: int):
    """记录for循环"""
    _trace_logger.debug(f"[LINE {lineno}] 进入for循环: {iterator}")


def log_while(condition: str, lineno: int):
    """记录while循环"""
    _trace_logger.debug(f"[LINE {lineno}] 进入while循环: {condition}")


def log_try(lineno: int):
    """记录try块"""
    _trace_logger.debug(f"[LINE {lineno}] 进入try块")


def log_except(exception: str, lineno: int):
    """记录except捕获"""
    _trace_logger.debug(f"[LINE {lineno}] 异常捕获: {exception}")


def log_call(caller: str, callee: str, lineno: int):
    """记录函数调用"""
    _trace_logger.debug(f"[LINE {lineno}] 调用: {caller} -> {callee}")


# ============================================================================
# 错误恢复装饰器 - 带日志
# ============================================================================

def error_recovery(default_return: Any = None, log_level: int = logging.ERROR):
    """
    错误恢复装饰器 - 带详细日志
    
    遇到异常时记录错误并返回默认值，不中断整个解析流程
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            lineno = inspect.currentframe().f_lineno
            log_entry(func_name, lineno)
            try:
                result = func(*args, **kwargs)
                log_exit(func_name, lineno, result)
                return result
            except Exception as e:
                lineno = inspect.currentframe().f_lineno
                log_except(str(e), lineno)
                _logger.log(log_level, f"[错误恢复] 函数 '{func_name}' 执行失败: {str(e)}")
                log_exit(func_name, lineno, default_return)
                return default_return
        return wrapper
    return decorator


# ============================================================================
# 循环依赖检测器 - 带日志
# ============================================================================

class CircularDependencyDetector:
    """
    循环依赖检测器 - 带详细日志
    
    使用DFS算法检测继承关系中的循环依赖
    """
    
    def __init__(self):
        lineno = inspect.currentframe().f_lineno
        log_entry('CircularDependencyDetector.__init__', lineno)
        
        # 邻接表表示的图: {child: [parent1, parent2, ...]}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        # 所有节点
        self.nodes: Set[str] = set()
        
        lineno = inspect.currentframe().f_lineno
        log_var('graph', {}, lineno)
        log_var('nodes', set(), lineno)
        log_exit('CircularDependencyDetector.__init__', lineno)
    
    def add_edge(self, child: str, parent: str) -> None:
        """
        添加继承关系边
        """
        lineno = 122  # 对应原文件行号
        log_entry('add_edge', lineno, child=child, parent=parent)
        
        if child and parent and child != parent:
            self.graph[child].append(parent)
            self.nodes.add(child)
            self.nodes.add(parent)
            lineno = inspect.currentframe().f_lineno
            log_var('graph[child]', self.graph[child], lineno)
            _logger.debug(f"[循环依赖检测] 添加边: {child} -> {parent}")
        else:
            lineno = inspect.currentframe().f_lineno
            log_if('child and parent and child != parent', False, lineno)
        
        log_exit('add_edge', lineno)
    
    def add_edges_from_relations(self, inherits: List[Any]) -> None:
        """
        从继承关系列表批量添加边
        """
        lineno = 136
        log_entry('add_edges_from_relations', lineno, inherits_count=len(inherits))
        
        log_for(f"inherit in inherits (total {len(inherits)})", lineno)
        for inherit in inherits:
            self.add_edge(inherit.child_class, inherit.parent_class)
        
        log_exit('add_edges_from_relations', lineno)
    
    def detect_cycles(self) -> List[List[str]]:
        """
        使用DFS检测所有循环依赖
        """
        lineno = 146
        log_entry('detect_cycles', lineno)
        
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        lineno = inspect.currentframe().f_lineno
        log_var('cycles', cycles, lineno)
        log_var('visited', visited, lineno)
        log_var('rec_stack', rec_stack, lineno)
        
        def dfs(node: str) -> None:
            dfs_lineno = 158
            log_entry('dfs', dfs_lineno, node=node)
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            dfs_lineno = inspect.currentframe().f_lineno
            log_var('visited', visited, dfs_lineno)
            log_var('path', path, dfs_lineno)
            
            log_for(f"neighbor in graph.get('{node}', [])", dfs_lineno)
            for neighbor in self.graph.get(node, []):
                log_if('neighbor not in visited', neighbor not in visited, dfs_lineno)
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
            
            dfs_lineno = inspect.currentframe().f_lineno
            log_var('path_after_pop', path, dfs_lineno)
            log_exit('dfs', dfs_lineno)
        
        log_for(f"node in nodes (total {len(self.nodes)})", lineno)
        for node in self.nodes:
            log_if('node not in visited', node not in visited, lineno)
            if node not in visited:
                dfs(node)
        
        lineno = inspect.currentframe().f_lineno
        log_var('cycles_result', cycles, lineno)
        log_exit('detect_cycles', lineno, cycles)
        return cycles
    
    def has_cycle(self) -> bool:
        """
        检查是否存在循环依赖
        """
        lineno = 182
        log_entry('has_cycle', lineno)
        
        cycles = self.detect_cycles()
        result = len(cycles) > 0
        
        lineno = inspect.currentframe().f_lineno
        log_var('has_cycle_result', result, lineno)
        log_exit('has_cycle', lineno, result)
        return result
    
    def get_cycle_report(self) -> str:
        """
        生成循环依赖报告
        """
        lineno = 191
        log_entry('get_cycle_report', lineno)
        
        cycles = self.detect_cycles()
        if not cycles:
            log_exit('get_cycle_report', lineno, "未发现循环依赖")
            return "未发现循环依赖"
        
        report = ["=" * 60, "循环依赖检测报告", "=" * 60]
        report.append(f"\n发现 {len(cycles)} 个循环依赖:\n")
        
        log_for(f"cycle in cycles (total {len(cycles)})", lineno)
        for i, cycle in enumerate(cycles, 1):
            report.append(f"  {i}. {' -> '.join(cycle)}")
        
        report.append("\n" + "=" * 60)
        result = "\n".join(report)
        
        log_exit('get_cycle_report', lineno, result[:100] + '...')
        return result


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
# 数据库管理 - 带日志
# ============================================================================

class DatabaseManager:
    """
    SQLite数据库管理器 (Logged Version)
    
    修复内容:
    1. 外键约束问题 - 自动插入文件记录
    2. 性能优化 - 支持批量插入和事务
    3. 详细日志输出
    """
    
    def __init__(self, db_path: str = "code.db"):
        lineno = 285
        log_entry('DatabaseManager.__init__', lineno, db_path=db_path)
        
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
        
        lineno = inspect.currentframe().f_lineno
        log_var('_batch_size', self._batch_size, lineno)
        log_exit('DatabaseManager.__init__', lineno)
    
    def connect(self):
        """连接数据库"""
        lineno = 301
        log_entry('DatabaseManager.connect', lineno)
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        log_var('conn', 'sqlite3.Connection', lineno)
        
        # 预加载文件缓存
        self._load_file_cache()
        
        log_exit('DatabaseManager.connect', lineno)
    
    def _load_file_cache(self):
        """加载已有文件到缓存"""
        lineno = 308
        log_entry('_load_file_cache', lineno)
        
        log_try(lineno)
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT path FROM files")
            self._file_cache = {row[0] for row in cursor.fetchall()}
            lineno = inspect.currentframe().f_lineno
            log_var('_file_cache_size', len(self._file_cache), lineno)
            _logger.debug(f"[数据库] 已加载 {len(self._file_cache)} 个文件到缓存")
        except sqlite3.OperationalError:
            lineno = inspect.currentframe().f_lineno
            log_except('sqlite3.OperationalError', lineno)
            # 表不存在，缓存为空
            self._file_cache = set()
            _logger.debug("[数据库] 文件表不存在，缓存为空")
        
        log_exit('_load_file_cache', lineno)
    
    def close(self):
        """关闭数据库连接"""
        lineno = 320
        log_entry('DatabaseManager.close', lineno)
        
        # 刷新剩余批量数据
        self._flush_all_batches()
        if self.conn:
            self.conn.close()
            log_var('conn', 'closed', lineno)
        
        log_exit('DatabaseManager.close', lineno)
    
    def create_tables(self):
        """创建数据库表结构"""
        lineno = 327
        log_entry('DatabaseManager.create_tables', lineno)
        
        cursor = self.conn.cursor()
        
        # 实体表
        log_var('creating_table', 'files', lineno)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                line_count INTEGER DEFAULT 0
            )
        """)
        
        log_var('creating_table', 'classes', lineno)
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
        
        log_var('creating_table', 'methods', lineno)
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
        log_var('creating_table', 'calls', lineno)
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
        
        log_var('creating_table', 'components', lineno)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                parent TEXT NOT NULL,
                child TEXT NOT NULL,
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (parent, child, file)
            )
        """)
        
        log_var('creating_table', 'inherits', lineno)
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
        log_var('creating_index', 'idx_classes_file', lineno)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_child ON components(child)")
        
        self.conn.commit()
        log_exit('DatabaseManager.create_tables', lineno)
    
    def clear_tables(self):
        """清空所有表数据"""
        lineno = 407
        log_entry('DatabaseManager.clear_tables', lineno)
        
        cursor = self.conn.cursor()
        tables = ['calls', 'components', 'inherits', 'methods', 'classes', 'files']
        log_for(f"table in tables (total {len(tables)})", lineno)
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()
        
        # 清空缓存
        self._file_cache.clear()
        for key in self._batch_buffer:
            self._batch_buffer[key].clear()
        
        log_exit('DatabaseManager.clear_tables', lineno)
    
    def _ensure_file_exists(self, file_path: str, immediate: bool = False):
        """
        确保文件记录存在，不存在则自动插入
        """
        lineno = 419
        log_entry('_ensure_file_exists', lineno, file_path=file_path, immediate=immediate)
        
        log_if('file_path not in _file_cache', file_path not in self._file_cache, lineno)
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
        
        log_exit('_ensure_file_exists', lineno)
    
    def insert_file(self, file_info: FileInfo):
        """插入文件记录"""
        lineno = 440
        log_entry('insert_file', lineno, path=file_info.path)
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO files (path) VALUES (?)",
            (file_info.path,)
        )
        self._file_cache.add(file_info.path)
        
        log_exit('insert_file', lineno)
    
    def insert_class(self, class_info: ClassInfo):
        """
        插入类/组件记录 (修复版)
        """
        lineno = 449
        log_entry('insert_class', lineno, name=class_info.name, file=class_info.file)
        
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
        
        log_exit('insert_class', lineno)
    
    def insert_method(self, method_info: MethodInfo):
        """
        插入方法记录 (修复版)
        """
        lineno = 468
        log_entry('insert_method', lineno, name=method_info.name, class_name=method_info.class_name)
        
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
        
        log_exit('insert_method', lineno)
    
    def insert_call(self, call: CallRelation):
        """插入调用关系"""
        lineno = 487
        log_entry('insert_call', lineno, caller=call.caller, callee=call.callee)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO calls 
               (caller, caller_class, callee, callee_class, file, line_number) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (call.caller, call.caller_class, call.callee, call.callee_class,
             call.file, call.line_number)
        )
        
        log_exit('insert_call', lineno)
    
    def insert_component_relation(self, comp: ComponentRelation):
        """插入组件嵌套关系"""
        lineno = 498
        log_entry('insert_component_relation', lineno, parent=comp.parent, child=comp.child)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO components 
               (parent, child, file, line_number) 
               VALUES (?, ?, ?, ?)""",
            (comp.parent, comp.child, comp.file, comp.line_number)
        )
        
        log_exit('insert_component_relation', lineno)
    
    def insert_inherit(self, inherit: InheritRelation):
        """插入继承关系"""
        lineno = 508
        log_entry('insert_inherit', lineno, child=inherit.child_class, parent=inherit.parent_class)
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO inherits 
               (child_class, parent_class, file, line_number) 
               VALUES (?, ?, ?, ?)""",
            (inherit.child_class, inherit.parent_class, inherit.file, inherit.line_number)
        )
        
        log_exit('insert_inherit', lineno)
    
    # ========== 批量插入方法 (性能优化) ==========
    
    def batch_insert_file(self, file_info: FileInfo):
        """批量插入文件记录"""
        lineno = 520
        log_entry('batch_insert_file', lineno, path=file_info.path)
        
        log_if('file_info.path not in _file_cache', file_info.path not in self._file_cache, lineno)
        if file_info.path not in self._file_cache:
            self._batch_buffer['files'].append((file_info.path,))
            self._file_cache.add(file_info.path)
            self._check_batch('files')
        
        log_exit('batch_insert_file', lineno)
    
    def batch_insert_class(self, class_info: ClassInfo):
        """批量插入类记录"""
        lineno = 527
        log_entry('batch_insert_class', lineno, name=class_info.name)
        
        self._ensure_file_exists(class_info.file, immediate=True)
        self._batch_buffer['classes'].append((
            class_info.name, class_info.file,
            int(class_info.is_component), int(class_info.is_entry),
            class_info.line_number
        ))
        self._check_batch('classes')
        
        log_exit('batch_insert_class', lineno)
    
    def batch_insert_method(self, method_info: MethodInfo):
        """批量插入方法记录"""
        lineno = 537
        log_entry('batch_insert_method', lineno, name=method_info.name)
        
        self._ensure_file_exists(method_info.file, immediate=True)
        self._batch_buffer['methods'].append((
            method_info.name, method_info.class_name, method_info.file,
            method_info.line_number, int(method_info.is_static or False),
            int(method_info.is_private or False)
        ))
        self._check_batch('methods')
        
        log_exit('batch_insert_method', lineno)
    
    def batch_insert_call(self, call: CallRelation):
        """批量插入调用关系"""
        lineno = 547
        log_entry('batch_insert_call', lineno, caller=call.caller, callee=call.callee)
        
        self._batch_buffer['calls'].append((
            call.caller, call.caller_class, call.callee, call.callee_class,
            call.file, call.line_number
        ))
        self._check_batch('calls')
        
        log_exit('batch_insert_call', lineno)
    
    def batch_insert_component(self, comp: ComponentRelation):
        """批量插入组件关系"""
        lineno = 555
        log_entry('batch_insert_component', lineno, parent=comp.parent, child=comp.child)
        
        self._batch_buffer['components'].append((
            comp.parent, comp.child, comp.file, comp.line_number
        ))
        self._check_batch('components')
        
        log_exit('batch_insert_component', lineno)
    
    def batch_insert_inherit(self, inherit: InheritRelation):
        """批量插入继承关系"""
        lineno = 562
        log_entry('batch_insert_inherit', lineno, child=inherit.child_class)
        
        self._batch_buffer['inherits'].append((
            inherit.child_class, inherit.parent_class, inherit.file, inherit.line_number
        ))
        self._check_batch('inherits')
        
        log_exit('batch_insert_inherit', lineno)
    
    def _check_batch(self, table: str):
        """检查是否需要刷新批量缓冲区"""
        lineno = 569
        log_entry('_check_batch', lineno, table=table)
        
        buffer_len = len(self._batch_buffer[table])
        log_if(f'len(_batch_buffer[table]) >= _batch_size ({buffer_len} >= {self._batch_size})',
               buffer_len >= self._batch_size, lineno)
        
        if buffer_len >= self._batch_size:
            self._flush_batch(table)
        
        log_exit('_check_batch', lineno)
    
    def _flush_batch(self, table: str):
        """刷新指定表的批量缓冲区"""
        lineno = 574
        log_entry('_flush_batch', lineno, table=table)
        
        log_if('not _batch_buffer[table]', not self._batch_buffer[table], lineno)
        if not self._batch_buffer[table]:
            log_exit('_flush_batch', lineno)
            return
        
        cursor = self.conn.cursor()
        
        log_var('table', table, lineno)
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
        
        log_exit('_flush_batch', lineno)
    
    def _flush_all_batches(self):
        """刷新所有批量缓冲区"""
        lineno = 626
        log_entry('_flush_all_batches', lineno)
        
        log_for(f"table in _batch_buffer (total {len(self._batch_buffer)})", lineno)
        for table in self._batch_buffer:
            self._flush_batch(table)
        
        log_exit('_flush_all_batches', lineno)
    
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
        lineno = 675
        log_entry('execute_query', lineno, sql=sql[:50] + '...')
        
        cursor = self.conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        
        lineno = inspect.currentframe().f_lineno
        log_var('result_count', len(result), lineno)
        log_exit('execute_query', lineno)
        return result
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        lineno = 681
        log_entry('get_statistics', lineno)
        
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
        
        lineno = inspect.currentframe().f_lineno
        log_var('stats', stats, lineno)
        log_exit('get_statistics', lineno, stats)
        return stats


# ============================================================================
# ArkTS代码解析器 - 带日志
# ============================================================================

# Unicode标识符模式（支持中文、日文、韩文、$符号）
_ID_PATTERN = r'[\w$\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]+'


class ArkTSParser:
    """
    ArkTS代码静态解析器 V4 (Logged Version)
    
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
        lineno = 836
        log_entry('ArkTSParser.__init__', lineno)
        
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
        
        lineno = inspect.currentframe().f_lineno
        log_var('files_count', len(self.files), lineno)
        log_var('classes_count', len(self.classes), lineno)
        log_exit('ArkTSParser.__init__', lineno)
    
    def _init_regex_patterns(self):
        """初始化并缓存所有正则表达式"""
        lineno = 852
        log_entry('_init_regex_patterns', lineno)
        
        # 装饰器正则（支持嵌套括号如 @StorageLink(StorageKeys.THEME)）
        self.decorator_pattern = re.compile(r'@\w+\s*\([^()]*\)')
        # 组件装饰器
        self.component_decorator = re.compile(r'@(?:Component|CustomDialog|Reusable)\s*(?:\([^()]*\))?\s*')
        self.entry_decorator = re.compile(r'@Entry\s*(?:\([^()]*\))?\s*')

        # struct正则
        self.struct_pattern = re.compile(
            r'(export\s+)?(default\s+)?struct\s+(' + _ID_PATTERN + r')\s*(?:<[^>]*>)?\s*(?:extends\s+(' + _ID_PATTERN + r'))?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # class正则
        self.class_pattern = re.compile(
            r'(export\s+)?(default\s+)?(abstract\s+)?class\s+(' + _ID_PATTERN + r')\s*(?:<[^>]*>)?\s*(?:extends\s+(\w+)(?:\s*<[^>]*>)?)?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # method正则
        self.method_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(async\s+)?(abstract\s+|override\s+)?(' + _ID_PATTERN + r')\s*(?:<[^>]*>\s*)?\(',
            re.MULTILINE
        )

        # 装饰器行移除正则
        self.decorator_line_pattern = re.compile(
            r'^([ \t]*)@\w+[ \t]*\([^()]*\)[ \t]*',
            re.MULTILINE
        )
        self.decorator_line_noarg_pattern = re.compile(
            r'^([ \t]*)@\w+[ \t]+',
            re.MULTILINE
        )

        # 箭头函数正则
        self.arrow_property_pattern = re.compile(
            r'^[ \t]*'
            r'(?:(private|public|protected)\s+)?'
            r'(?:(static)\s+)?'
            r'(?:(readonly)\s+)?'
            r'(' + _ID_PATTERN + r')'
            r'\s*'
            r'(?:<[^>]*>)?'
            r'\s*'
            r'=\s*'
            r'(?:\([^)]*\)|\w+)'
            r'\s*'
            r'(?:<[^>]*>)?'
            r'\s*'
            r'=>',
            re.MULTILINE
        )
        
        # 简化的箭头函数模式
        self.arrow_simple_pattern = re.compile(
            r'^[ \t]*'
            r'(?:(private|public|protected)\s+)?'
            r'(?:(static)\s+)?'
            r'(' + _ID_PATTERN + r')'
            r'\s*=\s*\(',
            re.MULTILINE
        )

        # call正则
        self.call_pattern = re.compile(
            r'(?:(\w+)\s*\.\s*)?(\w+)\s*(?:<[^{;]*?>\s*)?\(',
            re.MULTILINE
        )

        # import正则
        self.import_pattern = re.compile(
            r'import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
            re.MULTILINE
        )

        # 顶层函数正则
        self.top_func_pattern = re.compile(
            r'(export\s+)?(async\s+)?function\s+(' + _ID_PATTERN + r')\s*(?:<[^{]*?>\s*)?\(',
            re.MULTILINE
        )
        
        log_exit('_init_regex_patterns', lineno)

    @error_recovery(default_return="")
    def _strip_comments_and_strings(self, content: str) -> str:
        """移除注释和字符串，保留换行符"""
        lineno = 946
        log_entry('_strip_comments_and_strings', lineno, content_len=len(content))
        
        result = []
        i = 0
        n = len(content)
        log_var('content_length', n, lineno)
        
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
            # 模板字符串
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
        
        result_str = ''.join(result)
        log_var('result_length', len(result_str), lineno)
        log_exit('_strip_comments_and_strings', lineno)
        return result_str

    @error_recovery(default_return=-1)
    def _find_matching_brace(self, stripped: str, start: int) -> int:
        """在stripped内容中找到匹配的}"""
        lineno = 1007
        log_entry('_find_matching_brace', lineno, start=start)
        
        brace_count = 0
        i = start
        while i < len(stripped):
            if stripped[i] == '{':
                brace_count += 1
            elif stripped[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    log_exit('_find_matching_brace', lineno, i)
                    return i
            i += 1
        
        result = len(stripped) - 1
        log_exit('_find_matching_brace', lineno, result)
        return result

    @error_recovery(default_return={
        'files': [], 'classes': [], 'methods': [],
        'calls': [], 'component_relations': [], 'inherits': []
    })
    def parse_project(self, project_path: str) -> Dict:
        """解析整个项目 - 两遍解析"""
        lineno = 1022
        log_entry('parse_project', lineno, project_path=project_path)
        
        project_path = Path(project_path)
        log_var('project_path', str(project_path), lineno)

        if not project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {project_path}")

        arkts_files = list(project_path.rglob("*.ets")) + \
                      list(project_path.rglob("*.ts"))

        print(f"找到 {len(arkts_files)} 个ArkTS文件")
        _logger.info(f"开始解析项目: {project_path}, 共 {len(arkts_files)} 个文件")
        log_var('arkts_files_count', len(arkts_files), lineno)

        # 第一遍：收集所有类/组件名
        log_for(f"file_path in arkts_files (total {len(arkts_files)})", lineno)
        for file_path in arkts_files:
            log_if("'node_modules' not in str(file_path)", 'node_modules' not in str(file_path), lineno)
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            self._scan_declarations(str(file_path))

        # 第二遍：完整解析
        log_for(f"file_path in arkts_files - full parse", lineno)
        for file_path in arkts_files:
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            self._full_parse(str(file_path))

        # 后处理
        log_var('before_resolve_callee_classes', 'calls count: ' + str(len(self.calls)), lineno)
        self._resolve_callee_classes()
        self._extract_component_relations()

        result = self._get_result()
        log_exit('parse_project', lineno)
        return result

    @error_recovery()
    def _scan_declarations(self, file_path: str):
        """第一遍：只收集类/组件声明"""
        lineno = 1057
        log_entry('_scan_declarations', lineno, file_path=file_path)
        
        log_try(lineno)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            log_except(str(e), lineno)
            _logger.warning(f"[扫描] 无法读取文件 {file_path}: {e}")
            log_exit('_scan_declarations', lineno)
            return

        self.files.append(FileInfo(path=file_path))
        stripped = self._strip_comments_and_strings(content)
        _logger.debug(f"[SCAN] {file_path}: stripped {len(content)} -> {len(stripped)} chars")

        log_for(f"match in struct_pattern.finditer", lineno)
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

        log_for(f"match in class_pattern.finditer", lineno)
        for match in self.class_pattern.finditer(stripped):
            name = match.group(4)
            self._all_class_names.add(name)
            _logger.debug(f"[SCAN] class '{name}' declared at line {content[:match.start()].count(chr(10))+1}")
        
        log_exit('_scan_declarations', lineno)

    @error_recovery()
    def _full_parse(self, file_path: str):
        """第二遍：完整解析"""
        lineno = 1087
        log_entry('_full_parse', lineno, file_path=file_path)
        
        log_try(lineno)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            log_except(str(e), lineno)
            _logger.warning(f"[解析] 无法读取文件 {file_path}: {e}")
            log_exit('_full_parse', lineno)
            return

        stripped = self._strip_comments_and_strings(content)
        _logger.debug(f"[PARSE] {file_path}: starting full parse")

        # struct
        log_for(f"match in struct_pattern.finditer", lineno)
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
            log_if('parent_class and parent_class not in JS_KEYWORDS', 
                   parent_class and parent_class not in self.JS_KEYWORDS, lineno)
            if parent_class and parent_class not in self.JS_KEYWORDS:
                self.inherits.append(InheritRelation(
                    child_class=name, parent_class=parent_class,
                    file=file_path, line_number=line_number
                ))
                _logger.debug(f"[PARSE] struct '{name}' extends '{parent_class}'")

            # 提取struct的implements接口关系
            implements_str = match.group(5)
            log_if('implements_str', bool(implements_str), lineno)
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
        log_for(f"match in class_pattern.finditer", lineno)
        for match in self.class_pattern.finditer(stripped):
            name = match.group(4)
            parent = match.group(5)
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1

            log_if("any(c.name == name and c.file == file_path for c in classes)",
                   any(c.name == name and c.file == file_path for c in self.classes), lineno)
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

            log_if('parent', bool(parent), lineno)
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
        log_exit('_full_parse', lineno)

    def _extract_body(self, stripped: str, open_brace: int) -> str:
        """在stripped上提取类体"""
        lineno = 1186
        log_entry('_extract_body', lineno, open_brace=open_brace)
        
        close = self._find_matching_brace(stripped, open_brace)
        result = stripped[open_brace:close + 1]
        
        log_var('body_length', len(result), lineno)
        log_exit('_extract_body', lineno)
        return result

    @error_recovery()
    def _parse_methods(self, body_stripped: str, class_name: str, file_path: str,
                       class_line: int):
        """
        在stripped类体上解析方法（包括箭头函数属性）
        """
        lineno = 1191
        log_entry('_parse_methods', lineno, class_name=class_name, class_line=class_line)
        
        # 在类方法上下文中，以下关键字是合法的方法名
        METHOD_SAFE_KEYWORDS = {'get', 'set', 'delete', 'has', 'of'}
        # ArkTS组件生命周期方法
        ARKTS_LIFECYCLE = frozenset({
            'aboutToAppear', 'aboutToDisappear', 'aboutToRecycle', 'aboutToReuse',
            'onPageShow', 'onPageHide', 'onBackPress', 'onQuery',
            'onWindowStageCreate', 'onWindowStageDestroy',
            'onForeground', 'onBackground',
            'onDidBuild', 'onSizeChange', 'onAreaChange',
        })

        # 预处理：移除装饰器
        body_no_dec = self.decorator_line_pattern.sub(r'\1', body_stripped)
        body_no_dec = self.decorator_line_noarg_pattern.sub(r'\1', body_no_dec)
        
        # 计算每个位置的花括号深度
        brace_depth = 0
        depth_at_pos = {}
        log_for(f"idx, ch in enumerate(body_no_dec)", lineno)
        for idx, ch in enumerate(body_no_dec):
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            depth_at_pos[idx] = brace_depth
        
        # 收集所有已匹配的位置，避免箭头函数属性和普通方法重复
        matched_positions = set()

        # 1. 匹配普通方法
        log_for(f"match in method_pattern.finditer", lineno)
        for match in self.method_pattern.finditer(body_no_dec):
            method_name = match.group(5)

            # 只匹配类体顶层的方法定义（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            log_if('match_depth == 1', match_depth == 1, lineno)
            if match_depth != 1:
                continue

            # 增强过滤逻辑
            log_if('is_valid_method_name', self._is_valid_method_name(method_name, class_name, METHOD_SAFE_KEYWORDS, ARKTS_LIFECYCLE), lineno)
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
            log_if('is_abstract', is_abstract, lineno)
            if is_abstract:
                continue

            # 提取方法体
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
            log_if('brace_pos != -1', brace_pos != -1, lineno)
            if brace_pos == -1:
                _logger.debug(f"[METHOD] '{class_name}.{method_name}' -> no body found (brace_pos=-1)")
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            _logger.debug(f"[METHOD] '{class_name}.{method_name}' body: {len(method_body_stripped)} chars")
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

        # 2. 匹配箭头函数属性
        self._parse_arrow_functions(
            body_no_dec, depth_at_pos, matched_positions,
            class_name, file_path, class_line,
            METHOD_SAFE_KEYWORDS, ARKTS_LIFECYCLE
        )
        log_exit('_parse_methods', lineno)

    def _is_valid_method_name(self, method_name: str, class_name: str,
                              safe_keywords: Set[str], lifecycle: Set[str]) -> bool:
        """
        检查方法名是否有效
        """
        lineno = 1282
        log_entry('_is_valid_method_name', lineno, method_name=method_name)
        
        # 跳过: JS_KEYWORDS, ARKTS_KEYWORDS (但保留安全关键字)
        log_if('method_name in JS_KEYWORDS or method_name in ARKTS_KEYWORDS',
               method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS, lineno)
        if method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS:
            if method_name not in safe_keywords:
                log_exit('_is_valid_method_name', lineno, False)
                return False
        
        # 跳过 constructor
        log_if('method_name == constructor', method_name == 'constructor', lineno)
        if method_name == 'constructor':
            log_exit('_is_valid_method_name', lineno, False)
            return False
        
        # 跳过 UI_COMPONENTS
        log_if('method_name in UI_COMPONENTS', method_name in self.UI_COMPONENTS, lineno)
        if method_name in self.UI_COMPONENTS:
            log_exit('_is_valid_method_name', lineno, False)
            return False
        
        # 跳过 UI_CHAIN_PROPERTIES（但保留生命周期方法）
        log_if('method_name in UI_CHAIN_PROPERTIES and method_name not in lifecycle',
               method_name in self.UI_CHAIN_PROPERTIES and method_name not in lifecycle, lineno)
        if method_name in self.UI_CHAIN_PROPERTIES and method_name not in lifecycle:
            log_exit('_is_valid_method_name', lineno, False)
            return False
        
        # 跳过已知组件名
        log_if('method_name in _component_names and method_name != class_name',
               method_name in self._component_names and method_name != class_name, lineno)
        if method_name in self._component_names and method_name != class_name:
            log_exit('_is_valid_method_name', lineno, False)
            return False
        
        # 跳过已知类名
        log_if('method_name in _all_class_names and method_name != class_name',
               method_name in self._all_class_names and method_name != class_name, lineno)
        if method_name in self._all_class_names and method_name != class_name:
            log_exit('_is_valid_method_name', lineno, False)
            return False
        
        log_exit('_is_valid_method_name', lineno, True)
        return True

    def _parse_arrow_functions(self, body_no_dec: str, depth_at_pos: Dict[int, int],
                               matched_positions: Set[int], class_name: str,
                               file_path: str, class_line: int,
                               safe_keywords: Set[str], lifecycle: Set[str]):
        """
        解析箭头函数属性
        """
        lineno = 1316
        log_entry('_parse_arrow_functions', lineno, class_name=class_name)
        
        # 使用增强的正则表达式匹配箭头函数
        log_for(f"match in arrow_property_pattern.finditer", lineno)
        for match in self.arrow_property_pattern.finditer(body_no_dec):
            # 跳过已匹配的位置
            log_if('match.start() in matched_positions', match.start() in matched_positions, lineno)
            if match.start() in matched_positions:
                continue

            # 获取属性名
            method_name = match.group(4)
            log_if('method_name', bool(method_name), lineno)
            if not method_name:
                continue

            # 只匹配类体顶层（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            log_if('match_depth == 1', match_depth == 1, lineno)
            if match_depth != 1:
                continue

            # 检查是否为有效方法名
            log_if('is_valid_method_name', self._is_valid_method_name(method_name, class_name, safe_keywords, lifecycle), lineno)
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
            arrow_match = re.search(r'=>\s*\{', body_no_dec[match.start():match.end() + 200])
            log_if('arrow_match', bool(arrow_match), lineno)
            if arrow_match:
                brace_pos = match.start() + arrow_match.start() + arrow_match.group().index('{')
                close_pos = self._find_matching_brace(body_no_dec, brace_pos)
                method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
                self._parse_calls(method_body_stripped, method_name, class_name,
                                  file_path, line_number)

        # 使用简化正则作为备选
        log_for(f"match in arrow_simple_pattern.finditer", lineno)
        for match in self.arrow_simple_pattern.finditer(body_no_dec):
            log_if('match.start() in matched_positions', match.start() in matched_positions, lineno)
            if match.start() in matched_positions:
                continue

            method_name = match.group(3)
            log_if('method_name', bool(method_name), lineno)
            if not method_name:
                continue

            match_depth = depth_at_pos.get(match.start(), 0)
            log_if('match_depth == 1', match_depth == 1, lineno)
            if match_depth != 1:
                continue

            log_if('is_valid_method_name', self._is_valid_method_name(method_name, class_name, safe_keywords, lifecycle), lineno)
            if not self._is_valid_method_name(method_name, class_name, safe_keywords, lifecycle):
                continue

            # 检查是否已被第一个正则匹配
            already_matched = False
            log_for(f"pos in matched_positions", lineno)
            for pos in matched_positions:
                if abs(pos - match.start()) < 10:  # 接近的位置
                    already_matched = True
                    break
            log_if('already_matched', already_matched, lineno)
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
            log_if('brace_pos != -1', brace_pos != -1, lineno)
            if brace_pos == -1:
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)
        
        log_exit('_parse_arrow_functions', lineno)

    @error_recovery(default_return=-1)
    def _skip_params_and_return_type(self, stripped: str, paren_pos: int) -> int:
        """跳过参数列表和返回类型，返回方法体{的位置"""
        lineno = 1413
        log_entry('_skip_params_and_return_type', lineno, paren_pos=paren_pos)
        
        i = paren_pos
        n = len(stripped)
        log_var('stripped_length', n, lineno)

        # 括号匹配跳过参数
        paren_count = 0
        log_while(f"i < n ({i} < {n})", lineno)
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
        log_while(f"stripped[i] in ' \\t\\n\\r'", lineno)
        while i < n and stripped[i] in ' \t\n\r':
            i += 1

        log_if('i >= n', i >= n, lineno)
        if i >= n:
            log_exit('_skip_params_and_return_type', lineno, -1)
            return -1

        # 如果遇到':'，跳过返回类型
        log_if('stripped[i] == :', stripped[i] == ':', lineno)
        if stripped[i] == ':':
            i += 1
            angle_count = 0
            brace_count = 0
            log_while(f"i < n", lineno)
            while i < n:
                if stripped[i] == '<':
                    angle_count += 1
                elif stripped[i] == '>':
                    angle_count -= 1
                elif stripped[i] == '{' and angle_count <= 0:
                    if brace_count == 0:
                        log_exit('_skip_params_and_return_type', lineno, i)
                        return i
                    brace_count += 1
                elif stripped[i] == '}' and angle_count <= 0:
                    brace_count -= 1
                elif stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
                    break
                elif stripped[i] == ';' and angle_count <= 0 and brace_count == 0:
                    log_exit('_skip_params_and_return_type', lineno, -1)
                    return -1
                i += 1

        log_if('i >= n', i >= n, lineno)
        if i >= n:
            log_exit('_skip_params_and_return_type', lineno, -1)
            return -1

        # 如果遇到'=>'，跳过到'{'或表达式结束
        log_if('stripped[i] == = and i+1 < n and stripped[i+1] == >',
               stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>', lineno)
        if stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
            i += 2
            log_while(f"stripped[i] in ' \\t\\n\\r'", lineno)
            while i < n and stripped[i] in ' \t\n\r':
                i += 1
            log_if('stripped[i] == {', stripped[i] == '{', lineno)
            if i < n and stripped[i] == '{':
                log_exit('_skip_params_and_return_type', lineno, i)
                return i
            else:
                # 箭头函数表达式体，没有花括号方法体
                log_exit('_skip_params_and_return_type', lineno, -1)
                return -1

        # 普通方法体
        log_if('stripped[i] == {', stripped[i] == '{', lineno)
        if stripped[i] == '{':
            log_exit('_skip_params_and_return_type', lineno, i)
            return i

        log_exit('_skip_params_and_return_type', lineno, -1)
        return -1

    @error_recovery()
    def _parse_calls(self, method_body_stripped: str, method_name: str,
                     class_name: str, file_path: str, line_number: int):
        """在stripped方法体上解析调用关系"""
        lineno = 1480
        log_entry('_parse_calls', lineno, method_name=method_name, class_name=class_name)
        
        log_if('method_body_stripped', bool(method_body_stripped), lineno)
        if not method_body_stripped:
            log_exit('_parse_calls', lineno)
            return

        log_for(f"match in call_pattern.finditer", lineno)
        for match in self.call_pattern.finditer(method_body_stripped):
            obj_name = match.group(1)  # 可能是None
            callee = match.group(2)

            # 跳过SKIP_IDENTIFIERS
            log_if('callee in SKIP_IDENTIFIERS', callee in self.SKIP_IDENTIFIERS, lineno)
            if callee in self.SKIP_IDENTIFIERS:
                # 如果是 obj.method() 形式，保留常见方法名
                if obj_name and callee in {'get', 'set', 'delete', 'has', 'of', 'entries', 'keys', 'values', 'forEach', 'map', 'filter', 'reduce', 'find', 'some', 'every', 'includes', 'indexOf', 'slice', 'splice', 'push', 'pop', 'shift', 'unshift', 'join', 'split', 'trim', 'toString', 'toFixed', 'stringify', 'parse', 'json', 'then', 'catch', 'finally', 'next', 'done', 'value', 'ok', 'status', 'length', 'count', 'round', 'min', 'max', 'abs', 'floor', 'ceil', 'random', 'sort', 'reverse', 'concat', 'flat', 'fill', 'copyWithin', 'entries'}:
                    pass  # 保留
                else:
                    continue

            # 跳过数字开头的obj_name
            log_if('obj_name and re.match(r"^\d", obj_name)',
                   obj_name and re.match(r'^\d', obj_name), lineno)
            if obj_name and re.match(r'^\d', obj_name):
                continue

            # 跳过单字母变量
            log_if('obj_name and len(obj_name) == 1 and obj_name.islower()',
                   obj_name and len(obj_name) == 1 and obj_name.islower(), lineno)
            if obj_name and len(obj_name) == 1 and obj_name.islower():
                continue

            # 行号
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
        
        log_exit('_parse_calls', lineno)

    @error_recovery()
    def _parse_top_level_functions(self, stripped: str, content: str, file_path: str):
        """解析顶层函数"""
        lineno = 1520
        log_entry('_parse_top_level_functions', lineno, file_path=file_path)
        
        log_for(f"match in top_func_pattern.finditer", lineno)
        for match in self.top_func_pattern.finditer(stripped):
            func_name = match.group(3)
            line_number = content[:match.start()].count('\n') + 1
            self.methods.append(MethodInfo(
                name=func_name, class_name='',
                file=file_path, line_number=line_number
            ))
        
        log_exit('_parse_top_level_functions', lineno)

    @error_recovery()
    def _resolve_callee_classes(self):
        """后处理：推断callee_class"""
        lineno = 1531
        log_entry('_resolve_callee_classes', lineno)
        
        # 构建类→方法映射
        class_methods = {}
        log_for(f"cls in classes (total {len(self.classes)})", lineno)
        for cls in self.classes:
            methods = set()
            for m in self.methods:
                if m.class_name == cls.name:
                    methods.add(m.name)
            class_methods[cls.name] = methods
        
        # 提取成员变量类型
        member_types = self._extract_member_types()
        
        log_for(f"call in calls (total {len(self.calls)})", lineno)
        for call in self.calls:
            log_if('call.callee_class', bool(call.callee_class), lineno)
            if call.callee_class:
                # 已有推断，验证并优化
                log_if('callee_class not in _all_class_names',
                       call.callee_class not in self._all_class_names, lineno)
                if call.callee_class not in self._all_class_names:
                    # obj_name不是类名，尝试通过成员变量推断
                    resolved = member_types.get(call.caller_class, {}).get(call.callee_class, '')
                    log_if('resolved and resolved in _all_class_names',
                           resolved and resolved in self._all_class_names, lineno)
                    if resolved and resolved in self._all_class_names:
                        call.callee_class = resolved
                    elif not call.callee_class[0].isupper():
                        call.callee_class = ''
                continue

            # 规则1: callee本身是类名
            log_if('callee in _all_class_names', call.callee in self._all_class_names, lineno)
            if call.callee in self._all_class_names:
                call.callee_class = call.callee
                continue

            # 规则3: callee是当前类的已知方法 → 同类调用
            log_if('callee in class_methods.get(caller_class, set())',
                   call.callee in class_methods.get(call.caller_class, set()), lineno)
            if call.callee in class_methods.get(call.caller_class, set()):
                call.callee_class = call.caller_class
                continue
            
            # 规则4: callee是当前类的成员变量名 → 推断为变量类型
            var_type = member_types.get(call.caller_class, {}).get(call.callee, '')
            log_if('var_type and var_type in _all_class_names',
                   var_type and var_type in self._all_class_names, lineno)
            if var_type and var_type in self._all_class_names:
                call.callee_class = var_type
                continue
        
        log_exit('_resolve_callee_classes', lineno)
    
    @error_recovery(default_return={})
    def _extract_member_types(self) -> Dict[str, Dict[str, str]]:
        """从类体中提取成员变量的类型信息"""
        lineno = 1574
        log_entry('_extract_member_types', lineno)
        
        result = {}
        
        log_for(f"cls in classes (total {len(self.classes)})", lineno)
        for cls in self.classes:
            member_map = {}
            
            log_try(lineno)
            try:
                with open(cls.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                log_except('Exception', lineno)
                continue
            
            stripped = self._strip_comments_and_strings(content)
            
            member_pattern = re.compile(
                r'(private|public|protected)?\s*'
                r'(?:static\s+)?'
                r'(\w+)\s*:\s*(\w+)'
            )
            
            # 在struct和class中查找
            log_for(f"match in struct_pattern.finditer", lineno)
            for match in self.struct_pattern.finditer(stripped):
                if match.group(3) == cls.name:
                    body = self._extract_body(stripped, match.end() - 1)
                    self._scan_members_in_body(body, member_pattern, member_map)
                    break
            
            log_if('cls.name not in member_map', cls.name not in member_map, lineno)
            if cls.name not in member_map:
                log_for(f"match in class_pattern.finditer", lineno)
                for match in self.class_pattern.finditer(stripped):
                    if match.group(4) == cls.name:
                        body = self._extract_body(stripped, match.end() - 1)
                        self._scan_members_in_body(body, member_pattern, member_map)
                        break
            
            log_if('member_map', bool(member_map), lineno)
            if member_map:
                result[cls.name] = member_map
        
        log_exit('_extract_member_types', lineno, result)
        return result
    
    @error_recovery()
    def _scan_members_in_body(self, body: str, pattern, member_map: Dict):
        """在类体中扫描成员变量（只在花括号深度=1时）"""
        lineno = 1615
        log_entry('_scan_members_in_body', lineno)
        
        # 预计算每个位置的深度
        depths = []
        d = 0
        log_for(f"ch in body", lineno)
        for ch in body:
            if ch == '{': d += 1
            elif ch == '}': d -= 1
            depths.append(d)
        
        log_for(f"m in pattern.finditer(body)", lineno)
        for m in pattern.finditer(body):
            pos = m.start()
            log_if('depths[pos] == 1', depths[pos] == 1, lineno)
            if depths[pos] == 1:
                var_name = m.group(2)
                type_name = m.group(3)
                log_if('var_name not in JS_KEYWORDS and type_name not in JS_KEYWORDS',
                       var_name not in self.JS_KEYWORDS and type_name not in self.JS_KEYWORDS, lineno)
                if var_name not in self.JS_KEYWORDS and type_name not in self.JS_KEYWORDS:
                    log_if('type_name[0].isupper()', type_name[0].isupper(), lineno)
                    if type_name[0].isupper():
                        member_map[var_name] = type_name
        
        log_exit('_scan_members_in_body', lineno)
    
    @error_recovery()
    def _extract_component_relations(self):
        """后处理：提取组件嵌套关系（去重）"""
        lineno = 1635
        log_entry('_extract_component_relations', lineno)
        
        seen = set()

        log_for(f"class_info in classes (total {len(self.classes)})", lineno)
        for class_info in self.classes:
            log_if('class_info.is_component', class_info.is_component, lineno)
            if not class_info.is_component:
                continue

            build_calls = [
                c for c in self.calls
                if c.caller == 'build' and c.caller_class == class_info.name
            ]

            log_for(f"call in build_calls (total {len(build_calls)})", lineno)
            for call in build_calls:
                callee = call.callee
                is_component = (
                    callee in self._component_names or
                    any(c.name == callee and c.is_component for c in self.classes)
                )

                log_if('is_component and callee != class_info.name',
                       is_component and callee != class_info.name, lineno)
                if is_component and callee != class_info.name:
                    key = (class_info.name, callee)
                    log_if('key not in seen', key not in seen, lineno)
                    if key not in seen:
                        seen.add(key)
                        self.component_relations.append(ComponentRelation(
                            parent=class_info.name,
                            child=callee,
                            file=class_info.file,
                            line_number=call.line_number
                        ))
        
        log_exit('_extract_component_relations', lineno)

    def _get_result(self) -> Dict:
        lineno = 1667
        log_entry('_get_result', lineno)
        
        result = {
            'files': self.files,
            'classes': self.classes,
            'methods': self.methods,
            'calls': self.calls,
            'component_relations': self.component_relations,
            'inherits': self.inherits
        }
        
        log_var('files_count', len(self.files), lineno)
        log_var('classes_count', len(self.classes), lineno)
        log_var('methods_count', len(self.methods), lineno)
        log_var('calls_count', len(self.calls), lineno)
        log_exit('_get_result', lineno)
        return result


# ============================================================================
# 知识图谱构建器 - 带日志
# ============================================================================

class KnowledgeGraphBuilder:
    """
    知识图谱构建器 (Logged Version)
    
    新增功能:
    1. 循环依赖检测
    2. 性能优化（批量插入）
    3. 详细的构建报告
    4. 逐行执行日志
    """
    
    def __init__(self, db_path: str = "code.db"):
        lineno = 1814
        log_entry('KnowledgeGraphBuilder.__init__', lineno, db_path=db_path)
        
        self.db = DatabaseManager(db_path)
        self.parser = ArkTSParser()
        self.circular_detector = CircularDependencyDetector()
        self.build_time: float = 0.0
        
        log_exit('KnowledgeGraphBuilder.__init__', lineno)
    
    def build(self, project_path: str, detect_cycles: bool = True) -> Dict:
        """
        构建知识图谱
        """
        lineno = 1830
        log_entry('KnowledgeGraphBuilder.build', lineno, project_path=project_path)
        
        start_time = time.time()
        
        print(f"开始构建知识图谱: {project_path}")
        _logger.info(f"开始构建知识图谱: {project_path}")
        
        # 连接数据库
        log_var('step', 'connecting database', lineno)
        self.db.connect()
        self.db.create_tables()
        self.db.clear_tables()
        
        # 解析项目
        log_var('step', 'parsing project', lineno)
        print("正在解析项目...")
        result = self.parser.parse_project(project_path)
        
        # 循环依赖检测
        log_if('detect_cycles', detect_cycles, lineno)
        if detect_cycles:
            print("检测循环依赖...")
            self.circular_detector.add_edges_from_relations(result['inherits'])
            log_if('has_cycle', self.circular_detector.has_cycle(), lineno)
            if self.circular_detector.has_cycle():
                print(self.circular_detector.get_cycle_report())
            else:
                print("未发现循环依赖")
        
        # 存储到数据库
        log_var('step', 'storing to database', lineno)
        print("正在存储到数据库...")
        self._store_result(result)
        
        # 获取统计信息
        log_var('step', 'getting statistics', lineno)
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
        
        log_exit('KnowledgeGraphBuilder.build', lineno, stats)
        return stats
    
    def _store_result(self, result: Dict):
        """
        存储解析结果到数据库 (使用批量插入优化)
        """
        lineno = 1888
        log_entry('_store_result', lineno)
        
        _logger.info("开始存储解析结果到数据库...")
        
        # 存储文件（立即提交，确保外键约束）
        log_var('step', 'storing files', lineno)
        log_for(f"file_info in files (total {len(result['files'])})", lineno)
        for file_info in result['files']:
            self.db.insert_file(file_info)
        self.db.conn.commit()
        _logger.info(f"已插入 {len(result['files'])} 个文件记录")
        
        # 存储类
        log_var('step', 'storing classes', lineno)
        log_for(f"class_info in classes (total {len(result['classes'])})", lineno)
        for class_info in result['classes']:
            self.db.batch_insert_class(class_info)
        
        # 存储方法
        log_var('step', 'storing methods', lineno)
        log_for(f"method_info in methods (total {len(result['methods'])})", lineno)
        for method_info in result['methods']:
            self.db.batch_insert_method(method_info)
        
        # 存储调用关系
        log_var('step', 'storing calls', lineno)
        log_for(f"call in calls (total {len(result['calls'])})", lineno)
        for call in result['calls']:
            self.db.batch_insert_call(call)
        
        # 存储组件关系
        log_var('step', 'storing components', lineno)
        log_for(f"comp in component_relations (total {len(result['component_relations'])})", lineno)
        for comp in result['component_relations']:
            self.db.batch_insert_component(comp)
        
        # 存储继承关系
        log_var('step', 'storing inherits', lineno)
        log_for(f"inherit in inherits (total {len(result['inherits'])})", lineno)
        for inherit in result['inherits']:
            self.db.batch_insert_inherit(inherit)
        
        # 刷新所有批量缓冲区
        log_var('step', 'flushing all batches', lineno)
        self.db._flush_all_batches()
        
        _logger.info("解析结果存储完成")
        log_exit('_store_result', lineno)
    
    def get_circular_dependency_report(self) -> str:
        """获取循环依赖报告"""
        return self.circular_detector.get_cycle_report()
    
    def close(self):
        """关闭数据库连接"""
        lineno = 1929
        log_entry('KnowledgeGraphBuilder.close', lineno)
        
        self.db.close()
        
        log_exit('KnowledgeGraphBuilder.close', lineno)


# ============================================================================
# 主程序
# ============================================================================

def build_knowledge_graph(project_path: str, db_path: str = "code.db", 
                          detect_cycles: bool = True) -> KnowledgeGraphBuilder:
    """构建知识图谱的便捷函数"""
    lineno = 1938
    log_entry('build_knowledge_graph', lineno, project_path=project_path)
    
    builder = KnowledgeGraphBuilder(db_path)
    builder.build(project_path, detect_cycles=detect_cycles)
    
    log_exit('build_knowledge_graph', lineno)
    return builder


# ============================================================================
# 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    lineno = 1958
    log_entry('__main__', lineno)
    
    parser = argparse.ArgumentParser(description="ArkTS代码知识图谱系统 (Logged Version)")
    parser.add_argument("command", choices=["build", "query", "stats", "cycles"],
                       help="命令: build构建图谱, query查询, stats统计, cycles检测循环依赖")
    parser.add_argument("--project", "-p", help="项目路径")
    parser.add_argument("--db", "-d", default="code.db", help="数据库路径")
    parser.add_argument("--question", "-q", help="查询问题")
    parser.add_argument("--api-key", "-k", help="硅基流动API密钥")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    parser.add_argument("--no-cycle-check", action="store_true", help="跳过循环依赖检测")

    args = parser.parse_args()
    
    log_var('command', args.command, lineno)
    log_var('project', args.project, lineno)
    log_var('db', args.db, lineno)

    if args.command == "build":
        log_if('args.project', bool(args.project), lineno)
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        log_var('step', 'building knowledge graph', lineno)
        builder = KnowledgeGraphBuilder(args.db)
        builder.build(args.project, detect_cycles=not args.no_cycle_check)
        builder.close()
        
    elif args.command == "stats":
        log_var('step', 'getting stats', lineno)
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
        log_if('args.project', bool(args.project), lineno)
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        log_var('step', 'detecting cycles', lineno)
        print(f"检测项目循环依赖: {args.project}")
        parser = ArkTSParser()
        result = parser.parse_project(args.project)
        
        detector = CircularDependencyDetector()
        detector.add_edges_from_relations(result['inherits'])
        print(detector.get_cycle_report())
    
    log_exit('__main__', lineno)
