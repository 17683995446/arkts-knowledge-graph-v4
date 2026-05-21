#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS→SQLite 代码知识图谱系统 V2 (增强版)
基于第一性原理设计：将代码视为实体-关系系统，实现极简、高效、零成本的代码知识图谱

增强功能：
1. 详细日志系统 - 在每一句关键代码后打印日志
2. 复杂场景支持 - 解析更复杂的ArkTS代码结构，处理嵌套多层的方法调用
3. 循环依赖检测 - 检测并报告循环依赖
4. 性能监控 - 记录每个阶段的执行时间
5. 错误恢复 - 遇到解析错误时跳过并继续

核心设计原则：
1. 确定性原则：所有实体和关系通过静态分析100%确定
2. 最小化原则：只存储必要的结构信息
3. 零依赖原则：尽可能少地依赖外部服务
4. 可验证原则：所有数据可追溯到源代码位置
5. 零成本原则：使用免费工具和服务
6. 健壮性原则：错误恢复和边界情况处理
"""

import os
import re
import sqlite3
import json
import logging
import time
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Callable, Any
from functools import wraps
from contextlib import contextmanager

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

# ============================================================================
# 全局日志系统
# ============================================================================

class DetailedLogger:
    """详细日志记录器 - 支持统一格式和日志级别控制"""
    
    # 日志级别常量
    DEBUG = logging.DEBUG      # 10
    INFO = logging.INFO        # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR      # 40
    CRITICAL = logging.CRITICAL  # 50
    
    # 级别名称映射
    LEVEL_NAMES = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARNING: 'WARNING',
        ERROR: 'ERROR',
        CRITICAL: 'CRITICAL'
    }
    
    def __init__(self, name: str = 'arkts_kg_v2', level: int = logging.INFO):
        """初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        """
        self.logger = logging.getLogger(name)
        self.logger.handlers = []  # 清除已有处理器
        self.logger.setLevel(level)
        
        # 创建控制台处理器
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # 设置统一格式: [LEVEL 函数名:行号] 消息
        formatter = logging.Formatter(
            '[%(levelname)s %(funcName)s:%(lineno)d] %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.level = level
        self._log_counts = {self.DEBUG: 0, self.INFO: 0, self.WARNING: 0, self.ERROR: 0, self.CRITICAL: 0}
        
        self._log(self.DEBUG, '__init__', 48, f'日志系统初始化完成，级别: {self.LEVEL_NAMES.get(level, "UNKNOWN")}')
    
    def _get_caller_info(self) -> Tuple[str, int]:
        """获取调用者信息（函数名和行号）
        
        Returns:
            (函数名, 行号) 元组
        """
        import inspect
        frame = inspect.currentframe()
        try:
            # 向上回溯找到实际调用者（跳过当前函数和_log）
            caller_frame = frame.f_back.f_back
            if caller_frame:
                return (caller_frame.f_code.co_name, caller_frame.f_lineno)
            return ('unknown', 0)
        finally:
            del frame
    
    def _log(self, level: int, func_name: str, line_no: int, message: str):
        """内部日志记录方法
        
        Args:
            level: 日志级别
            func_name: 函数名
            line_no: 行号
            message: 日志消息
        """
        if level < self.level:
            return
        
        self._log_counts[level] += 1
        
        # 创建临时记录以使用统一格式
        level_name = self.LEVEL_NAMES.get(level, 'UNKNOWN')
        formatted_message = f'[{level_name} {func_name}:{line_no}] {message}'
        
        # 根据级别使用对应的日志方法
        if level <= self.DEBUG:
            self.logger.debug(message)
        elif level <= self.INFO:
            self.logger.info(message)
        elif level <= self.WARNING:
            self.logger.warning(message)
        elif level <= self.ERROR:
            self.logger.error(message)
        else:
            self.logger.critical(message)
    
    def debug(self, message: str, func_name: str = None, line_no: int = None):
        """记录DEBUG级别日志"""
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        self._log(self.DEBUG, func_name, line_no, message)
    
    def info(self, message: str, func_name: str = None, line_no: int = None):
        """记录INFO级别日志"""
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        self._log(self.INFO, func_name, line_no, message)
    
    def warning(self, message: str, func_name: str = None, line_no: int = None):
        """记录WARNING级别日志"""
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        self._log(self.WARNING, func_name, line_no, message)
    
    def error(self, message: str, func_name: str = None, line_no: int = None):
        """记录ERROR级别日志"""
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        self._log(self.ERROR, func_name, line_no, message)
    
    def critical(self, message: str, func_name: str = None, line_no: int = None):
        """记录CRITICAL级别日志"""
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        self._log(self.CRITICAL, func_name, line_no, message)
    
    def exception(self, message: str, func_name: str = None, line_no: int = None):
        """记录异常信息（包含堆栈）"""
        import traceback
        if func_name is None or line_no is None:
            func_name, line_no = self._get_caller_info()
        
        exc_info = traceback.format_exc()
        full_message = f'{message}\n异常详情:\n{exc_info}'
        self._log(self.ERROR, func_name, line_no, full_message)
    
    def log_entry(self, func_name: str, **kwargs):
        """记录函数入口
        
        Args:
            func_name: 函数名
            **kwargs: 参数信息
        """
        if kwargs:
            params = ', '.join(f'{k}={repr(v)[:50]}' for k, v in kwargs.items())
            self._log(self.DEBUG, func_name, 0, f'>>> 进入函数，参数: {params}')
        else:
            self._log(self.DEBUG, func_name, 0, '>>> 进入函数')
    
    def log_exit(self, func_name: str, result: Any = None):
        """记录函数出口
        
        Args:
            func_name: 函数名
            result: 返回值（可选）
        """
        if result is not None:
            result_str = repr(result)[:50]
            self._log(self.DEBUG, func_name, 0, f'<<< 退出函数，返回值: {result_str}')
        else:
            self._log(self.DEBUG, func_name, 0, '<<< 退出函数')
    
    def log_branch(self, func_name: str, condition: str, result: bool):
        """记录分支条件判断
        
        Args:
            func_name: 函数名
            condition: 条件描述
            result: 判断结果
        """
        self._log(self.DEBUG, func_name, 0, f'[分支] {condition} -> {result}')
    
    def log_loop(self, func_name: str, loop_type: str, iteration: int, info: str = ''):
        """记录循环执行
        
        Args:
            func_name: 函数名
            loop_type: 循环类型 (for/while)
            iteration: 迭代次数
            info: 额外信息
        """
        msg = f'[循环-{loop_type}] 第{iteration}次迭代'
        if info:
            msg += f', {info}'
        self._log(self.DEBUG, func_name, 0, msg)
    
    def get_stats(self) -> Dict[str, int]:
        """获取日志统计信息"""
        return {
            'debug': self._log_counts[self.DEBUG],
            'info': self._log_counts[self.INFO],
            'warning': self._log_counts[self.WARNING],
            'error': self._log_counts[self.ERROR],
            'critical': self._log_counts[self.CRITICAL],
            'total': sum(self._log_counts.values())
        }


# 全局日志实例（将在初始化时设置）
_logger: Optional[DetailedLogger] = None


def get_logger() -> DetailedLogger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = DetailedLogger()
    return _logger


def init_logger(level: int = logging.INFO) -> DetailedLogger:
    """初始化全局日志记录器
    
    Args:
        level: 日志级别
        
    Returns:
        DetailedLogger实例
    """
    global _logger
    _logger = DetailedLogger(level=level)
    return _logger


# ============================================================================
# 性能监控装饰器
# ============================================================================

def timed(func: Callable) -> Callable:
    """性能监控装饰器 - 记录函数执行时间"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        func_name = func.__name__
        
        # 记录入口
        logger.log_entry(func_name)
        
        # 记录开始时间
        start_time = time.perf_counter()
        logger.debug(f'开始计时', func_name, 0)
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 计算执行时间
            elapsed = time.perf_counter() - start_time
            logger.info(f'执行完成，耗时: {elapsed:.4f}秒', func_name, 0)
            
            # 记录出口
            logger.log_exit(func_name)
            
            return result
            
        except Exception as e:
            # 计算执行时间（即使出错）
            elapsed = time.perf_counter() - start_time
            logger.error(f'执行异常，耗时: {elapsed:.4f}秒，错误: {str(e)}', func_name, 0)
            raise
    
    return wrapper


@contextmanager
def timed_context(name: str):
    """性能监控上下文管理器
    
    Args:
        name: 上下文名称
        
    Usage:
        with timed_context('数据库操作'):
            # 执行数据库操作
            pass
    """
    logger = get_logger()
    start_time = time.perf_counter()
    logger.info(f'[{name}] 开始执行')
    
    try:
        yield
        elapsed = time.perf_counter() - start_time
        logger.info(f'[{name}] 执行完成，耗时: {elapsed:.4f}秒')
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logger.error(f'[{name}] 执行异常，耗时: {elapsed:.4f}秒，错误: {str(e)}')
        raise


