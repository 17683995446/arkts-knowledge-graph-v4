#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS→SQLite 代码知识图谱系统
基于第一性原理设计：将代码视为实体-关系系统，实现极简、高效、零成本的代码知识图谱

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
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

# 全局调试日志
_logger = logging.getLogger('arkts_kg')
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('[%(levelname)s %(funcName)s:%(lineno)d] %(message)s'))
_logger.addHandler(_handler)
_logger.setLevel(logging.WARNING)  # 默认WARNING，通过 --debug 开启DEBUG


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
# 数据库管理
# ============================================================================

class DatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_path: str = "code.db"):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Phase 3: 性能优化 PRAGMA
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA cache_size = -64000")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self.conn.execute("PRAGMA mmap_size = 268435456")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def create_tables(self):
        """创建数据库表结构"""
        cursor = self.conn.cursor()
        
        # 实体表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                line_count INTEGER DEFAULT 0,
                md5_hash TEXT DEFAULT ''
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
                PRIMARY KEY (name, class_name, file, line_number),
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

        # Phase 4 & 5: 新增实体表和关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interfaces (
                name TEXT NOT NULL,
                file TEXT NOT NULL,
                methods TEXT DEFAULT '',
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (name, file)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enums (
                name TEXT NOT NULL,
                file TEXT NOT NULL,
                "values" TEXT DEFAULT '',
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (name, file)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS type_aliases (
                name TEXT NOT NULL,
                file TEXT NOT NULL,
                target_type TEXT DEFAULT '',
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (name, file)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decorators (
                name TEXT NOT NULL,
                dec_type TEXT NOT NULL,
                target_type TEXT NOT NULL DEFAULT '',
                target_name TEXT NOT NULL DEFAULT '',
                target_class TEXT NOT NULL DEFAULT '',
                argument TEXT DEFAULT '',
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (name, target_name, target_class, file, line_number)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                source_file TEXT NOT NULL,
                imported_names TEXT DEFAULT '',
                module_path TEXT NOT NULL,
                is_relative INTEGER DEFAULT 0,
                PRIMARY KEY (source_file, module_path)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_relations (
                relation_type TEXT NOT NULL,
                source_class TEXT NOT NULL,
                source_property TEXT NOT NULL,
                property_type TEXT DEFAULT '',
                key TEXT DEFAULT '',
                file TEXT NOT NULL,
                line_number INTEGER DEFAULT 0,
                PRIMARY KEY (source_class, source_property, file)
            )
        """)

        # 新索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decorators_file ON decorators(file)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_imports_source ON imports(source_file)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_class ON state_relations(source_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interfaces_file ON interfaces(file)")

        self.conn.commit()
    
    def clear_tables(self):
        """清空所有表数据"""
        cursor = self.conn.cursor()
        tables = [
            'calls', 'components', 'inherits', 'methods', 'classes', 'files',
            'interfaces', 'enums', 'type_aliases', 'decorators',
            'imports', 'state_relations'
        ]
        for table in tables:
            cursor.execute(f"DELETE FROM [{table}]")
        self.conn.commit()
    
    def insert_file(self, file_info: FileInfo):
        """插入文件记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO files (path) VALUES (?)",
            (file_info.path,)
        )
    
    def insert_class(self, class_info: ClassInfo):
        """插入类/组件记录"""
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
        """插入方法记录"""
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
    
    # 只允许执行的SQL关键字（安全白名单）
    _ALLOWED_SQL_STARTS = ('SELECT', 'WITH', 'EXPLAIN')

    def execute_query(self, sql: str) -> Tuple[List[Tuple], List[str]]:
        """执行SQL查询（带安全过滤）
        
        Returns:
            (rows, columns): 数据行列表和列名列表
        """
        sql_upper = sql.strip().upper()
        if not any(sql_upper.startswith(kw) for kw in self._ALLOWED_SQL_STARTS):
            raise ValueError(f"只允许执行查询语句(SELECT/WITH/EXPLAIN)，拒绝: {sql[:50]}")
        # 额外检查危险操作
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'ATTACH', 'DETACH']
        if any(kw in sql_upper for kw in dangerous):
            raise ValueError(f"查询中包含不允许的操作: {sql[:50]}")
        # 检查分号（防止多语句注入，如 SELECT ...; DROP TABLE ...）
        # 去除字符串内的分号后检查
        cleaned = re.sub(r"'[^']*'", '', sql)
        cleaned = re.sub(r'"[^"]*"', '', cleaned)
        if ';' in cleaned:
            raise ValueError(f"查询中包含分号，可能存在多语句注入: {sql[:50]}")
        # 检查注释符号（防止注释注入，如 ' OR 1=1; --）
        if '--' in sql:
            raise ValueError(f"查询中包含注释符号，可能存在注入: {sql[:50]}")
        cursor = self.conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return rows, columns
    
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

    def get_extended_statistics(self) -> Optional[Dict]:
        """获取 Phase 4 & 5 扩展统计信息"""
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            stats = {}
            for table in ['interfaces', 'enums', 'type_aliases', 'decorators', 'imports', 'state_relations']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            return stats
        except sqlite3.OperationalError:
            return None


# ============================================================================
# ArkTS代码解析器 (V4.1 - @CustomDialog/@Reusable组件识别 + OpenAI可选依赖)
# ============================================================================

# Unicode标识符模式（支持中文、日文、韩文、$符号）
_ID_PATTERN = r'[\w$\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]+'

class ArkTSParser:
    """ArkTS代码静态解析器 V3

    核心设计变更：所有解析都在stripped内容上操作（stripped = 移除注释和字符串后的内容），
    避免原始内容和stripped内容之间的位置映射问题。行号通过 content[:pos].count('\\n')
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

    def __init__(self):
        # 装饰器正则（支持嵌套括号如 @StorageLink(StorageKeys.THEME)）
        self.decorator_pattern = re.compile(r'@\w+\s*\([^()]*\)')
        # 组件装饰器（@Component, @CustomDialog, @Reusable 都标记为组件）
        self.component_decorator = re.compile(r'@(?:Component|CustomDialog|Reusable)\s*(?:\([^()]*\))?\s*')
        self.entry_decorator = re.compile(r'@Entry\s*(?:\([^()]*\))?\s*')

        # struct正则（支持extends和implements，支持嵌套泛型）
        self.struct_pattern = re.compile(
            r'(export\s+)?(default\s+)?struct\s+(' + _ID_PATTERN + r')\s*(?:<[^{}]*?>\s*)?(?:extends\s+(' + _ID_PATTERN + r'))?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # class正则（支持嵌套泛型）
        self.class_pattern = re.compile(
            r'(export\s+)?(default\s+)?(abstract\s+)?class\s+(' + _ID_PATTERN + r')\s*(?:<[^{}]*?>\s*)?(?:extends\s+(\w+)(?:\s*<[^{}]*?>\s*)?)?\s*(?:implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )

        # method正则（行首锚定，支持abstract/override关键字，支持嵌套泛型）
        # 注意：不包含装饰器匹配，装饰器在 _parse_methods 中预先移除
        self.method_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(async\s+)?(abstract\s+|override\s+)?(' + _ID_PATTERN + r')\s*(?:<[^{}]*?>\s*)?\(',
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
        # 注意：不包含装饰器匹配，装饰器在 _parse_methods 中预先移除
        self.arrow_property_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(' + _ID_PATTERN + r')\s*=\s*\(',
            re.MULTILINE
        )

        # getter/setter访问器正则
        self.accessor_pattern = re.compile(
            r'^[ \t]*(private\s+|public\s+|protected\s+)?(static\s+)?(get|set)\s+(' + _ID_PATTERN + r')\s*\(',
            re.MULTILINE
        )

        # call正则 (支持嵌套泛型方法调用如 get<T<A>>())
        self.call_pattern = re.compile(
            r'(?:(\w+)\s*\.\s*)?(\w+)\s*(?:<[^{};]*?>\s*)?\(',
            re.MULTILINE
        )

        # import正则
        self.import_pattern = re.compile(
            r'import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
            re.MULTILINE
        )

        # 顶层函数正则（支持复杂嵌套泛型）
        self.top_func_pattern = re.compile(
            r'(export\s+)?(async\s+)?function\s+(' + _ID_PATTERN + r')\s*(?:<[^{}]*?>\s*)?\(',
            re.MULTILINE
        )

        # 存储列表
        self.files: List[FileInfo] = []
        self.classes: List[ClassInfo] = []
        self.methods: List[MethodInfo] = []
        self.calls: List[CallRelation] = []
        self.component_relations: List[ComponentRelation] = []
        self.inherits: List[InheritRelation] = []

        # Phase 4 & 5: 扩展实体和关系
        self.interfaces: list = []
        self.enums: list = []
        self.type_aliases: list = []
        self.decorators: list = []
        self.imports: list = []
        self.state_relations: list = []

        # _component_names, _all_class_names
        self._component_names: Set[str] = set()
        self._all_class_names: Set[str] = set()

    def _strip_comments_and_strings(self, content: str) -> str:
        """移除注释、字符串和正则字面量，保留换行符"""
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
            # 正则字面量 /pattern/flags
            elif c == '/' and i + 1 < n and content[i + 1] != '/' and content[i + 1] != '*':
                # 判断是否为正则字面量（非除法运算符）
                # 如果前面是标识符字符、)、]、}，则为除法
                is_regex = True
                if i > 0:
                    prev = content[i - 1]
                    if prev.isalnum() or prev in '_$)]}':
                        is_regex = False
                if is_regex:
                    result.append(' ')
                    i += 1
                    while i < n and content[i] != '/':
                        if content[i] == '\\' and i + 1 < n:
                            i += 1  # 跳过转义字符
                        if i < n and content[i] == '\n':
                            result.append('\n')
                        i += 1
                    if i < n:
                        i += 1  # 跳过结尾的 /
                    # 跳过flags
                    while i < n and content[i].isalpha():
                        i += 1
                    result.append(' ')
                else:
                    result.append(c)
                    i += 1
            # 模板字符串 `...`
            elif c == '`':
                result.append(' ')
                i += 1
                while i < n and content[i] != '`':
                    if content[i] == '\\' and i + 1 < n:
                        i += 1  # 跳过转义字符
                        result.append(' ')
                    elif content[i] == '$' and i + 1 < n and content[i + 1] == '{':
                        # 模板表达式 ${...}，需要处理嵌套花括号
                        result.append(' ')
                        i += 2  # 跳过 ${
                        brace_depth = 1
                        while i < n and brace_depth > 0:
                            if content[i] == '{':
                                brace_depth += 1
                            elif content[i] == '}':
                                brace_depth -= 1
                                if brace_depth == 0:
                                    i += 1
                                    break
                            elif content[i] == "'" or content[i] == '"':
                                # 跳过模板表达式内的字符串
                                quote = content[i]
                                i += 1
                                while i < n and content[i] != quote:
                                    if content[i] == '\\' and i + 1 < n:
                                        i += 1
                                    i += 1
                            elif content[i] == '`':
                                # 跳过模板表达式内的嵌套模板字符串
                                i += 1
                                while i < n and content[i] != '`':
                                    if content[i] == '\\' and i + 1 < n:
                                        i += 1
                                    i += 1
                            result.append(' ')
                            i += 1
                        continue
                    if i < n and content[i] == '\n':
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
                    if content[i] == '\\' and i + 1 < n:
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
                    if content[i] == '\\' and i + 1 < n:
                        i += 1
                    i += 1
                if i < n:
                    i += 1
                result.append(' ')
            else:
                result.append(c)
                i += 1
        return ''.join(result)

    def _find_matching_brace(self, stripped: str, start: int) -> int:
        """在stripped内容中找到匹配的}，找不到返回-1"""
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
        # 花括号不匹配，返回-1让调用方跳过
        _logger.debug(f"[BRACE] Unmatched brace at pos {start}, returning -1")
        return -1

    def parse_project(self, project_path: str, 
                      exclude_third_party: bool = False,
                      files_override: List = None) -> Dict:
        """解析整个项目 - 两遍解析
        
        Args:
            project_path: 项目根目录路径
            exclude_third_party: 是否启用智能第三方库过滤 (Phase 2)
            files_override: 指定要解析的文件列表（增量解析用）
        """
        project_path = Path(project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {project_path}")

        # 如果指定了文件列表，直接使用（增量解析）
        if files_override is not None:
            arkts_files = files_override
            print(f"增量解析 {len(arkts_files)} 个文件")
        else:
            arkts_files = list(project_path.rglob("*.ets")) + \
                          list(project_path.rglob("*.ts"))

            print(f"找到 {len(arkts_files)} 个ArkTS文件")

            # Phase 2: 智能第三方库过滤
            if exclude_third_party:
                try:
                    from smart_filter import SmartFilter
                    smart_filter = SmartFilter(str(project_path))
                    filtered = smart_filter.filter()
                    arkts_files = [Path(f) for f in filtered]
                    print(f"过滤后保留 {len(arkts_files)} 个业务文件")
                except ImportError:
                    print("警告: smart_filter.py 未找到，跳过第三方库过滤")

        # 第一遍：收集所有类/组件名（不解析方法）
        for file_path in arkts_files:
            if '/node_modules/' in str(file_path) or str(file_path).endswith('/node_modules') or '/.git/' in str(file_path) or str(file_path).endswith('/.git'):
                continue
            self._scan_declarations(str(file_path))

        # 第二遍：完整解析（包括方法，可利用第一遍收集的名称）
        for file_path in arkts_files:
            if '/node_modules/' in str(file_path) or str(file_path).endswith('/node_modules') or '/.git/' in str(file_path) or str(file_path).endswith('/.git'):
                continue
            self._full_parse(str(file_path))

        # 后处理
        self._resolve_callee_classes()
        self._extract_component_relations()

        # Phase 4 & 5: 扩展提取
        self._extract_extended_entities()

        return self._get_result()

    def _scan_declarations(self, file_path: str):
        """第一遍：只收集类/组件声明"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, IOError, UnicodeDecodeError) as e:
            _logger.warning(f"[SCAN] 无法读取文件 {file_path}: {type(e).__name__}")
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

    def _full_parse(self, file_path: str):
        """第二遍：完整解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, IOError, UnicodeDecodeError) as e:
            _logger.warning(f"[PARSE] 无法读取文件 {file_path}: {type(e).__name__}")
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
                    # 过滤：关键字、自身名、单字母（泛型参数如T/U/V）
                    if (iface_name not in self.JS_KEYWORDS 
                        and iface_name != name 
                        and len(iface_name) > 1):
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

            # 同名同文件时，不重复添加类声明，但仍解析方法
            is_duplicate = any(c.name == name and c.file == file_path for c in self.classes)
            if not is_duplicate:
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
                        # 过滤：关键字、自身名、单字母（泛型参数如T/U/V）
                        if (iface_name not in self.JS_KEYWORDS 
                            and iface_name != name 
                            and len(iface_name) > 1):
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
        if close == -1:
            return ''
        return stripped[open_brace:close + 1]

    def _parse_methods(self, body_stripped: str, class_name: str, file_path: str,
                       class_line: int):
        """在stripped类体上解析方法（包括箭头函数属性）"""
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

            # 跳过: JS_KEYWORDS, ARKTS_KEYWORDS, constructor, UI_COMPONENTS, UI_CHAIN_PROPERTIES
            if method_name in self.JS_KEYWORDS or method_name in self.ARKTS_KEYWORDS:
                if method_name not in METHOD_SAFE_KEYWORDS:
                    continue
            if method_name == 'constructor':
                continue
            if method_name in self.UI_COMPONENTS:
                continue
            if method_name in self.UI_CHAIN_PROPERTIES and method_name not in ARKTS_LIFECYCLE:
                continue
            # 跳过已知组件名（在build体中使用的组件不是方法定义）
            if method_name in self._component_names and method_name != class_name:
                continue
            # 跳过已知类名（同理）
            if method_name in self._all_class_names and method_name != class_name:
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
            if close_pos == -1:
                _logger.debug(f"[METHOD] '{class_name}.{method_name}' -> unmatched brace in body")
                continue
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            _logger.debug(f"[METHOD] '{class_name}.{method_name}' body: {len(method_body_stripped)} chars")
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

        # 2. 匹配箭头函数属性（如 on = (event) => { ... }）
        for match in self.arrow_property_pattern.finditer(body_no_dec):
            # 跳过已匹配的位置
            if match.start() in matched_positions:
                continue

            method_name = match.group(3)  # group(3) = 属性名

            # 只匹配类体顶层（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            # 跳过: JS_KEYWORDS, ARKTS_KEYWORDS, constructor, UI_COMPONENTS, UI_CHAIN_PROPERTIES
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

            # 提取箭头函数体
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
            if brace_pos == -1:
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            if close_pos == -1:
                continue
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

        # 3. 匹配getter/setter访问器
        for match in self.accessor_pattern.finditer(body_no_dec):
            accessor_type = match.group(3)  # 'get' 或 'set'
            prop_name = match.group(4)  # 属性名
            method_name = f"{accessor_type}_{prop_name}"  # 如 get_value, set_value

            # 只匹配类体顶层（深度=1）
            match_depth = depth_at_pos.get(match.start(), 0)
            if match_depth != 1:
                continue

            # 跳过已匹配的位置
            if match.start() in matched_positions:
                continue

            line_number = class_line + body_no_dec[:match.start()].count('\n')
            is_static = bool(match.group(2))
            is_private = match.group(1) is not None and 'private' in match.group(1)

            self.methods.append(MethodInfo(
                name=method_name, class_name=class_name,
                file=file_path, line_number=line_number,
                is_static=is_static, is_private=is_private
            ))
            _logger.debug(f"[METHOD] '{class_name}.{method_name}' L{line_number} accessor={accessor_type}")

            # 提取accessor体
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(body_no_dec, paren_pos)
            if brace_pos == -1:
                continue

            close_pos = self._find_matching_brace(body_no_dec, brace_pos)
            if close_pos == -1:
                continue
            method_body_stripped = body_no_dec[brace_pos:close_pos + 1]
            self._parse_calls(method_body_stripped, method_name, class_name,
                              file_path, line_number)

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
            paren_count = 0
            while i < n:
                if stripped[i] == '<':
                    angle_count += 1
                elif stripped[i] == '>':
                    if angle_count > 0:
                        angle_count -= 1
                elif stripped[i] == '(' and angle_count <= 0:
                    paren_count += 1
                elif stripped[i] == ')' and angle_count <= 0:
                    paren_count -= 1
                elif stripped[i] == '{' and angle_count <= 0 and paren_count <= 0:
                    if brace_count == 0:
                        return i
                    brace_count += 1
                elif stripped[i] == '}' and angle_count <= 0 and paren_count <= 0:
                    brace_count -= 1
                elif stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>' and angle_count <= 0 and paren_count <= 0:
                    # 返回类型中的箭头函数，如 () => void
                    # 跳过 => 后面的表达式直到 , ; { 或 )
                    i += 2
                    while i < n and stripped[i] not in ',;{})':
                        if stripped[i] == '(':
                            # 嵌套箭头函数参数，如 (output: string) => boolean
                            nested_paren = 1
                            i += 1
                            while i < n and nested_paren > 0:
                                if stripped[i] == '(':
                                    nested_paren += 1
                                elif stripped[i] == ')':
                                    nested_paren -= 1
                                i += 1
                            # 跳过 => 和后续表达式
                            while i < n and stripped[i] in ' \t\n\r':
                                i += 1
                            if i < n and stripped[i] == '=' and i + 1 < n and stripped[i + 1] == '>':
                                i += 2
                                while i < n and stripped[i] not in ',;{})':
                                    i += 1
                        else:
                            i += 1
                    continue
                elif stripped[i] == ';' and angle_count <= 0 and brace_count == 0 and paren_count <= 0:
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

    def _parse_top_level_functions(self, stripped: str, content: str, file_path: str):
        """解析顶层函数及其调用关系"""
        for match in self.top_func_pattern.finditer(stripped):
            func_name = match.group(3)
            line_number = content[:match.start()].count('\n') + 1
            self.methods.append(MethodInfo(
                name=func_name, class_name='',
                file=file_path, line_number=line_number
            ))
            _logger.debug(f"[TOP_FUNC] '{func_name}' L{line_number}")

            # 提取顶层函数体并解析其中的调用关系
            paren_pos = match.end() - 1
            brace_pos = self._skip_params_and_return_type(stripped, paren_pos)
            if brace_pos == -1:
                _logger.debug(f"[TOP_FUNC] '{func_name}' -> no body found")
                continue

            close_pos = self._find_matching_brace(stripped, brace_pos)
            if close_pos == -1:
                _logger.debug(f"[TOP_FUNC] '{func_name}' -> unmatched brace in body")
                continue
            func_body_stripped = stripped[brace_pos:close_pos + 1]
            _logger.debug(f"[TOP_FUNC] '{func_name}' body: {len(func_body_stripped)} chars")
            self._parse_calls(func_body_stripped, func_name, '', file_path, line_number)

    def _resolve_callee_classes(self):
        """后处理：推断callee_class（Phase 3.2: O(N) 哈希表优化）"""
        # 1. 构建 O(1) 查找表: class_name -> {method_names}
        class_methods: Dict[str, Set[str]] = {}
        for m in self.methods:
            class_methods.setdefault(m.class_name, set()).add(m.name)

        # 2. 提取成员变量类型: class_name -> {var_name -> type_name}
        member_types = self._extract_member_types()

        # 3. 单次遍历 calls 列表，O(N)
        for call in self.calls:
            if call.callee_class:
                # 已有推断，验证并优化
                if call.callee_class not in self._all_class_names:
                    resolved = member_types.get(call.caller_class, {}).get(call.callee_class, '')
                    if resolved and resolved in self._all_class_names:
                        call.callee_class = resolved
                    elif call.callee_class and not call.callee_class[0].isupper():
                        call.callee_class = ''
                continue

            # 规则1: callee本身是类名 → O(1) set lookup
            if call.callee in self._all_class_names:
                call.callee_class = call.callee
                continue

            # 规则2: callee是当前类的已知方法 → O(1) set lookup
            if call.callee in class_methods.get(call.caller_class, set()):
                call.callee_class = call.caller_class
                continue

            # 规则3: callee_class是成员变量名 → O(1) dict lookup
            var_type = member_types.get(call.caller_class, {}).get(call.callee_class, '')
            if var_type and var_type in self._all_class_names:
                call.callee_class = var_type
                continue
    
    def _extract_member_types(self) -> Dict[str, Dict[str, str]]:
        """从类体中提取成员变量的类型信息"""
        result = {}
        
        for cls in self.classes:
            member_map = {}
            
            try:
                with open(cls.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, IOError, UnicodeDecodeError) as e:
                _logger.warning(f"[MEMBER_TYPE] 无法读取文件 {cls.file}: {type(e).__name__}")
                continue
            
            stripped = self._strip_comments_and_strings(content)
            
            # 成员变量模式 - 支持泛型类型、联合类型、可选类型、函数类型
            member_pattern = re.compile(
                r'(private|public|protected)?\s*'
                r'(?:static\s+)?'
                r'(\w+)\s*:\s*'
                r'([\w<>,\s|&?()]+\w)'  # 捕获类型表达式（含联合|、可选?、泛型<>、函数()）
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
    
    def _scan_members_in_body(self, body: str, pattern, member_map: Dict):
        """在类体中扫描成员变量（只在花括号深度=1时）"""
        # 预计算每个位置的深度（单次遍历）
        depths = []
        d = 0
        for ch in body:
            if ch == '{':
                d += 1
            elif ch == '}':
                d -= 1
            depths.append(d)
        
        for m in pattern.finditer(body):
            pos = m.start()
            if depths[pos] == 1:
                var_name = m.group(2)
                type_expr = m.group(3).strip()
                if var_name not in self.JS_KEYWORDS:
                    # 从类型表达式中提取第一个大写开头的标识符作为类型名
                    # 处理联合类型 string | number | MyClass、可选类型 MyClass?、泛型 List<MyClass>
                    type_name = ''
                    # 尝试提取大写开头的类名
                    type_candidates = re.findall(r'\b([A-Z]\w*)', type_expr)
                    for candidate in type_candidates:
                        if candidate not in self.JS_KEYWORDS and candidate not in self.ARKTS_KEYWORDS:
                            type_name = candidate
                            break
                    if type_name:
                        member_map[var_name] = type_name

    def _extract_component_relations(self):
        """后处理：提取组件嵌套关系（去重）
        
        从多个来源提取组件关系：
        1. build() 方法中的组件使用
        2. @Builder 装饰的方法中的组件使用
        3. ForEach/LazyForEach 闭包中的组件使用
        """
        seen = set()

        for class_info in self.classes:
            if not class_info.is_component:
                continue

            # 收集该组件所有方法中的调用
            class_calls = [
                c for c in self.calls
                if c.caller_class == class_info.name
            ]

            for call in class_calls:
                callee = call.callee
                # 跳过UI链式属性方法
                if callee in self.UI_CHAIN_PROPERTIES:
                    continue
                # 跳过JS全局方法
                if callee in self.JS_GLOBALS:
                    continue

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
                        _logger.debug(f"[COMP_REL] {class_info.name} -> {callee} (from {call.caller})")

    def _extract_extended_entities(self):
        """Phase 4 & 5: 提取扩展实体和关系"""
        try:
            from extended_extractors import (
                DecoratorExtractor, EntityTypeExtractor,
                ImportExtractor, StateRelationExtractor,
            )
        except ImportError:
            return

        dec_extractor = DecoratorExtractor()
        entity_extractor = EntityTypeExtractor()
        import_extractor = ImportExtractor()
        state_extractor = StateRelationExtractor()

        for file_path in self.files:
            fp = file_path.path
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, IOError, UnicodeDecodeError) as e:
                _logger.warning(f"[EXT_ENTITY] 无法读取文件 {fp}: {type(e).__name__}")
                continue

            stripped = self._strip_comments_and_strings(content)

            # 接口
            self.interfaces.extend(
                entity_extractor.extract_interfaces(stripped, content, fp))

            # 枚举
            self.enums.extend(
                entity_extractor.extract_enums(stripped, content, fp))

            # 类型别名
            self.type_aliases.extend(
                entity_extractor.extract_type_aliases(stripped, content, fp))

            # Import
            self.imports.extend(
                import_extractor.extract(content, fp))

        # 装饰器和状态关系需要类上下文，在类解析中提取
        for cls in self.classes:
            try:
                with open(cls.file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, IOError, UnicodeDecodeError) as e:
                _logger.warning(f"[DECORATOR] 无法读取文件 {cls.file}: {type(e).__name__}")
                continue

            stripped = self._strip_comments_and_strings(content)

            # 找到该类的 body
            body = self._find_class_body(stripped, cls.name)
            if body is None:
                continue

            # 类级装饰器（@Component, @Entry 等）
            class_decors = dec_extractor.extract_from_file(stripped, content, cls.file)
            for d in class_decors:
                if d.dec_type in ('component_def', 'entry_def', 'dialog_def', 'reusable_def'):
                    d.target_type = 'class'
                    d.target_name = cls.name
                    d.target_class = cls.name
                    self.decorators.append(d)

            # 类体内的装饰器（@State, @Prop, @Watch 等）
            self.decorators.extend(
                dec_extractor.extract_from_class(body, cls.name, cls.file, cls.line_number))

            # 状态管理关系
            self.state_relations.extend(
                state_extractor.extract_from_class(body, cls.name, cls.file, cls.line_number))

    def _find_class_body(self, stripped: str, class_name: str) -> Optional[str]:
        """在 stripped 内容中找到指定类的 body"""
        # 尝试 struct
        for match in self.struct_pattern.finditer(stripped):
            if match.group(3) == class_name:
                return self._extract_body(stripped, match.end() - 1)
        # 尝试 class
        for match in self.class_pattern.finditer(stripped):
            if match.group(4) == class_name:
                return self._extract_body(stripped, match.end() - 1)
        return None

    def _get_result(self) -> Dict:
        return {
            'files': self.files,
            'classes': self.classes,
            'methods': self.methods,
            'calls': self.calls,
            'component_relations': self.component_relations,
            'inherits': self.inherits,
            # Phase 4 & 5
            'interfaces': self.interfaces,
            'enums': self.enums,
            'type_aliases': self.type_aliases,
            'decorators': self.decorators,
            'imports': self.imports,
            'state_relations': self.state_relations,
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
            results, columns = self.db.execute_query(sql)
            
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
# 知识图谱构建器
# ============================================================================

class KnowledgeGraphBuilder:
    """知识图谱构建器
    
    整合解析器和数据库，构建完整的代码知识图谱
    """
    
    BATCH_SIZE = 5000  # Phase 3: 批量写入大小
    
    def __init__(self, db_path: str = "code.db"):
        self.db = DatabaseManager(db_path)
        self.parser = ArkTSParser()
    
    def build(self, project_path: str, exclude_third_party: bool = False,
              incremental: bool = False) -> Dict:
        """构建知识图谱
        
        Args:
            project_path: 项目路径
            exclude_third_party: 是否启用第三方库过滤
            incremental: 是否启用增量解析（只解析变更文件）
        """
        print(f"开始构建知识图谱: {project_path}")
        
        # 连接数据库
        self.db.connect()
        self.db.create_tables()

        # Phase 3.3: 增量解析检测
        files_to_parse = None
        deleted_files = []
        if incremental:
            inc = None
            try:
                from incremental_parser import IncrementalParser
                inc = IncrementalParser(self.db.db_path)
                inc.connect()

                if inc.should_full_rebuild(project_path):
                    print("  增量检测: 需要全量重建")
                else:
                    added, modified, deleted = inc.detect_changes(project_path)
                    inc.print_change_summary(added, modified, deleted)
                    files_to_parse = [Path(f) for f in (added + modified)]
                    deleted_files = deleted

            except ImportError:
                print("警告: incremental_parser.py 未找到，执行全量解析")
            finally:
                if inc:
                    inc.close()

        # 如果增量检测发现无变更，跳过解析
        if incremental and files_to_parse is not None and len(files_to_parse) == 0 and len(deleted_files) == 0:
            print("  无变更，跳过解析")
            stats = self.db.get_statistics()
            return stats

        # 清理删除的文件记录
        if deleted_files:
            for f in deleted_files:
                self.db.conn.execute("DELETE FROM calls WHERE file = ?", (f,))
                self.db.conn.execute("DELETE FROM methods WHERE file = ?", (f,))
                self.db.conn.execute("DELETE FROM classes WHERE file = ?", (f,))
                self.db.conn.execute("DELETE FROM files WHERE path = ?", (f,))
            self.db.conn.commit()
            print(f"  已清理 {len(deleted_files)} 个删除文件的记录")

        # 如果是增量且有变更文件，只解析变更文件
        if files_to_parse is not None and len(files_to_parse) > 0:
            # 增量模式：只删除变更文件的旧记录，不清空整个数据库
            print(f"  增量解析 {len(files_to_parse)} 个变更文件")
            from incremental_parser import IncrementalParser
            inc = IncrementalParser(self.db.db_path)
            inc.conn = self.db.conn  # 复用已有连接
            for f in files_to_parse:
                fpath = str(f)
                inc.delete_file_records(fpath)
                _logger.debug(f"[INCREMENTAL] Deleted records for changed file: {fpath}")
            # 提交删除操作，避免与后续事务冲突
            self.db.conn.commit()
        else:
            # 全量构建：清空表
            self.db.clear_tables()
        
        # 解析项目
        print("正在解析项目...")
        result = self.parser.parse_project(project_path, exclude_third_party=exclude_third_party,
                                            files_override=files_to_parse)
        
        # 存储到数据库（Phase 3: 批量写入 + 事务）
        print("正在存储到数据库...")
        try:
            self.db.conn.execute("BEGIN TRANSACTION")
            self._store_result(result)
            self.db.conn.execute("COMMIT")
        except Exception:
            self.db.conn.execute("ROLLBACK")
            raise
        
        # 更新文件哈希（增量解析用，全量和增量都需要）
        try:
            from incremental_parser import IncrementalParser
            for f in result['files']:
                fhash = IncrementalParser.compute_hash(f.path)
                self.db.conn.execute(
                    "UPDATE files SET md5_hash = ? WHERE path = ?",
                    (fhash, f.path)
                )
            self.db.conn.commit()
        except Exception as e:
            _logger.warning(f"[HASH_UPDATE] 更新文件哈希失败: {e}")
        
        # 获取统计信息
        stats = self.db.get_statistics()
        
        print("\n构建完成！统计信息:")
        print(f"  文件数: {stats['files']}")
        print(f"  类数: {stats['classes']}")
        print(f"  组件数: {stats['components']}")
        print(f"  入口组件数: {stats['entry_components']}")
        print(f"  方法数: {stats['methods']}")
        print(f"  调用关系数: {stats['call_relations']}")
        print(f"  组件嵌套关系数: {stats['component_relations']}")
        print(f"  继承关系数: {stats['inherit_relations']}")
        # Phase 4 & 5 扩展统计
        try:
            ext = self.db.get_extended_statistics()
            if ext:
                print(f"  --- Phase 4 扩展 ---")
                print(f"  接口数: {ext.get('interfaces', 0)}")
                print(f"  枚举数: {ext.get('enums', 0)}")
                print(f"  类型别名数: {ext.get('type_aliases', 0)}")
                print(f"  装饰器数: {ext.get('decorators', 0)}")
                print(f"  --- Phase 5 扩展 ---")
                print(f"  Import数: {ext.get('imports', 0)}")
                print(f"  状态管理关系数: {ext.get('state_relations', 0)}")
        except Exception:
            pass
        
        return stats
    
    def _store_result(self, result: Dict):
        """存储解析结果到数据库（Phase 3: 批量写入优化）"""
        # 文件
        file_data = [(f.path,) for f in result['files']]
        if file_data:
            self.db.conn.executemany(
                "INSERT OR IGNORE INTO files (path) VALUES (?)", file_data)
        
        # 类
        class_data = [
            (c.name, c.file, int(c.is_component), int(c.is_entry), c.line_number)
            for c in result['classes']
        ]
        if class_data:
            self.db.conn.executemany(
                """INSERT OR IGNORE INTO classes 
                   (name, file, is_component, is_entry, line_number) 
                   VALUES (?, ?, ?, ?, ?)""", class_data)
        
        # 方法
        method_data = [
            (m.name, m.class_name, m.file, m.line_number,
             int(m.is_static or False), int(m.is_private or False))
            for m in result['methods']
        ]
        if method_data:
            self.db.conn.executemany(
                """INSERT OR IGNORE INTO methods 
                   (name, class_name, file, line_number, is_static, is_private) 
                   VALUES (?, ?, ?, ?, ?, ?)""", method_data)
        
        # 调用关系
        call_data = [
            (c.caller, c.caller_class, c.callee, c.callee_class,
             c.file, c.line_number)
            for c in result['calls']
        ]
        if call_data:
            self.db.conn.executemany(
                """INSERT OR IGNORE INTO calls 
                   (caller, caller_class, callee, callee_class, file, line_number) 
                   VALUES (?, ?, ?, ?, ?, ?)""", call_data)
        
        # 组件关系
        comp_data = [
            (c.parent, c.child, c.file, c.line_number)
            for c in result['component_relations']
        ]
        if comp_data:
            self.db.conn.executemany(
                """INSERT OR IGNORE INTO components 
                   (parent, child, file, line_number) 
                   VALUES (?, ?, ?, ?)""", comp_data)
        
        # 继承关系
        inherit_data = [
            (i.child_class, i.parent_class, i.file, i.line_number)
            for i in result['inherits']
        ]
        if inherit_data:
            self.db.conn.executemany(
                """INSERT OR IGNORE INTO inherits 
                   (child_class, parent_class, file, line_number) 
                   VALUES (?, ?, ?, ?)""", inherit_data)

        # Phase 4: 接口
        if result.get('interfaces'):
            iface_data = [(i.name, i.file, i.methods, i.line_number) for i in result['interfaces']]
            if iface_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO interfaces (name, file, methods, line_number) 
                       VALUES (?, ?, ?, ?)""", iface_data)

        # Phase 4: 枚举
        if result.get('enums'):
            enum_data = [(e.name, e.file, e.values, e.line_number) for e in result['enums']]
            if enum_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO enums (name, file, "values", line_number) 
                       VALUES (?, ?, ?, ?)""", enum_data)

        # Phase 4: 类型别名
        if result.get('type_aliases'):
            ta_data = [(t.name, t.file, t.target_type, t.line_number) for t in result['type_aliases']]
            if ta_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO type_aliases (name, file, target_type, line_number) 
                       VALUES (?, ?, ?, ?)""", ta_data)

        # Phase 4: 装饰器
        if result.get('decorators'):
            dec_data = [(d.name, d.dec_type, d.target_type, d.target_name,
                        d.target_class, d.argument, d.file, d.line_number)
                       for d in result['decorators']]
            if dec_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO decorators 
                       (name, dec_type, target_type, target_name, target_class, argument, file, line_number) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", dec_data)

        # Phase 5: Import
        if result.get('imports'):
            imp_data = [(i.source_file, i.imported_names, i.module_path, i.is_relative)
                       for i in result['imports']]
            if imp_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO imports 
                       (source_file, imported_names, module_path, is_relative) 
                       VALUES (?, ?, ?, ?)""", imp_data)

        # Phase 5: 状态管理关系
        if result.get('state_relations'):
            sr_data = [(s.relation_type, s.source_class, s.source_property,
                        s.property_type, s.key, s.file, s.line_number)
                       for s in result['state_relations']]
            if sr_data:
                self.db.conn.executemany(
                    """INSERT OR IGNORE INTO state_relations 
                       (relation_type, source_class, source_property, property_type, key, file, line_number) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""", sr_data)
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


# ============================================================================
# 主程序
# ============================================================================

def build_knowledge_graph(project_path: str, db_path: str = "code.db") -> KnowledgeGraphBuilder:
    """构建知识图谱的便捷函数"""
    builder = KnowledgeGraphBuilder(db_path)
    builder.build(project_path)
    return builder


def ask_ai(question: str, api_key: str, db_path: str = "code.db") -> Dict:
    """AI查询的便捷函数"""
    db = DatabaseManager(db_path)
    try:
        db.connect()
        ai = AIQueryInterface(api_key, db)
        result = ai.ask(question)
        return result
    finally:
        db.close()


# ============================================================================
# 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ArkTS代码知识图谱系统")
    parser.add_argument("command", choices=["build", "query", "stats", "validate"],
                       help="命令: build构建图谱, query查询, stats统计, validate验证覆盖率")
    parser.add_argument("--project", "-p", help="项目路径")
    parser.add_argument("--db", "-d", default="code.db", help="数据库路径")
    parser.add_argument("--question", "-q", help="查询问题")
    parser.add_argument("--api-key", "-k", help="硅基流动API密钥")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    parser.add_argument("--filter", action="store_true", help="启用智能第三方库过滤 (Phase 2)")
    parser.add_argument("--incremental", action="store_true", help="启用增量解析 (Phase 3)")

    args = parser.parse_args()

    if args.debug:
        _logger.setLevel(logging.DEBUG)
        _logger.info("调试日志已开启")
    
    if args.command == "build":
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        builder = KnowledgeGraphBuilder(args.db)
        builder.build(args.project, exclude_third_party=args.filter, incremental=args.incremental)
        builder.close()
        
    elif args.command == "validate":
        if not args.project:
            print("错误: 需要指定项目路径 --project")
            exit(1)
        
        try:
            from coverage_validator import CoverageValidator
            validator = CoverageValidator(args.db)
            validator.connect()
            report = validator.validate_all(args.project)
            validator.print_report(report)
            validator.close()
        except ImportError:
            print("错误: coverage_validator.py 未找到")
            exit(1)
        
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