# ============================================================================
# 错误恢复装饰器
# ============================================================================

def error_recovery(default_return: Any = None, log_level: int = DetailedLogger.WARNING):
    """错误恢复装饰器 - 遇到异常时记录并返回默认值
    
    Args:
        default_return: 异常时的默认返回值
        log_level: 日志级别
        
    Usage:
        @error_recovery(default_return=[])
        def parse_something():
            # 可能抛出异常的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            func_name = func.__name__
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 根据日志级别记录
                if log_level <= DetailedLogger.DEBUG:
                    logger.debug(f'执行被跳过，错误: {str(e)}', func_name, 0)
                elif log_level <= DetailedLogger.INFO:
                    logger.info(f'执行被跳过，错误: {str(e)}', func_name, 0)
                elif log_level <= DetailedLogger.WARNING:
                    logger.warning(f'执行被跳过，错误: {str(e)}', func_name, 0)
                else:
                    logger.error(f'执行失败，错误: {str(e)}', func_name, 0)
                
                return default_return
        
        return wrapper
    return decorator


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class FileInfo:
    """文件实体"""
    path: str
    line_count: int = 0  # 文件行数


@dataclass
class ClassInfo:
    """类/组件实体"""
    name: str
    file: str
    is_component: bool = False
    is_entry: bool = False
    line_number: int = 0
    end_line_number: int = 0  # 结束行号


@dataclass
class MethodInfo:
    """方法/函数实体"""
    name: str
    class_name: str
    file: str
    line_number: int = 0
    end_line_number: int = 0  # 结束行号
    is_static: bool = False
    is_private: bool = False
    is_async: bool = False  # 是否异步方法
    is_abstract: bool = False  # 是否抽象方法


@dataclass
class CallRelation:
    """函数调用关系"""
    caller: str
    caller_class: str
    callee: str
    callee_class: str
    file: str
    line_number: int = 0
    call_depth: int = 0  # 调用深度（嵌套层级）


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


@dataclass
class ParseError:
    """解析错误记录"""
    file: str
    line_number: int
    error_type: str
    message: str
    stack_trace: str = ''


# ============================================================================
# 循环依赖检测器
# ============================================================================

class CircularDependencyDetector:
    """循环依赖检测器"""
    
    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}
        self.logger = get_logger()
        self.logger.log_entry('CircularDependencyDetector.__init__')
        self.logger.log_exit('CircularDependencyDetector.__init__')
    
    def add_dependency(self, from_node: str, to_node: str):
        """添加依赖关系"""
        self.logger.debug(f'添加依赖: {from_node} -> {to_node}')
        
        if from_node not in self.dependencies:
            self.dependencies[from_node] = set()
        self.dependencies[from_node].add(to_node)
    
    def detect_cycles(self) -> List[List[str]]:
        """检测所有循环依赖
        
        Returns:
            循环路径列表，每个路径是一个节点列表
        """
        self.logger.log_entry('detect_cycles')
        
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """深度优先搜索检测循环"""
            self.logger.debug(f'DFS访问节点: {node}, 当前路径: {path}')
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # 遍历所有依赖
            for neighbor in self.dependencies.get(node, set()):
                self.logger.debug(f'检查邻居: {neighbor}')
                
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 发现循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    self.logger.warning(f'发现循环依赖: {" -> ".join(cycle)}')
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        # 对所有节点执行DFS
        for node in self.dependencies:
            self.logger.debug(f'从节点开始DFS: {node}')
            if node not in visited:
                dfs(node)
        
        self.logger.info(f'循环依赖检测完成，发现 {len(cycles)} 个循环')
        self.logger.log_exit('detect_cycles', cycles)
        return cycles
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖图"""
        self.logger.log_entry('get_dependency_graph')
        result = {k: list(v) for k, v in self.dependencies.items()}
        self.logger.log_exit('get_dependency_graph', result)
        return result


# ============================================================================
# 数据库管理
# ============================================================================

class DatabaseManager:
    """SQLite数据库管理器（增强版）"""
    
    def __init__(self, db_path: str = "code_v2.db"):
        self.logger = get_logger()
        self.logger.log_entry('DatabaseManager.__init__', db_path=db_path)
        
        self.db_path = db_path
        self.conn = None
        self._error_count = 0
        
        self.logger.info(f'数据库路径: {db_path}')
        self.logger.log_exit('DatabaseManager.__init__')
    
    @timed
    def connect(self):
        """连接数据库"""
        self.logger.log_entry('DatabaseManager.connect')
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.logger.info('数据库连接成功')
        except sqlite3.Error as e:
            self.logger.error(f'数据库连接失败: {str(e)}')
            self._error_count += 1
            raise
        
        self.logger.log_exit('DatabaseManager.connect')
    
    @timed
    def close(self):
        """关闭数据库连接"""
        self.logger.log_entry('DatabaseManager.close')
        
        if self.conn:
            try:
                self.conn.close()
                self.logger.info('数据库连接已关闭')
            except sqlite3.Error as e:
                self.logger.error(f'关闭数据库连接失败: {str(e)}')
                self._error_count += 1
        else:
            self.logger.warning('数据库连接未建立，无需关闭')
        
        self.logger.log_exit('DatabaseManager.close')
    
    @timed
    def create_tables(self):
        """创建数据库表结构"""
        self.logger.log_entry('DatabaseManager.create_tables')
        
        if not self.conn:
            self.logger.error('数据库未连接')
            raise RuntimeError("数据库未连接")
        
        cursor = self.conn.cursor()
        
        try:
            # 实体表 - files
            self.logger.debug('创建 files 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    line_count INTEGER DEFAULT 0
                )
            """)
            
            # 实体表 - classes
            self.logger.debug('创建 classes 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    name TEXT NOT NULL,
                    file TEXT NOT NULL,
                    is_component INTEGER DEFAULT 0,
                    is_entry INTEGER DEFAULT 0,
                    line_number INTEGER DEFAULT 0,
                    end_line_number INTEGER DEFAULT 0,
                    PRIMARY KEY (name, file),
                    FOREIGN KEY (file) REFERENCES files(path)
                )
            """)
            
            # 实体表 - methods
            self.logger.debug('创建 methods 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS methods (
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    end_line_number INTEGER DEFAULT 0,
                    is_static INTEGER DEFAULT 0,
                    is_private INTEGER DEFAULT 0,
                    is_async INTEGER DEFAULT 0,
                    is_abstract INTEGER DEFAULT 0,
                    PRIMARY KEY (name, class_name, file),
                    FOREIGN KEY (file) REFERENCES files(path)
                )
            """)
            
            # 关系表 - calls
            self.logger.debug('创建 calls 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    caller TEXT NOT NULL,
                    caller_class TEXT NOT NULL,
                    callee TEXT NOT NULL,
                    callee_class TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    call_depth INTEGER DEFAULT 0,
                    PRIMARY KEY (caller, caller_class, callee, callee_class, file, line_number)
                )
            """)
            
            # 关系表 - components
            self.logger.debug('创建 components 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS components (
                    parent TEXT NOT NULL,
                    child TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    PRIMARY KEY (parent, child, file)
                )
            """)
            
            # 关系表 - inherits
            self.logger.debug('创建 inherits 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inherits (
                    child_class TEXT NOT NULL,
                    parent_class TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    PRIMARY KEY (child_class, parent_class, file)
                )
            """)
            
            # 错误记录表 - parse_errors
            self.logger.debug('创建 parse_errors 表')
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parse_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    error_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    stack_trace TEXT DEFAULT ''
                )
            """)
            
            # 创建索引加速查询
            self.logger.debug('创建索引')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_class)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_class)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_child ON components(child)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_file ON parse_errors(file)")
            
            self.conn.commit()
            self.logger.info('数据库表创建成功')
            
        except sqlite3.Error as e:
            self.logger.error(f'创建表失败: {str(e)}')
            self._error_count += 1
            raise
        
        self.logger.log_exit('DatabaseManager.create_tables')
    
    @timed
    def clear_tables(self):
        """清空所有表数据"""
        self.logger.log_entry('DatabaseManager.clear_tables')
        
        cursor = self.conn.cursor()
        tables = ['calls', 'components', 'inherits', 'methods', 'classes', 'files', 'parse_errors']
        
        for table in tables:
            try:
                self.logger.debug(f'清空表: {table}')
                cursor.execute(f"DELETE FROM {table}")
            except sqlite3.Error as e:
                self.logger.warning(f'清空表 {table} 失败: {str(e)}')
                self._error_count += 1
        
        self.conn.commit()
        self.logger.info('所有表已清空')
        self.logger.log_exit('DatabaseManager.clear_tables')
    
    def insert_file(self, file_info: FileInfo):
        """插入文件记录"""
        self.logger.debug(f'插入文件: {file_info.path}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO files (path, line_count) VALUES (?, ?)",
                (file_info.path, file_info.line_count)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入文件失败: {file_info.path}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_class(self, class_info: ClassInfo):
        """插入类/组件记录"""
        self.logger.debug(f'插入类: {class_info.name} (文件: {class_info.file})')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO classes 
                   (name, file, is_component, is_entry, line_number, end_line_number) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (class_info.name, class_info.file, 
                 int(class_info.is_component), int(class_info.is_entry),
                 class_info.line_number, class_info.end_line_number)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入类失败: {class_info.name}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_method(self, method_info: MethodInfo):
        """插入方法记录"""
        self.logger.debug(f'插入方法: {method_info.class_name}.{method_info.name}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO methods 
                   (name, class_name, file, line_number, end_line_number, 
                    is_static, is_private, is_async, is_abstract) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (method_info.name, method_info.class_name, method_info.file,
                 method_info.line_number, method_info.end_line_number,
                 int(method_info.is_static), int(method_info.is_private),
                 int(method_info.is_async), int(method_info.is_abstract))
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入方法失败: {method_info.name}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_call(self, call: CallRelation):
        """插入调用关系"""
        self.logger.debug(f'插入调用关系: {call.caller} -> {call.callee}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO calls 
                   (caller, caller_class, callee, callee_class, file, line_number, call_depth) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (call.caller, call.caller_class, call.callee, call.callee_class,
                 call.file, call.line_number, call.call_depth)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入调用关系失败: {call.caller} -> {call.callee}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_component_relation(self, comp: ComponentRelation):
        """插入组件嵌套关系"""
        self.logger.debug(f'插入组件关系: {comp.parent} -> {comp.child}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO components 
                   (parent, child, file, line_number) 
                   VALUES (?, ?, ?, ?)""",
                (comp.parent, comp.child, comp.file, comp.line_number)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入组件关系失败: {comp.parent} -> {comp.child}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_inherit(self, inherit: InheritRelation):
        """插入继承关系"""
        self.logger.debug(f'插入继承关系: {inherit.child_class} -> {inherit.parent_class}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO inherits 
                   (child_class, parent_class, file, line_number) 
                   VALUES (?, ?, ?, ?)""",
                (inherit.child_class, inherit.parent_class, inherit.file, inherit.line_number)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入继承关系失败: {inherit.child_class} -> {inherit.parent_class}, 错误: {str(e)}')
            self._error_count += 1
    
    def insert_parse_error(self, error: ParseError):
        """插入解析错误记录"""
        self.logger.debug(f'插入解析错误: {error.file}:{error.line_number} - {error.error_type}')
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO parse_errors 
                   (file, line_number, error_type, message, stack_trace) 
                   VALUES (?, ?, ?, ?, ?)""",
                (error.file, error.line_number, error.error_type, 
                 error.message, error.stack_trace)
            )
        except sqlite3.Error as e:
            self.logger.warning(f'插入解析错误失败: {str(e)}')
            self._error_count += 1
    
    def get_schema_description(self) -> str:
        """获取数据库schema描述，用于AI查询"""
        self.logger.log_entry('DatabaseManager.get_schema_description')
        
        schema = """
数据库表结构：

1. files - 文件表
   - path: 文件路径 (主键)
   - line_count: 文件行数

2. classes - 类/组件表
   - name: 类名
   - file: 所属文件
   - is_component: 是否为组件 (0/1)
   - is_entry: 是否为入口组件 (0/1)
   - line_number: 开始行号
   - end_line_number: 结束行号

3. methods - 方法表
   - name: 方法名
   - class_name: 所属类名
   - file: 所属文件
   - line_number: 开始行号
   - end_line_number: 结束行号
   - is_static: 是否静态方法 (0/1)
   - is_private: 是否私有方法 (0/1)
   - is_async: 是否异步方法 (0/1)
   - is_abstract: 是否抽象方法 (0/1)

4. calls - 函数调用关系表
   - caller: 调用者方法名
   - caller_class: 调用者所属类
   - callee: 被调用方法名
   - callee_class: 被调用方法所属类
   - file: 文件路径
   - line_number: 行号
   - call_depth: 调用深度

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

7. parse_errors - 解析错误表
   - id: 错误ID
   - file: 文件路径
   - line_number: 行号
   - error_type: 错误类型
   - message: 错误消息
   - stack_trace: 堆栈跟踪
"""
        self.logger.log_exit('DatabaseManager.get_schema_description', schema[:100] + '...')
        return schema
    
    @timed
    def execute_query(self, sql: str) -> List[Tuple]:
        """执行SQL查询"""
        self.logger.log_entry('DatabaseManager.execute_query', sql=sql[:50])
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            self.logger.info(f'查询执行成功，返回 {len(results)} 行')
            self.logger.log_exit('DatabaseManager.execute_query', results[:5] if results else [])
            return results
        except sqlite3.Error as e:
            self.logger.error(f'查询执行失败: {str(e)}')
            self._error_count += 1
            raise
    
    @timed
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        self.logger.log_entry('DatabaseManager.get_statistics')
        
        cursor = self.conn.cursor()
        stats = {'errors': self._error_count}
        
        queries = {
            'files': 'SELECT COUNT(*) FROM files',
            'classes': 'SELECT COUNT(*) FROM classes',
            'components': 'SELECT COUNT(*) FROM classes WHERE is_component = 1',
            'entry_components': 'SELECT COUNT(*) FROM classes WHERE is_entry = 1',
            'methods': 'SELECT COUNT(*) FROM methods',
            'call_relations': 'SELECT COUNT(*) FROM calls',
            'component_relations': 'SELECT COUNT(*) FROM components',
            'inherit_relations': 'SELECT COUNT(*) FROM inherits',
            'parse_errors': 'SELECT COUNT(*) FROM parse_errors'
        }
        
        for key, query in queries.items():
            try:
                cursor.execute(query)
                stats[key] = cursor.fetchone()[0]
                self.logger.debug(f'{key}: {stats[key]}')
            except sqlite3.Error as e:
                self.logger.warning(f'统计 {key} 失败: {str(e)}')
                stats[key] = -1
        
        self.logger.log_exit('DatabaseManager.get_statistics', stats)
        return stats


# ============================================================================
# ArkTS代码解析器 (V2 增强版)
# ============================================================================

# Unicode标识符模式（支持中文、日文、韩文、$符号）
_ID_PATTERN = r'[\w$\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]+'


class ArkTSParser:
    """ArkTS代码静态解析器 V2 (增强版)
    
    增强功能：
    1. 详细日志记录
    2. 错误恢复机制
    3. 循环依赖检测
    4. 性能监控
    5. 嵌套调用深度分析
    
    核心设计变更：所有解析都在stripped内容上操作（stripped = 移除注释和字符串后的内容），
    避免原始内容和stripped内容之间的位置映射问题。行号通过 content[:pos].count('\n')
    从原始内容获取。
    """

    # === 过滤器集合 ===

    # ArkTS内置UI组件名
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
    })

    # ArkTS链式属性设置方法
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
        'id', 'tag', 'key', 'name', 'style', 'show', 'visibility',
        'zIndex', 'markAnchor', 'anchor',
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
        'structuredClone', 'queueMicrotask',
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
        'struct', 'declare', 'namespace', 'module',
    })

    # 所有应跳过的标识符
    SKIP_IDENTIFIERS = JS_GLOBALS | JS_KEYWORDS | ARKTS_KEYWORDS | UI_COMPONENTS | UI_CHAIN_PROPERTIES

    def __init__(self, log_level: int = logging.INFO):
        """初始化解析器
        
        Args:
            log_level: 日志级别
        """
        # 初始化日志
        self.logger = init_logger(log_level)
        self.logger.log_entry('ArkTSParser.__init__', log_level=log_level)
        
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

        # 箭头函数属性正则（如 on = (event: string) => { ... }）
        self.arrow_property_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(' + _ID_PATTERN + r')\s*=\s*\(',
            re.MULTILINE
        )

        # call正则 (支持泛型方法调用如 get<T>())
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

        # 存储列表
        self.files: List[FileInfo] = []
        self.classes: List[ClassInfo] = []
        self.methods: List[MethodInfo] = []
        self.calls: List[CallRelation] = []
        self.component_relations: List[ComponentRelation] = []
        self.inherits: List[InheritRelation] = []
        self.parse_errors: List[ParseError] = []

        # _component_names, _all_class_names
        self._component_names: Set[str] = set()
        self._all_class_names: Set[str] = set()
        
        # 循环依赖检测器
        self._circular_detector = CircularDependencyDetector()
        
        # 性能统计
        self._parse_times: Dict[str, float] = {}
        
        self.logger.info('解析器初始化完成')
        self.logger.log_exit('ArkTSParser.__init__')

    @timed
    def _strip_comments_and_strings(self, content: str) -> str:
        """移除注释和字符串，保留换行符
        
        Args:
            content: 原始代码内容
            
        Returns:
            移除注释和字符串后的内容
        """
        self.logger.log_entry('_strip_comments_and_strings', content_length=len(content))
        
        result = []
        i = 0
        n = len(content)
        
        while i < n:
            c = content[i]
            
            # 单行注释
            if c == '/' and i + 1 < n and content[i + 1] == '/':
                self.logger.debug(f'发现单行注释，位置: {i}')
                while i < n and content[i] != '\n':
                    i += 1
                result.append(' ')
            # 多行注释
            elif c == '/' and i + 1 < n and content[i + 1] == '*':
                self.logger.debug(f'发现多行注释，位置: {i}')
                i += 2
                while i + 1 < n and not (content[i] == '*' and content[i + 1] == '/'):
                    if content[i] == '\n':
                        result.append('\n')
                    i += 1
                i += 2
                result.append(' ')
            # 模板字符串 `...`
            elif c == '`':
                self.logger.debug(f'发现模板字符串，位置: {i}')
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
        
        stripped = ''.join(result)
        self.logger.info(f'注释和字符串移除完成: {len(content)} -> {len(stripped)} 字符')
        self.logger.log_exit('_strip_comments_and_strings', stripped[:100] + '...')
        return stripped

    @timed
    def _find_matching_brace(self, stripped: str, start: int) -> int:
        """在stripped内容中找到匹配的}
        
        Args:
            stripped: 处理后的代码内容
            start: 开始位置（应该是{的位置）
            
        Returns:
            匹配的}的位置
        """
        self.logger.log_entry('_find_matching_brace', start=start)
        
        brace_count = 0
        i = start
        
        while i < len(stripped):
            if stripped[i] == '{':
                brace_count += 1
            elif stripped[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    self.logger.debug(f'找到匹配的花括号，位置: {i}')
                    self.logger.log_exit('_find_matching_brace', i)
                    return i
            i += 1
        
        self.logger.warning(f'未找到匹配的花括号，返回末尾位置: {len(stripped) - 1}')
        self.logger.log_exit('_find_matching_brace', len(stripped) - 1)
        return len(stripped) - 1

    @timed
    def parse_project(self, project_path: str) -> Dict:
        """解析整个项目 - 两遍解析（增强版）
        
        Args:
            project_path: 项目路径
            
        Returns:
            解析结果字典
        """
        self.logger.log_entry('parse_project', project_path=project_path)
        
        project_path = Path(project_path)
        
        # 检查路径是否存在
        if not project_path.exists():
            self.logger.error(f'项目路径不存在: {project_path}')
            raise FileNotFoundError(f"项目路径不存在: {project_path}")
        
        self.logger.info(f'开始解析项目: {project_path}')
        
        # 查找所有ArkTS文件
        arkts_files = list(project_path.rglob("*.ets")) + list(project_path.rglob("*.ts"))
        self.logger.info(f'找到 {len(arkts_files)} 个ArkTS文件')
        
        # 第一遍：收集所有类/组件名（不解析方法）
        self.logger.info('===== 第一遍解析：收集声明 =====')
        scan_count = 0
        for file_path in arkts_files:
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                self.logger.debug(f'跳过目录: {file_path}')
                continue
            
            try:
                self._scan_declarations(str(file_path))
                scan_count += 1
            except Exception as e:
                self.logger.error(f'扫描文件失败: {file_path}, 错误: {str(e)}')
                self._record_error(str(file_path), 0, 'SCAN_ERROR', str(e))
        
        self.logger.info(f'第一遍解析完成，扫描了 {scan_count} 个文件')
        
        # 第二遍：完整解析（包括方法，可利用第一遍收集的名称）
        self.logger.info('===== 第二遍解析：完整解析 =====')
        parse_count = 0
        for file_path in arkts_files:
            if 'node_modules' in str(file_path) or '.git' in str(file_path):
                continue
            
            try:
                self._full_parse(str(file_path))
                parse_count += 1
            except Exception as e:
                self.logger.error(f'解析文件失败: {file_path}, 错误: {str(e)}')
                self._record_error(str(file_path), 0, 'PARSE_ERROR', str(e))
        
        self.logger.info(f'第二遍解析完成，解析了 {parse_count} 个文件')
        
        # 后处理
        self.logger.info('===== 后处理 =====')
        
        with timed_context('解析被调用类'):
            self._resolve_callee_classes()
        
        with timed_context('提取组件关系'):
            self._extract_component_relations()
        
        # 检测循环依赖
        with timed_context('循环依赖检测'):
            cycles = self._circular_detector.detect_cycles()
            if cycles:
                self.logger.warning(f'发现 {len(cycles)} 个循环依赖')
                for cycle in cycles:
                    self.logger.warning(f'  循环: {" -> ".join(cycle)}')
        
        result = self._get_result()
        self.logger.info('项目解析完成')
        self.logger.log_exit('parse_project', result.keys())
        
        return result

    @error_recovery(default_return=None)
    def _scan_declarations(self, file_path: str):
        """第一遍：只收集类/组件声明
        
        Args:
            file_path: 文件路径
        """
        self.logger.log_entry('_scan_declarations', file_path=file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f'读取文件失败: {file_path}, 错误: {str(e)}')
            raise
        
        # 添加文件记录
        line_count = content.count('\n') + 1
        self.files.append(FileInfo(path=file_path, line_count=line_count))
        self.logger.debug(f'文件行数: {line_count}')
        
        # 移除注释和字符串
        stripped = self._strip_comments_and_strings(content)
        self.logger.debug(f'文件内容处理: {len(content)} -> {len(stripped)} 字符')
        
        # 扫描struct声明
        struct_count = 0
        for match in self.struct_pattern.finditer(stripped):
            name = match.group(3)
            before = stripped[:match.start()]
            last_brace = before.rfind('}')
            region = before[last_brace:] if last_brace != -1 else before
            
            if self.component_decorator.search(region):
                self._component_names.add(name)
                self.logger.debug(f'发现组件: {name}')
            
            self._all_class_names.add(name)
            line_no = content[:match.start()].count(chr(10)) + 1
            self.logger.debug(f'发现struct: {name} 在第 {line_no} 行')
            struct_count += 1
        
        self.logger.debug(f'共发现 {struct_count} 个struct')
        
        # 扫描class声明
        class_count = 0
        for match in self.class_pattern.finditer(stripped):
            name = match.group(4)
            self._all_class_names.add(name)
            line_no = content[:match.start()].count(chr(10)) + 1
            self.logger.debug(f'发现class: {name} 在第 {line_no} 行')
            class_count += 1
        
        self.logger.debug(f'共发现 {class_count} 个class')
        self.logger.info(f'文件扫描完成: {file_path} (struct: {struct_count}, class: {class_count})')
        self.logger.log_exit('_scan_declarations')

    @error_recovery(default_return=None)
    def _full_parse(self, file_path: str):
        """第二遍：完整解析
        
        Args:
            file_path: 文件路径
        """
        self.logger.log_entry('_full_parse', file_path=file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f'读取文件失败: {file_path}, 错误: {str(e)}')
            raise
        
        stripped = self._strip_comments_and_strings(content)
        self.logger.debug(f'开始完整解析: {file_path}')
        
        # 解析struct
        struct_count = 0
        for match in self.struct_pattern.finditer(stripped):
            try:
                self._parse_struct(match, stripped, content, file_path)
                struct_count += 1
            except Exception as e:
                self.logger.error(f'解析struct失败: {str(e)}')
                self._record_error(file_path, 0, 'STRUCT_PARSE_ERROR', str(e))
        
        self.logger.debug(f'解析了 {struct_count} 个struct')
        
        # 解析class
        class_count = 0
        for match in self.class_pattern.finditer(stripped):
            try:
                self._parse_class(match, stripped, content, file_path)
                class_count += 1
            except Exception as e:
                self.logger.error(f'解析class失败: {str(e)}')
                self._record_error(file_path, 0, 'CLASS_PARSE_ERROR', str(e))
        
        self.logger.debug(f'解析了 {class_count} 个class')
        
        # 解析顶层函数
        try:
            self._parse_top_level_functions(stripped, content, file_path)
        except Exception as e:
            self.logger.error(f'解析顶层函数失败: {str(e)}')
            self._record_error(file_path, 0, 'TOP_FUNC_PARSE_ERROR', str(e))
        
        self.logger.info(f'文件解析完成: {file_path}')
        self.logger.log_exit('_full_parse')

    def _parse_struct(self, match, stripped: str, content: str, file_path: str):
        """解析单个struct
        
        Args:
            match: 正则匹配结果
            stripped: 处理后的代码
            content: 原始代码
            file_path: 文件路径
        """
        name = match.group(3)
        start_pos = match.start()
        line_number = content[:start_pos].count('\n') + 1
        
        self.logger.debug(f'解析struct: {name} 在第 {line_number} 行')
        
        # 检查装饰器
        before = stripped[:start_pos]
        last_brace = before.rfind('}')
        region = before[last_brace:] if last_brace != -1 else before
        is_component = bool(self.component_decorator.search(region))
        is_entry = bool(self.entry_decorator.search(region))
        
        # 提取struct体
        body_start = match.end() - 1
        body_end = self._find_matching_brace(stripped, body_start)
        end_line = content[:body_end].count('\n') + 1
        
        self.classes.append(ClassInfo(
            name=name, file=file_path,
            is_component=is_component, is_entry=is_entry,
            line_number=line_number, end_line_number=end_line
        ))
        self.logger.debug(f'添加类: {name} (component={is_component}, entry={is_entry})')
        
        # 提取extends继承关系
        parent_class = match.group(4)
        if parent_class and parent_class not in self.JS_KEYWORDS:
            self.inherits.append(InheritRelation(
                child_class=name, parent_class=parent_class,
                file=file_path, line_number=line_number
            ))
            self.logger.debug(f'添加继承关系: {name} extends {parent_class}')
            # 添加到循环依赖检测器
            self._circular_detector.add_dependency(name, parent_class)
        
        # 提取implements接口关系
        implements_str = match.group(5)
        if implements_str:
            for iface_name in re.findall(r'\b(\w+)\b', implements_str):
                if iface_name not in self.JS_KEYWORDS and iface_name != name:
                    self.inherits.append(InheritRelation(
                        child_class=name, parent_class=iface_name,
                        file=file_path, line_number=line_number
                    ))
                    self.logger.debug(f'添加实现关系: {name} implements {iface_name}')
        
        # 提取struct体并解析方法
        body = stripped[body_start:body_end + 1]
        self.logger.debug(f'struct体大小: {len(body)} 字符')
        
        try:
            self._parse_methods(body, name, file_path, line_number)
        except Exception as e:
            self.logger.error(f'解析struct方法失败: {name}, 错误: {str(e)}')
            self._record_error(file_path, line_number, 'METHOD_PARSE_ERROR', str(e))

    def _parse_class(self, match, stripped: str, content: str, file_path: str):
        """解析单个class
        
        Args:
            match: 正则匹配结果
            stripped: 处理后的代码
            content: 原始代码
            file_path: 文件路径
        """
        name = match.group(4)
        parent = match.group(5)
        start_pos = match.start()
        line_number = content[:start_pos].count('\n') + 1
        
        self.logger.debug(f'解析class: {name} 在第 {line_number} 行')
        
        # 检查是否已存在
        if any(c.name == name and c.file == file_path for c in self.classes):
            self.logger.debug(f'类已存在，跳过: {name}')
            return
        
        # 检查装饰器
        before = stripped[:start_pos]
        last_brace = before.rfind('}')
        region = before[last_brace:] if last_brace != -1 else before
        is_component = bool(self.component_decorator.search(region))
        is_entry = bool(self.entry_decorator.search(region))
        
        # 提取class体
        body_start = match.end() - 1
        body_end = self._find_matching_brace(stripped, body_start)
        end_line = content[:body_end].count('\n') + 1
        
        self.classes.append(ClassInfo(
            name=name, file=file_path,
            is_component=is_component, is_entry=is_entry,
            line_number=line_number, end_line_number=end_line
        ))
        self.logger.debug(f'添加类: {name}')
        
        # 添加继承关系
        if parent:
            self.inherits.append(InheritRelation(
                child_class=name, parent_class=parent,
                file=file_path, line_number=line_number
            ))
            self.logger.debug(f'添加继承关系: {name} extends {parent}')
            self._circular_detector.add_dependency(name, parent)
        
        # 提取implements接口关系
        implements_str = match.group(6)
        if implements_str:
            for iface_name in re.findall(r'\b(\w+)\b', implements_str):
                if iface_name not in self.JS_KEYWORDS and iface_name != name:
                    self.inherits.append(InheritRelation(
                        child_class=name, parent_class=iface_name,
                        file=file_path, line_number=line_number
                    ))
                    self.logger.debug(f'添加实现关系: {name} implements {iface_name}')
        
        # 提取class体并解析方法
        body = stripped[body_start:body_end + 1]
        self.logger.debug(f'class体大小: {len(body)} 字符')
        
        try:
            self._parse_methods(body, name, file_path, line_number)
        except Exception as e:
            self.logger.error(f'解析class方法失败: {name}, 错误: {str(e)}')
            self._record_error(file_path, line_number, 'METHOD_PARSE_ERROR', str(e))

    def _extract_body(self, stripped: str, open_brace: int) -> str:
        """在stripped上提取类体
        
        Args:
            stripped: 处理后的代码
            open_brace: 左花括号位置
            
        Returns:
            类体内容
        """
        self.logger.log_entry('_extract_body', open_brace=open_brace)
        close = self._find_matching_brace(stripped, open_brace)
        body = stripped[open_brace:close + 1]
        self.logger.log_exit('_extract_body', body[:50] + '...')
        return body

    @timed
    def _parse_methods(self, body_stripped: str, class_name: str, file_path: str,
                       class_line: int):
        """在stripped类体上解析方法（包括箭头函数属性）
        
        Args:
            body_stripped: 类体内容
            class_name: 类名
            file_path: 文件路径
            class_line: 类开始行号
        """
        self.logger.log_entry('_parse_methods', 
                              class_name=class_name, 
                              file_path=file_path, 
                              class_line=class_line,
                              body_length=len(body_stripped))
        
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
        self.logger.debug('移除装饰器...')
        body_no_dec = self.decorator_line_pattern.sub(r'\1', body_stripped)
        body_no_dec = self.decorator_line_noarg_pattern.sub(r'\1', body_no_dec)
        
        # 计算每个位置的花括号深度
        self.logger.debug('计算花括号深度...')
        brace_depth = 0
        depth_at_pos = {}
        for idx, ch in enumerate(body_no_dec):
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            depth_at_pos[idx] = brace_depth
        
        # 收集所有已匹配的位置
        matched_positions = set()
        method_count = 0
        arrow_count = 0

        # 1. 匹配普通方法
        self.logger.debug('开始匹配普通方法...')
        for match in self.method_pattern.finditer(body_no_dec):
            method_name = match.group(5)
            
            # 只匹配类体顶层的方法定义（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                self.logger.debug(f'跳过非顶层方法: {method_name} (深度={match_depth})')
                continue

            # 跳过各种不应识别的标识符
            if method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS:
                if method_name not in METHOD_SAFE_KEYWORDS:
                    self.logger.debug(f'跳过关键字: {method_name}')
                    continue
            if method_name == 'constructor':
                self.logger.debug(f'跳过构造函数: {method_name}')
                continue
            if method_name in self.UI_COMPONENTS:
                self.logger.debug(f'跳过UI组件: {method_name}')
                continue
            if method_name in self.UI_CHAIN_PROPERTIES and method_name not in ARKTS_LIFECYCLE:
                self.logger.debug(f'跳过UI属性: {method_name}')
                continue
            if method_name in self._component_names and method_name != class_name:
                self.logger.debug(f'跳过组件名: {method_name}')
                continue
            if method_name in self._all_class_names and method_name != class_name:
                self.logger.debug(f'跳过类名: {method_name}')
                continue

            matched_positions.add(match.start())

            # 计算行号
            line_number = class_line + body_no_dec[:match.start()].count('\n')

            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)
            is_async = match.group(3) is not None and 'async' in match.group(3)
            is_abstract = match.group(4) is not None and 'abstract' in match.group(4)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private,
                is_async=is_async, is_abstract=is_abstract
            ))
            self.logger.debug(f'添加方法: {class_name}.{method_name} (static={is_static}, private={is_private}, async={is_async}, abstract={is_abstract})')
            method_count += 1

            # abstract方法没有方法体
            if is_abstract:
                self.logger.debug(f'跳过抽象方法体: {method_name}')
                continue

            # 提取方法体
            try:
                paren_pos = match.end() - 1
                brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
                if brace_pos == -1:
                    self.logger.debug(f'未找到方法体: {method_name}')
                    continue

                close_pos = self._find_matching_brace(body_no_dec, brace_pos)
                method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
                end_line = class_line + body_no_dec[:close_pos].count('\n')
                
                # 更新结束行号
                for m in self.methods:
                    if m.name == method_name and m.class_name == class_name and m.file == file_path:
                        m.end_line_number = end_line
                        break
                
                self.logger.debug(f'方法体大小: {len(method_body_stripped)} 字符')
                
                # 解析方法体内的调用
                self._parse_calls(method_body_stripped, method_name, class_name,
                                  file_path, line_number)
            except Exception as e:
                self.logger.error(f'解析方法体失败: {method_name}, 错误: {str(e)}')
                self._record_error(file_path, line_number, 'METHOD_BODY_PARSE_ERROR', str(e))

        # 2. 匹配箭头函数属性
        self.logger.debug('开始匹配箭头函数属性...')
        for match in self.arrow_property_pattern.finditer(body_no_dec):
            if match.start() in matched_positions:
                continue

            method_name = match.group(3)

            # 只匹配类体顶层（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            # 跳过各种不应识别的标识符
            if method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS:
                if method_name not in METHOD_SAFE_KEYWORDS:
                    continue
            if method_name == 'constructor':
                continue
            if method_name in self.UI_COMPONENTS:
                continue
            if method_name in self.UI_CHAIN_PROPERTIES and method_name not in ARKTS_LIFECYCLE:
                continue
            if method_name in self._component_names and method_name != class_name:
                continue
            if method_name in self._all_class_names and method_name != class_name:
                continue

            line_number = class_line + body_no_dec[:match.start()].count('\n')
            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private
            ))
            self.logger.debug(f'添加箭头函数: {class_name}.{method_name}')
            arrow_count += 1

            # 提取箭头函数体
            try:
                paren_pos = match.end() - 1
                brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
                if brace_pos == -1:
                    continue

                close_pos = self._find_matching_brace(body_no_dec, brace_pos)
                method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
                end_line = class_line + body_no_dec[:close_pos].count('\n')
                
                # 更新结束行号
                for m in self.methods:
                    if m.name == method_name and m.class_name == class_name and m.file == file_path:
                        m.end_line_number = end_line
                        break
                
                self._parse_calls(method_body_stripped, method_name, class_name,
                                  file_path, line_number)
            except Exception as e:
                self.logger.error(f'解析箭头函数体失败: {method_name}, 错误: {str(e)}')
                self._record_error(file_path, line_number, 'ARROW_FUNC_PARSE_ERROR', str(e))

        self.logger.info(f'方法解析完成: 普通方法={method_count}, 箭头函数={arrow_count}')
        self.logger.log_exit('_parse_methods')

    def _skip_params_and_return_type(self, stripped: str, paren_pos: int) -> int:
        """跳过参数列表和返回类型，返回方法体{的位置
        
        Args:
            stripped: 处理后的代码
            paren_pos: 左括号位置
            
        Returns:
            左花括号位置，如果找不到返回-1
        """
        self.logger.log_entry('_skip_params_and_return_type', paren_pos=paren_pos)
        
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
            self.logger.debug('到达字符串末尾，未找到方法体')
            self.logger.log_exit('_skip_params_and_return_type', -1)
            return -1

        # 如果遇到':'，跳过返回类型
        if stripped[i] == ':':
            self.logger.debug('发现返回类型声明')
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
                        self.logger.debug(f'找到方法体开始位置: {i}')
                        self.logger.log_exit('_skip_params_and_return_type', i)
                        return i
                    brace_count += 1
                elif stripped[i] == '}' and angle_count <= 0:
                    brace_count -= 1
                elif stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
                    break
                elif stripped[i] == ';' and angle_count <= 0 and brace_count == 0:
                    self.logger.debug('发现分号，无方法体')
                    self.logger.log_exit('_skip_params_and_return_type', -1)
                    return -1
                i += 1

        if i >= n:
            self.logger.log_exit('_skip_params_and_return_type', -1)
            return -1

        # 如果遇到'=>'，跳过到'{'或表达式结束
        if stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
            self.logger.debug('发现箭头函数')
            i += 2
            while i < n and stripped[i] in ' \t\n\r':
                i += 1
            if i < n and stripped[i] == '{':
                self.logger.debug(f'找到箭头函数体: {i}')
                self.logger.log_exit('_skip_params_and_return_type', i)
                return i
            else:
                self.logger.debug('箭头函数表达式体，无花括号')
                self.logger.log_exit('_skip_params_and_return_type', -1)
                return -1

        # 普通方法体
        if stripped[i] == '{':
            self.logger.debug(f'找到普通方法体: {i}')
            self.logger.log_exit('_skip_params_and_return_type', i)
            return i

        self.logger.debug(f'未找到方法体，当前位置: {i}, 字符: {stripped[i] if i < n else "EOF"}')
        self.logger.log_exit('_skip_params_and_return_type', -1)
        return -1

    @timed
    def _parse_calls(self, method_body_stripped: str, method_name: str,
                     class_name: str, file_path: str, line_number: int):
        """在stripped方法体上解析调用关系（支持嵌套调用深度分析）
        
        Args:
            method_body_stripped: 方法体内容
            method_name: 方法名
            class_name: 类名
            file_path: 文件路径
            line_number: 方法开始行号
        """
        self.logger.log_entry('_parse_calls',
                              method_name=method_name,
                              class_name=class_name,
                              body_length=len(method_body_stripped))
        
        if not method_body_stripped:
            self.logger.debug('方法体为空，跳过')
            self.logger.log_exit('_parse_calls')
            return

        call_count = 0
        
        # 计算调用深度（通过分析括号嵌套）
        paren_depth = 0
        depths = []
        for ch in method_body_stripped:
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1
            depths.append(paren_depth)

        for match in self.call_pattern.finditer(method_body_stripped):
            obj_name = match.group(1)
            callee = match.group(2)
            pos = match.start()
            call_depth = depths[pos] if pos < len(depths) else 0

            # 跳过SKIP_IDENTIFIERS
            if callee in self.SKIP_IDENTIFIERS:
                if obj_name and callee in {'get', 'set', 'delete', 'has', 'of', 'entries', 'keys', 'values', 'forEach', 'map', 'filter', 'reduce', 'find', 'some', 'every', 'includes', 'indexOf', 'slice', 'splice', 'push', 'pop', 'shift', 'unshift', 'join', 'split', 'trim', 'toString', 'toFixed', 'stringify', 'parse', 'json', 'then', 'catch', 'finally', 'next', 'done', 'value', 'ok', 'status', 'length', 'count', 'round', 'min', 'max', 'abs', 'floor', 'ceil', 'random', 'sort', 'reverse', 'concat', 'flat', 'fill', 'copyWithin', 'entries'}:
                    pass
                else:
                    continue

            # 跳过数字开头的obj_name
            if obj_name and re.match(r'^\d', obj_name):
                continue

            # 跳过单字母变量
            if obj_name and len(obj_name) == 1 and obj_name.islower():
                continue

            # 计算行号
            call_line = line_number + method_body_stripped[:match.start()].count('\n')

            self.calls.append(CallRelation(
                caller=method_name,
                caller_class=class_name,
                callee=callee,
                callee_class=obj_name if obj_name and obj_name != 'this' else '',
                file=file_path,
                line_number=call_line,
                call_depth=call_depth
            ))
            self.logger.debug(f'添加调用: {class_name}.{method_name} -> {callee} (obj={obj_name}, depth={call_depth})')
            call_count += 1

        self.logger.info(f'方法调用解析完成: {call_count} 个调用')
        self.logger.log_exit('_parse_calls')

    def _parse_top_level_functions(self, stripped: str, content: str, file_path: str):
        """解析顶层函数
        
        Args:
            stripped: 处理后的代码
            content: 原始代码
            file_path: 文件路径
        """
        self.logger.log_entry('_parse_top_level_functions', file_path=file_path)
        
        func_count = 0
        for match in self.top_func_pattern.finditer(stripped):
            func_name = match.group(3)
            line_number = content[:match.start()].count('\n') + 1
            is_async = match.group(2) is not None
            
            self.methods.append(MethodInfo(
                name=func_name, class_name='',
                file=file_path, line_number=line_number,
                is_async=is_async
            ))
            self.logger.debug(f'添加顶层函数: {func_name} (async={is_async})')
            func_count += 1

        self.logger.info(f'顶层函数解析完成: {func_count} 个函数')
        self.logger.log_exit('_parse_top_level_functions')

    @timed
    def _resolve_callee_classes(self):
        """后处理：推断callee_class"""
        self.logger.log_entry('_resolve_callee_classes')
        
        # 构建类→方法映射
        self.logger.debug('构建类方法映射...')
        class_methods = {}
        for cls in self.classes:
            methods = set()
            for m in self.methods:
                if m.class_name == cls.name:
                    methods.add(m.name)
            class_methods[cls.name] = methods
        
        # 提取成员变量类型
        self.logger.debug('提取成员变量类型...')
        member_types = self._extract_member_types()
        
        resolved_count = 0
        
        for call in self.calls:
            if call.callee_class:
                # 已有推断，验证并优化
                if call.callee_class not in self._all_class_names:
                    resolved = member_types.get(call.caller_class, {}).get(call.callee_class, '')
                    if resolved and resolved in self._all_class_names:
                        call.callee_class = resolved
                        resolved_count += 1
                    elif not call.callee_class[0].isupper():
                        call.callee_class = ''
                continue

            # 规则1: callee本身是类名
            if call.callee in self._all_class_names:
                call.callee_class = call.callee
                resolved_count += 1
                continue

            # 规则2: callee是当前类的已知方法 → 同类调用
            if call.callee in class_methods.get(call.caller_class, set()):
                call.callee_class = call.caller_class
                resolved_count += 1
                continue
            
            # 规则3: callee是当前类的成员变量名 → 推断为变量类型
            var_type = member_types.get(call.caller_class, {}).get(call.callee, '')
            if var_type and var_type in self._all_class_names:
                call.callee_class = var_type
                resolved_count += 1
                continue
        
        self.logger.info(f'被调用类解析完成: 解析了 {resolved_count} 个调用')
        self.logger.log_exit('_resolve_callee_classes')
    
    @timed
    def _extract_member_types(self) -> Dict[str, Dict[str, str]]:
        """从类体中提取成员变量的类型信息
        
        Returns:
            类名 -> {变量名: 类型名} 的映射
        """
        self.logger.log_entry('_extract_member_types')
        
        result = {}
        
        for cls in self.classes:
            self.logger.debug(f'提取类成员类型: {cls.name}')
            member_map = {}
            
            try:
                with open(cls.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f'读取文件失败: {cls.file}, 错误: {str(e)}')
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
                self.logger.debug(f'类 {cls.name} 的成员: {member_map}')
        
        self.logger.info(f'成员类型提取完成: {len(result)} 个类')
        self.logger.log_exit('_extract_member_types', result)
        return result
    
    def _scan_members_in_body(self, body: str, pattern, member_map: Dict):
        """在类体中扫描成员变量（只在花括号深度=1时）
        
        Args:
            body: 类体内容
            pattern: 成员变量正则
            member_map: 成员变量映射（输出）
        """
        self.logger.log_entry('_scan_members_in_body')
        
        # 预计算每个位置的深度
        depths = []
        d = 0
        for ch in body:
            if ch == '{': d += 1
            elif ch == '}': d -= 1
            depths.append(d)
        
        count = 0
        for m in pattern.finditer(body):
            pos = m.start()
            if depths[pos] == 1:
                var_name = m.group(2)
                type_name = m.group(3)
                if var_name not in self.JS_KEYWORDS and type_name not in self.JS_KEYWORDS:
                    if type_name[0].isupper():
                        member_map[var_name] = type_name
                        count += 1
        
        self.logger.debug(f'扫描到 {count} 个成员变量')
        self.logger.log_exit('_scan_members_in_body')

    @timed
    def _extract_component_relations(self):
        """后处理：提取组件嵌套关系（去重）"""
        self.logger.log_entry('_extract_component_relations')
        
        seen = set()
        relation_count = 0

        for class_info in self.classes:
            if not class_info.is_component:
                continue

            self.logger.debug(f'提取组件关系: {class_info.name}')
            
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
                        self.logger.debug(f'添加组件关系: {class_info.name} -> {callee}')
                        relation_count += 1

        self.logger.info(f'组件关系提取完成: {relation_count} 个关系')
        self.logger.log_exit('_extract_component_relations')

    def _record_error(self, file: str, line_number: int, error_type: str, message: str):
        """记录解析错误
        
        Args:
            file: 文件路径
            line_number: 行号
            error_type: 错误类型
            message: 错误消息
        """
        import traceback
        stack_trace = traceback.format_exc()
        
        error = ParseError(
            file=file,
            line_number=line_number,
            error_type=error_type,
            message=message,
            stack_trace=stack_trace
        )
        self.parse_errors.append(error)
        self.logger.error(f'解析错误 [{error_type}]: {file}:{line_number} - {message}')

    def _get_result(self) -> Dict:
        """获取解析结果
        
        Returns:
            解析结果字典
        """
        self.logger.log_entry('_get_result')
        
        result = {
            'files': self.files,
            'classes': self.classes,
            'methods': self.methods,
            'calls': self.calls,
            'component_relations': self.component_relations,
            'inherits': self.inherits,
            'parse_errors': self.parse_errors,
            'circular_dependencies': self._circular_detector.detect_cycles()
        }
        
        self.logger.info(f'解析结果统计:')
        self.logger.info(f'  文件: {len(self.files)}')
        self.logger.info(f'  类: {len(self.classes)}')
        self.logger.info(f'  方法: {len(self.methods)}')
        self.logger.info(f'  调用关系: {len(self.calls)}')
        self.logger.info(f'  组件关系: {len(self.component_relations)}')
        self.logger.info(f'  继承关系: {len(self.inherits)}')
        self.logger.info(f'  解析错误: {len(self.parse_errors)}')
        
        self.logger.log_exit('_get_result', list(result.keys()))
        return result


# ============================================================================
# AI查询接口
# ============================================================================

class AIQueryInterface:
    """AI查询接口（增强版）
    
    使用硅基流动Qwen2.5-7B模型将自然语言转换为SQL
    """
    
    def __init__(self, api_key: str, db_manager: DatabaseManager):
        self.logger = get_logger()
        self.logger.log_entry('AIQueryInterface.__init__')
        
        if not _HAS_OPENAI:
            error_msg = "openai package is required for AIQueryInterface. Install with: pip install openai"
            self.logger.error(error_msg)
            raise ImportError(error_msg)
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"
        )
        self.db = db_manager
        self.model = "Qwen/Qwen2.5-7B-Instruct"
        
        self.logger.info(f'AI查询接口初始化完成，模型: {self.model}')
        self.logger.log_exit('AIQueryInterface.__init__')
    
    @timed
    def text_to_sql(self, question: str) -> str:
        """将自然语言问题转换为SQL语句
        
        Args:
            question: 自然语言问题
            
        Returns:
            SQL语句
        """
        self.logger.log_entry('text_to_sql', question=question[:50])
        
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
            self.logger.debug('发送请求到AI模型...')
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            sql = response.choices[0].message.content.strip()
            self.logger.debug(f'AI返回原始SQL: {sql[:100]}...')
            
            # 清理SQL语句
            sql = self._clean_sql(sql)
            self.logger.info(f'转换后的SQL: {sql[:100]}...')
            
            self.logger.log_exit('text_to_sql', sql[:50])
            return sql
            
        except Exception as e:
            error_msg = f"-- 错误: {str(e)}"
            self.logger.error(f'SQL转换失败: {str(e)}')
            self.logger.log_exit('text_to_sql', error_msg)
            return error_msg
    
    def _clean_sql(self, sql: str) -> str:
        """清理SQL语句
        
        Args:
            sql: 原始SQL
            
        Returns:
            清理后的SQL
        """
        self.logger.log_entry('_clean_sql')
        
        # 移除markdown代码块标记
        sql = re.sub(r'^```sql\s*', '', sql)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'\s*```$', '', sql)
        
        # 移除多余空白
        sql = sql.strip()
        
        # 确保以分号结尾
        if not sql.endswith(';'):
            sql += ';'
        
        self.logger.log_exit('_clean_sql', sql[:50])
        return sql
    
    @timed
    def ask(self, question: str) -> Dict:
        """执行自然语言查询
        
        Args:
            question: 自然语言问题
            
        Returns:
            查询结果字典
        """
        self.logger.log_entry('ask', question=question[:50])
        
        # 转换为SQL
        sql = self.text_to_sql(question)
        
        # 执行查询
        try:
            self.logger.debug('执行SQL查询...')
            results = self.db.execute_query(sql)
            
            # 获取列名
            columns = []
            cursor = self.db.conn.cursor()
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
            
            result = {
                'question': question,
                'sql': sql,
                'columns': columns,
                'results': results,
                'row_count': len(results),
                'success': True
            }
            self.logger.info(f'查询成功，返回 {len(results)} 行')
            self.logger.log_exit('ask', result.keys())
            return result
            
        except Exception as e:
            result = {
                'question': question,
                'sql': sql,
                'error': str(e),
                'success': False
            }
            self.logger.error(f'查询失败: {str(e)}')
            self.logger.log_exit('ask', result.keys())
            return result
    
    def format_result(self, result: Dict) -> str:
        """格式化查询结果
        
        Args:
            result: 查询结果字典
            
        Returns:
            格式化后的字符串
        """
        self.logger.log_entry('format_result')
        
        if not result['success']:
            output = f"查询失败: {result.get('error', '未知错误')}\nSQL: {result['sql']}"
            self.logger.log_exit('format_result', output[:50])
            return output
        
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
        
        formatted = "\n".join(output)
        self.logger.log_exit('format_result', formatted[:50])
        return formatted


# ============================================================================
# 知识图谱构建器
# ============================================================================

class KnowledgeGraphBuilder:
    """知识图谱构建器（增强版）
    
    整合解析器和数据库，构建完整的代码知识图谱
    """
    
    def __init__(self, db_path: str = "code_v2.db", log_level: int = logging.INFO):
        self.logger = init_logger(log_level)
        self.logger.log_entry('KnowledgeGraphBuilder.__init__', db_path=db_path)
        
        self.db = DatabaseManager(db_path)
        self.parser = ArkTSParser(log_level)
        
        self.logger.info('知识图谱构建器初始化完成')
        self.logger.log_exit('KnowledgeGraphBuilder.__init__')
    
    @timed
    def build(self, project_path: str) -> Dict:
        """构建知识图谱
        
        Args:
            project_path: 项目路径
            
        Returns:
            统计信息字典
        """
        self.logger.log_entry('KnowledgeGraphBuilder.build', project_path=project_path)
        
        print(f"开始构建知识图谱: {project_path}")
        self.logger.info(f'开始构建知识图谱: {project_path}')
        
        # 连接数据库
        self.logger.info('连接数据库...')
        self.db.connect()
        self.db.create_tables()
        self.db.clear_tables()
        
        # 解析项目
        print("正在解析项目...")
        self.logger.info('开始解析项目...')
        result = self.parser.parse_project(project_path)
        
        # 存储到数据库
        print("正在存储到数据库...")
        self.logger.info('开始存储到数据库...')
        self._store_result(result)
        
        # 获取统计信息
        stats = self.db.get_statistics()
        
        # 打印统计信息
        print("\n构建完成！统计信息:")
        print(f"  文件数: {stats['files']}")
        print(f"  类数: {stats['classes']}")
        print(f"  组件数: {stats['components']}")
        print(f"  入口组件数: {stats['entry_components']}")
        print(f"  方法数: {stats['methods']}")
        print(f"  调用关系数: {stats['call_relations']}")
        print(f"  组件嵌套关系数: {stats['component_relations']}")
        print(f"  继承关系数: {stats['inherit_relations']}")
        print(f"  解析错误数: {stats['parse_errors']}")
        
        # 打印循环依赖信息
        if result.get('circular_dependencies'):
            print(f"\n警告: 发现 {len(result['circular_dependencies'])} 个循环依赖")
            for cycle in result['circular_dependencies']:
                print(f"  循环: {' -> '.join(cycle)}")
        
        # 打印日志统计
        log_stats = self.logger.get_stats()
        print(f"\n日志统计:")
        print(f"  DEBUG: {log_stats['debug']}")
        print(f"  INFO: {log_stats['info']}")
        print(f"  WARNING: {log_stats['warning']}")
        print(f"  ERROR: {log_stats['error']}")
        print(f"  总计: {log_stats['total']}")
        
        self.logger.info('知识图谱构建完成')
        self.logger.log_exit('KnowledgeGraphBuilder.build', stats)
        
        return stats
    
    @timed
    def _store_result(self, result: Dict):
        """存储解析结果到数据库
        
        Args:
            result: 解析结果字典
        """
        self.logger.log_entry('_store_result')
        
        # 存储文件
        self.logger.debug('存储文件...')
        for file_info in result['files']:
            self.db.insert_file(file_info)
        
        # 存储类
        self.logger.debug('存储类...')
        for class_info in result['classes']:
            self.db.insert_class(class_info)
        
        # 存储方法
        self.logger.debug('存储方法...')
        for method_info in result['methods']:
            self.db.insert_method(method_info)
        
        # 存储调用关系
        self.logger.debug('存储调用关系...')
        for call in result['calls']:
            self.db.insert_call(call)
        
        # 存储组件关系
        self.logger.debug('存储组件关系...')
        for comp in result['component_relations']:
            self.db.insert_component_relation(comp)
        
        # 存储继承关系
        self.logger.debug('存储继承关系...')
        for inherit in result['inherits']:
            self.db.insert_inherit(inherit)
        
        # 存储解析错误
        self.logger.debug('存储解析错误...')
        for error in result.get('parse_errors', []):
            self.db.insert_parse_error(error)
        
        self.db.conn.commit()
        self.logger.info('所有数据已存储到数据库')
        self.logger.log_exit('_store_result')
    
    def close(self):
        """关闭数据库连接"""
        self.logger.log_entry('KnowledgeGraphBuilder.close')
        self.db.close()
        self.logger.info('数据库连接已关闭')
        self.logger.log_exit('KnowledgeGraphBuilder.close')


# ============================================================================
# 便捷函数
# ============================================================================

def build_knowledge_graph(project_path: str, db_path: str = "code_v2.db", 
                          log_level: int = logging.INFO) -> KnowledgeGraphBuilder:
    """构建知识图谱的便捷函数
    
    Args:
        project_path: 项目路径
        db_path: 数据库路径
        log_level: 日志级别
        
    Returns:
        KnowledgeGraphBuilder实例
    """
    logger = init_logger(log_level)
    logger.log_entry('build_knowledge_graph', project_path=project_path, db_path=db_path)
    
    builder = KnowledgeGraphBuilder(db_path, log_level)
    builder.build(project_path)
    
    logger.log_exit('build_knowledge_graph')
    return builder


def ask_ai(question: str, api_key: str, db_path: str = "code_v2.db",
           log_level: int = logging.INFO) -> Dict:
    """AI查询的便捷函数
    
    Args:
        question: 查询问题
        api_key: API密钥
        db_path: 数据库路径
        log_level: 日志级别
        
    Returns:
        查询结果字典
    """
    logger = init_logger(log_level)
    logger.log_entry('ask_ai', question=question[:50])
    
    db = DatabaseManager(db_path)
    db.connect()
    
    ai = AIQueryInterface(api_key, db)
    result = ai.ask(question)
    
    db.close()
    
    logger.log_exit('ask_ai', result.keys())
    return result


# ============================================================================
# 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ArkTS代码知识图谱系统 V2 (增强版)")
    parser.add_argument("command", choices=["build", "query", "stats"],
                       help="命令: build构建图谱, query查询, stats统计")
    parser.add_argument("--project", "-p", help="项目路径")
    parser.add_argument("--db", "-d", default="code_v2.db", help="数据库路径")
    parser.add_argument("--question", "-q", help="查询问题")
    parser.add_argument("--api-key", "-k", help="硅基流动API密钥")
    parser.add_argument("--log-level", "-l", 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help="日志级别 (默认: INFO)")
    parser.add_argument("--debug", action="store_true", 
                       help="开启DEBUG日志 (等同于 --log-level DEBUG)")

    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        log_level = log_level_map.get(args.log_level, logging.INFO)
    
    # 初始化日志
    logger = init_logger(log_level)
    logger.info(f"日志级别设置为: {args.log_level if not args.debug else 'DEBUG'}")
    
    if args.command == "build":
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            logger.error("缺少项目路径参数")
            exit(1)
        
        logger.info("开始构建命令")
        builder = KnowledgeGraphBuilder(args.db, log_level)
        builder.build(args.project)
        builder.close()
        logger.info("构建命令完成")
        
    elif args.command == "query":
        if not args.question:
            print("错误: 需要指定查询问题 --question")
            logger.error("缺少查询问题参数")
            exit(1)
        if not args.api_key:
            print("错误: 需要指定API密钥 --api-key")
            logger.error("缺少API密钥参数")
            exit(1)
        
        logger.info("开始查询命令")
        result = ask_ai(args.question, args.api_key, args.db, log_level)
        
        db = DatabaseManager(args.db)
        db.connect()
        ai = AIQueryInterface(args.api_key, db)
        print(ai.format_result(result))
        db.close()
        logger.info("查询命令完成")
        
    elif args.command == "stats":
        logger.info("开始统计命令")
        db = DatabaseManager(args.db)
        db.connect()
        stats = db.get_statistics()
        
        print("\n知识图谱统计信息:")
        print("=" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        db.close()
        logger.info("统计命令完成")
