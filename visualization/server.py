# -*- coding: utf-8 -*-
"""
ArkTS 知识图谱可视化 - Flask 后端服务
提供 REST API 和 WebSocket 接口，用于查询和展示知识图谱数据
"""

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import time
from functools import lru_cache
from threading import Lock, Thread

import requests
from flask import Flask, jsonify, request, Response, send_file, send_from_directory
from flask_cors import CORS

# 静态文件目录（index.html 所在目录）
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
CORS(app)  # 启用跨域支持

# 全局数据库路径，启动时通过命令行参数设置
DB_PATH = "../test_code.db"

# ============================================================
# AI 查询缓存系统
# ============================================================

class QueryCache:
    """LRU查询缓存，支持TTL过期"""

    def __init__(self, max_size=1000, default_ttl=300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.timestamps = {}
        self.lock = Lock()

    def _make_key(self, question, db_path):
        """生成缓存键"""
        key_str = f"{question}:{db_path}:{os.path.getmtime(db_path) if os.path.exists(db_path) else 0}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, question, db_path):
        """获取缓存结果"""
        key = self._make_key(question, db_path)
        with self.lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.default_ttl:
                    return self.cache[key]
                else:
                    # 过期清理
                    del self.cache[key]
                    del self.timestamps[key]
        return None

    def set(self, question, db_path, result):
        """设置缓存结果"""
        key = self._make_key(question, db_path)
        with self.lock:
            # LRU清理
            if len(self.cache) >= self.max_size:
                oldest = min(self.timestamps, key=self.timestamps.get)
                del self.cache[oldest]
                del self.timestamps[oldest]

            self.cache[key] = result
            self.timestamps[key] = time.time()

    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

    def stats(self):
        """返回缓存统计"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": getattr(self, '_hits', 0) / max(getattr(self, '_total', 1), 1)
            }

# 全局查询缓存实例
query_cache = QueryCache(max_size=500, default_ttl=600)  # 500条缓存，10分钟TTL


# ============================================================
# 页面路由
# ============================================================

@app.route("/")
def index():
    """返回前端页面"""
    return send_from_directory(STATIC_DIR, "index.html")


# ============================================================
# 数据库连接工具函数
# ============================================================

def validate_sql(sql: str) -> tuple:
    """验证SQL安全性，返回 (is_safe, error_message)"""
    sql_clean = sql.strip().rstrip(';').strip()

    # 检查是否以安全关键字开头
    safe_prefixes = ('SELECT', 'WITH', 'EXPLAIN')
    if not any(sql_clean.upper().startswith(p) for p in safe_prefixes):
        return False, f"只允许 SELECT/WITH/EXPLAIN 查询，当前以 {sql_clean[:20]} 开头"

    # 检查危险关键字
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
        'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE', 'ATTACH', 'DETACH'
    ]
    sql_upper = sql_clean.upper()
    for kw in dangerous_keywords:
        # 使用单词边界检查，避免误判（如 SELECT中的DELETE列名）
        if re.search(r'\b' + kw + r'\b', sql_upper):
            return False, f"SQL 中包含危险关键字: {kw}"

    # 检查分号（防止多语句注入）
    if ';' in sql_clean:
        return False, "SQL 中不允许分号"

    # 检查注释注入
    if '--' in sql_clean or '/*' in sql_clean:
        return False, "SQL 中不允许注释"

    return True, None


def get_db():
    """获取数据库连接，并启用字典模式（返回字典而非元组）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql, params=()):
    """执行查询并返回结果列表（每行为字典）"""
    conn = get_db()
    try:
        cursor = conn.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    finally:
        conn.close()


def query_db_one(sql, params=()):
    """执行查询并返回单条结果（字典），无结果时返回 None"""
    conn = get_db()
    try:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ============================================================
# API 端点实现
# ============================================================

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    返回知识图谱的统计信息
    包括：文件数、类数、组件数、入口组件数、方法数、调用关系数、组件嵌套关系数、继承关系数
    """
    stats = {
        "file_count": query_db("SELECT COUNT(*) as cnt FROM files")[0]["cnt"],
        "class_count": query_db("SELECT COUNT(*) as cnt FROM classes")[0]["cnt"],
        "component_count": query_db("SELECT COUNT(*) as cnt FROM classes WHERE is_component = 1")[0]["cnt"],
        "entry_count": query_db("SELECT COUNT(*) as cnt FROM classes WHERE is_entry = 1")[0]["cnt"],
        "method_count": query_db("SELECT COUNT(*) as cnt FROM methods")[0]["cnt"],
        "call_count": query_db("SELECT COUNT(*) as cnt FROM calls")[0]["cnt"],
        "component_relation_count": query_db("SELECT COUNT(*) as cnt FROM components")[0]["cnt"],
        "inherit_count": query_db("SELECT COUNT(*) as cnt FROM inherits")[0]["cnt"],
    }
    return jsonify(stats)


@app.route("/api/files", methods=["GET"])
def get_files():
    """返回所有文件列表（path, line_count）"""
    rows = query_db("SELECT path, line_count FROM files ORDER BY path")
    return jsonify(rows)


@app.route("/api/classes", methods=["GET"])
def get_classes():
    """返回所有类/组件（name, file, is_component, is_entry, line_number）"""
    rows = query_db(
        "SELECT name, file, is_component, is_entry, line_number FROM classes ORDER BY name, file"
    )
    return jsonify(rows)


@app.route("/api/methods", methods=["GET"])
def get_methods():
    """
    返回方法列表，支持按 class_name 过滤
    查询参数：class_name - 类名（可选）
    """
    class_name = request.args.get("class_name", "")
    if class_name:
        rows = query_db(
            "SELECT name, class_name, file, line_number, is_static, is_private "
            "FROM methods WHERE class_name = ? ORDER BY name",
            (class_name,),
        )
    else:
        rows = query_db(
            "SELECT name, class_name, file, line_number, is_static, is_private "
            "FROM methods ORDER BY class_name, name"
        )
    return jsonify(rows)


@app.route("/api/calls", methods=["GET"])
def get_calls():
    """返回所有调用关系"""
    rows = query_db(
        "SELECT caller, caller_class, callee, callee_class, file, line_number "
        "FROM calls ORDER BY caller_class, caller, file"
    )
    return jsonify(rows)


@app.route("/api/components", methods=["GET"])
def get_components():
    """返回所有组件嵌套关系"""
    rows = query_db(
        "SELECT parent, child, file, line_number FROM components ORDER BY parent, child"
    )
    return jsonify(rows)


@app.route("/api/inherits", methods=["GET"])
def get_inherits():
    """返回所有继承关系"""
    rows = query_db(
        "SELECT child_class, parent_class, file, line_number "
        "FROM inherits ORDER BY child_class, parent_class"
    )
    return jsonify(rows)


@app.route("/api/class/<name>/detail", methods=["GET"])
def get_class_detail(name):
    """
    返回某个类的详细信息
    包括：类基本信息、方法列表、调用关系、被调用关系、子组件、父组件、继承关系
    """
    # 查询类基本信息
    class_info = query_db(
        "SELECT name, file, is_component, is_entry, line_number "
        "FROM classes WHERE name = ?",
        (name,),
    )
    if not class_info:
        return jsonify({"error": f"未找到类: {name}"}), 404

    # 查询该类的方法
    methods = query_db(
        "SELECT name, file, line_number, is_static, is_private "
        "FROM methods WHERE class_name = ? ORDER BY name",
        (name,),
    )

    # 查询该类发起的调用关系（作为调用者）
    outgoing_calls = query_db(
        "SELECT caller, callee, callee_class, file, line_number "
        "FROM calls WHERE caller_class = ? ORDER BY callee",
        (name,),
    )

    # 查询该类被调用的关系（作为被调用者）
    incoming_calls = query_db(
        "SELECT caller, caller_class, callee, file, line_number "
        "FROM calls WHERE callee_class = ? ORDER BY caller",
        (name,),
    )

    # 查询该类作为父组件包含的子组件
    children = query_db(
        "SELECT child, file, line_number FROM components WHERE parent = ? ORDER BY child",
        (name,),
    )

    # 查询该类作为子组件被哪些父组件包含
    parents = query_db(
        "SELECT parent, file, line_number FROM components WHERE child = ? ORDER BY parent",
        (name,),
    )

    # 查询该类的父类（继承关系）
    parent_classes = query_db(
        "SELECT parent_class, file, line_number "
        "FROM inherits WHERE child_class = ? ORDER BY parent_class",
        (name,),
    )

    # 查询继承自该类的子类
    child_classes = query_db(
        "SELECT child_class, file, line_number "
        "FROM inherits WHERE parent_class = ? ORDER BY child_class",
        (name,),
    )

    result = {
        "class": class_info[0] if class_info else None,
        "methods": methods,
        "outgoing_calls": outgoing_calls,
        "incoming_calls": incoming_calls,
        "children": children,
        "parents": parents,
        "parent_classes": parent_classes,
        "child_classes": child_classes,
    }
    return jsonify(result)


@app.route("/api/search", methods=["GET"])
def search():
    """
    搜索实体（类名、方法名、文件名模糊匹配）
    查询参数：q - 搜索关键词
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "请提供搜索关键词参数 q"}), 400

    like_pattern = f"%{q}%"

    # 在类名中搜索
    matched_classes = query_db(
        "SELECT name, file, is_component, is_entry, line_number "
        "FROM classes WHERE name LIKE ? ORDER BY name",
        (like_pattern,),
    )

    # 在方法名中搜索
    matched_methods = query_db(
        "SELECT name, class_name, file, line_number, is_static, is_private "
        "FROM methods WHERE name LIKE ? ORDER BY name",
        (like_pattern,),
    )

    # 在文件路径中搜索
    matched_files = query_db(
        "SELECT path, line_count FROM files WHERE path LIKE ? ORDER BY path",
        (like_pattern,),
    )

    result = {
        "classes": matched_classes,
        "methods": matched_methods,
        "files": matched_files,
    }
    return jsonify(result)


def ai_query_with_retry(question, api_key, max_retries=3, delay=1):
    """AI 查询带重试机制，支持 SQL 验证和自动修正"""
    last_error = None

    for attempt in range(max_retries):
        try:
            # 构建 AI prompt
            prompt = f"""你是一个SQL专家。根据以下数据库表结构，将用户的问题转换为准确的SQL查询语句。

数据库表结构：
1. files - 文件表 (path 主键, line_count)
2. classes - 类/组件表 (name, file, is_component 0/1, is_entry 0/1, line_number)
3. methods - 方法表 (name, class_name, file, line_number, is_static 0/1, is_private 0/1)
4. calls - 调用关系表 (caller, caller_class, callee, callee_class, file, line_number)
5. components - 组件嵌套关系表 (parent, child, file, line_number)
6. inherits - 继承关系表 (child_class, parent_class, file, line_number)

重要规则：
1. 只返回SQL语句，不要有任何解释
2. SQL语句必须以分号结尾
3. 使用正确的表名和字段名
4. 对于模糊查询使用LIKE和通配符%
5. 对于统计查询使用COUNT、GROUP BY等

用户问题：{question}

SQL语句："""

            # 调用硅基流动 API
            response = requests.post(
                url="https://api.siliconflow.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            response.raise_for_status()
            ai_result = response.json()
            sql = ai_result["choices"][0]["message"]["content"].strip()

            # 清理 SQL：去除 markdown 代码块标记
            sql = sql.strip()
            if sql.startswith("```"):
                lines = sql.split("\n")
                cleaned_lines = []
                for line in lines:
                    if line.strip().startswith("```"):
                        continue
                    cleaned_lines.append(line)
                sql = "\n".join(cleaned_lines).strip()

            # 去除末尾多余的分号
            sql = sql.rstrip(";").strip()

            # SQL 安全检查
            is_safe, error_msg = validate_sql(sql)
            if not is_safe:
                # SQL 安全检查失败，尝试重试
                last_error = f"SQL安全检查失败: {error_msg}"
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                continue

            # 尝试执行 SQL 验证
            try:
                conn = get_db()
                try:
                    cursor = conn.execute(sql)
                    columns = [description[0] for description in cursor.description]
                    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    return {
                        'success': True,
                        'sql': sql,
                        'columns': columns,
                        'data': rows,
                        'row_count': len(rows),
                        'attempt': attempt + 1
                    }
                finally:
                    conn.close()
            except sqlite3.Error as e:
                # SQL 执行失败，尝试重试
                last_error = f"SQL 执行失败: {str(e)}"
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                continue

        except requests.exceptions.Timeout:
            last_error = "AI API 请求超时"
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
        except requests.exceptions.RequestException as e:
            last_error = f"AI API 请求失败: {str(e)}"
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
        except (KeyError, IndexError):
            last_error = "AI API 返回格式异常"
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))

    return {'success': False, 'error': last_error, 'attempts': max_retries}


@app.route("/api/ai/query", methods=["POST"])
def ai_query():
    """
    AI 自然语言查询（带缓存和重试机制）
    请求体：{ "question": "...", "api_key": "...", "use_cache": true }
    使用硅基流动 API 将自然语言转 SQL，执行后返回结果
    支持缓存（默认启用）、最多 3 次重试、SQL 验证和自动修正
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    question = data.get("question", "").strip()
    api_key = data.get("api_key", "").strip()
    use_cache = data.get("use_cache", True)  # 默认启用缓存

    if not question:
        return jsonify({"error": "请提供 question 参数"}), 400
    if not api_key:
        return jsonify({"error": "请提供 api_key 参数"}), 400

    # 检查缓存
    if use_cache:
        cached = query_cache.get(question, DB_PATH)
        if cached:
            cached['from_cache'] = True
            return jsonify(cached)

    # 使用带重试机制的查询
    result = ai_query_with_retry(question, api_key)

    if result.get('success'):
        # 存入缓存
        if use_cache:
            query_cache.set(question, DB_PATH, result)
        result['from_cache'] = False
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route("/api/ai/cache/stats", methods=["GET"])
def ai_cache_stats():
    """获取AI查询缓存统计"""
    return jsonify(query_cache.stats())


@app.route("/api/ai/cache/clear", methods=["POST"])
def ai_cache_clear():
    """清空AI查询缓存"""
    query_cache.clear()
    return jsonify({"success": True, "message": "缓存已清空"})


@app.route("/api/export/json", methods=["GET"])
def export_json():
    """导出全部数据为 JSON"""
    tables = ["files", "classes", "methods", "calls", "components", "inherits"]
    data = {}
    for table in tables:
        data[table] = query_db(f"SELECT * FROM {table}")
    return jsonify(data)


@app.route("/api/export/csv/<table_name>", methods=["GET"])
def export_csv(table_name):
    """导出指定表为 CSV"""
    # 允许导出的表名白名单，防止 SQL 注入
    allowed_tables = {"files", "classes", "methods", "calls", "components", "inherits"}
    if table_name not in allowed_tables:
        return jsonify({"error": f"不支持的表名: {table_name}，允许的表: {', '.join(sorted(allowed_tables))}"}), 400

    rows = query_db(f"SELECT * FROM {table_name}")
    if not rows:
        return jsonify({"error": f"表 {table_name} 中没有数据"}), 404

    # 使用 csv 模块生成 CSV 内容
    output = io.StringIO()
    columns = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

    # 返回 CSV 文件响应
    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
    )


# ============================================================
# 第四十三阶段：数据可视化仪表板 API
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard_data():
    """仪表板数据：类分布、Top 10 类、调用关系统计、继承关系统计"""
    conn = get_db()

    try:
        # 类分布
        class_distribution = conn.execute("""
            SELECT
                CASE WHEN is_component = 1 THEN '组件' ELSE '普通类' END as type,
                COUNT(*) as count
            FROM classes GROUP BY type
        """).fetchall()

        # 方法数量分布（Top 10 类）
        top_classes = conn.execute("""
            SELECT class_name, COUNT(*) as method_count
            FROM methods
            GROUP BY class_name
            ORDER BY method_count DESC
            LIMIT 10
        """).fetchall()

        # 调用关系统计
        call_stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT caller_class) as callers,
                COUNT(DISTINCT callee_class) as callees
            FROM calls
            WHERE caller_class != '' AND callee_class != ''
        """).fetchone()

        # 继承关系统计
        inherit_stats = conn.execute("""
            SELECT COUNT(*) FROM inherits
        """).fetchone()

        return jsonify({
            'class_distribution': [{'type': r[0], 'count': r[1]} for r in class_distribution],
            'top_classes': [{'name': r[0], 'methods': r[1]} for r in top_classes],
            'call_stats': {
                'total': call_stats[0] if call_stats else 0,
                'callers': call_stats[1] if call_stats else 0,
                'callees': call_stats[2] if call_stats else 0
            },
            'inherit_count': inherit_stats[0] if inherit_stats else 0
        })
    finally:
        conn.close()


# ============================================================
# 第四十四阶段：API 文档（OpenAPI/Swagger）
# ============================================================

@app.route("/api/docs", methods=["GET"])
def api_docs():
    """API 文档（OpenAPI 3.0 格式）"""
    docs = {
        "openapi": "3.0.0",
        "info": {
            "title": "ArkTS Knowledge Graph API",
            "version": "4.14.0",
            "description": "ArkTS 代码知识图谱可视化系统 API"
        },
        "paths": {
            "/api/stats": {
                "get": {
                    "summary": "获取统计信息",
                    "description": "返回知识图谱的统计信息，包括文件数、类数、组件数、方法数、调用关系数等",
                    "responses": {"200": {"description": "统计信息对象"}}
                }
            },
            "/api/files": {
                "get": {
                    "summary": "获取文件列表",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "文件列表"}}
                }
            },
            "/api/classes": {
                "get": {
                    "summary": "获取类列表",
                    "parameters": [
                        {"name": "component_only", "in": "query", "schema": {"type": "boolean"}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "类列表"}}
                }
            },
            "/api/methods": {
                "get": {
                    "summary": "获取方法列表",
                    "parameters": [
                        {"name": "class_name", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "方法列表"}}
                }
            },
            "/api/calls": {
                "get": {
                    "summary": "获取调用关系",
                    "responses": {"200": {"description": "调用关系列表"}}
                }
            },
            "/api/components": {
                "get": {
                    "summary": "获取组件关系",
                    "responses": {"200": {"description": "组件关系列表"}}
                }
            },
            "/api/inherits": {
                "get": {
                    "summary": "获取继承关系",
                    "responses": {"200": {"description": "继承关系列表"}}
                }
            },
            "/api/search": {
                "get": {
                    "summary": "搜索",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "搜索结果"}}
                }
            },
            "/api/ai/query": {
                "post": {
                    "summary": "AI 自然语言查询（带重试机制）",
                    "description": "使用 AI 将自然语言转换为 SQL 查询，支持最多 3 次重试",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string", "description": "自然语言问题"},
                                    "api_key": {"type": "string", "description": "AI API 密钥"}
                                },
                                "required": ["question"]
                            }
                        }}
                    },
                    "responses": {"200": {"description": "查询结果"}}
                }
            },
            "/api/dashboard": {
                "get": {
                    "summary": "仪表板数据",
                    "description": "返回仪表板统计数据，包括类分布、Top 10 类、调用关系统计等",
                    "responses": {"200": {"description": "仪表板统计数据"}}
                }
            },
            "/api/projects": {
                "get": {
                    "summary": "列出所有已解析的项目",
                    "description": "扫描当前目录下的 .db 文件，列出所有已解析的项目",
                    "responses": {"200": {"description": "项目列表"}}
                }
            },
            "/api/export/json": {
                "get": {"summary": "导出 JSON", "responses": {"200": {"description": "JSON 文件"}}}
            },
            "/api/export/csv/<table_name>": {
                "get": {
                    "summary": "导出 CSV",
                    "parameters": [
                        {"name": "table_name", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "CSV 文件"}}
                }
            },
            "/api/docs": {
                "get": {"summary": "API 文档", "responses": {"200": {"description": "OpenAPI 文档"}}}
            }
        }
    }
    return jsonify(docs)


# ============================================================
# 第四十五阶段：多项目仪表板 API
# ============================================================

@app.route("/api/projects", methods=["GET"])
def list_projects():
    """列出所有已解析的项目（扫描当前目录下的 .db 文件）"""
    db_files = glob.glob("*.db")
    projects = []
    for db_file in db_files:
        try:
            conn = sqlite3.connect(db_file)
            stats = conn.execute("SELECT COUNT(*) FROM classes").fetchone()
            conn.close()
            projects.append({
                'name': db_file.replace('.db', ''),
                'db_path': db_file,
                'class_count': stats[0] if stats else 0
            })
        except Exception:
            pass
    return jsonify({'projects': projects})


# ============================================================
# 代码质量分析 API
# ============================================================

@app.route("/api/quality/report", methods=["GET"])
def quality_report():
    """获取代码质量报告"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from quality_analyzer import analyze_quality

        report = analyze_quality(DB_PATH)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/quality/file", methods=["GET"])
def quality_file():
    """获取单个文件的质量分析"""
    file_path = request.args.get('path', '')
    if not file_path:
        return jsonify({"error": "请提供文件路径"}), 400

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from quality_analyzer import CodeQualityAnalyzer

        analyzer = CodeQualityAnalyzer(DB_PATH)
        try:
            metrics = analyzer.analyze_file(file_path)
            if metrics:
                return jsonify({
                    'file_path': metrics.file_path,
                    'total_lines': metrics.total_lines,
                    'code_lines': metrics.code_lines,
                    'comment_lines': metrics.comment_lines,
                    'blank_lines': metrics.blank_lines,
                    'class_count': metrics.class_count,
                    'method_count': metrics.method_count,
                    'avg_method_length': metrics.avg_method_length,
                    'max_method_length': metrics.max_method_length,
                    'complexity_score': metrics.complexity_score,
                    'maintainability_index': metrics.maintainability_index,
                    'duplicate_score': metrics.duplicate_score,
                    'naming_score': metrics.naming_score,
                    'overall_score': metrics.overall_score,
                    'grade': analyzer._score_to_grade(metrics.overall_score),
                    'issues': metrics.issues
                })
            else:
                return jsonify({"error": "无法分析文件"}), 404
        finally:
            analyzer.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# 图谱对比与差异分析 API
# ============================================================

@app.route("/api/diff/compare", methods=["POST"])
def diff_compare():
    """
    对比两个数据库的图谱差异
    请求体: { "old_db": "path/to/old.db", "new_db": "path/to/new.db" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    old_db = data.get("old_db", "").strip()
    new_db = data.get("new_db", "").strip()

    if not old_db or not new_db:
        return jsonify({"error": "请提供 old_db 和 new_db 参数"}), 400

    # 安全检查：确保路径在允许范围内
    base_dir = os.path.dirname(DB_PATH) or "."
    old_db_path = os.path.abspath(os.path.join(base_dir, old_db))
    new_db_path = os.path.abspath(os.path.join(base_dir, new_db))

    if not old_db_path.endswith('.db') or not new_db_path.endswith('.db'):
        return jsonify({"error": "只允许对比 .db 文件"}), 400

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from graph_diff import compare_graphs

        result = compare_graphs(old_db_path, new_db_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/diff/snapshots", methods=["GET"])
def diff_snapshots():
    """获取可用的数据库快照列表（用于对比选择）"""
    base_dir = os.path.dirname(DB_PATH) or "."

    snapshots = []
    for db_file in sorted(glob.glob(os.path.join(base_dir, "*.db"))):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.execute("SELECT COUNT(*) FROM classes")
            class_count = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM methods")
            method_count = cursor.fetchone()[0]
            conn.close()

            stat = os.stat(db_file)
            snapshots.append({
                "name": os.path.basename(db_file),
                "path": db_file,
                "class_count": class_count,
                "method_count": method_count,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            })
        except Exception:
            pass

    return jsonify({"snapshots": snapshots})


# ============================================================
# 智能代码搜索 API
# ============================================================

@app.route("/api/search/smart", methods=["GET"])
def search_smart():
    """
    智能代码搜索（基于语义）
    查询参数: ?q=关键词&limit=20
    """
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)

    if not query or len(query) < 2:
        return jsonify({"error": "查询词至少需要2个字符"}), 400

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from smart_search import smart_search

        results = smart_search(DB_PATH, query, limit)
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search/similar", methods=["GET"])
def search_similar():
    """
    查找相似代码
    查询参数: ?entity=类名或方法名&limit=10
    """
    entity = request.args.get('entity', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if not entity:
        return jsonify({"error": "请提供 entity 参数"}), 400

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from smart_search import find_similar_code

        results = find_similar_code(DB_PATH, entity, limit)
        return jsonify({
            "entity": entity,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search/patterns", methods=["GET"])
def search_patterns():
    """
    获取支持的搜索模式列表
    """
    patterns = [
        {"id": "event_handler", "name": "事件处理器", "pattern": "^on[A-Z]", "example": "onClick, onChange"},
        {"id": "getter", "name": "Getter方法", "pattern": "^get[A-Z]", "example": "getName, getValue"},
        {"id": "setter", "name": "Setter方法", "pattern": "^set[A-Z]", "example": "setName, setValue"},
        {"id": "boolean", "name": "布尔判断", "pattern": "^is[A-Z]|^has[A-Z]", "example": "isValid, hasChildren"},
        {"id": "factory", "name": "工厂方法", "pattern": "^create[A-Z]|^build[A-Z]", "example": "createInstance, buildView"},
        {"id": "lifecycle", "name": "生命周期", "pattern": "^aboutTo|^(on|did)[A-Z]", "example": "aboutToAppear, onInit"},
    ]
    return jsonify({"patterns": patterns})


@app.route("/api/search/pattern/<pattern_type>", methods=["GET"])
def search_by_pattern(pattern_type):
    """
    按模式搜索
    """
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from smart_search import SmartSearcher

        searcher = SmartSearcher(DB_PATH)
        try:
            results = searcher.search_by_pattern(pattern_type)
            return jsonify({
                "pattern": pattern_type,
                "count": len(results),
                "results": [
                    {
                        "name": r.name,
                        "type": r.entity_type,
                        "file": r.file_path,
                        "line": r.line_number,
                        "content": r.content[:100] if r.content else ""
                    }
                    for r in results
                ]
            })
        finally:
            searcher.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# 性能剖析 API
# ============================================================

@app.route("/api/profile/summary", methods=["GET"])
def profile_summary():
    """获取性能概要"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(DB_PATH)
        try:
            summary = profiler.get_performance_summary()
            return jsonify(summary)
        finally:
            profiler.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/hotspots", methods=["GET"])
def profile_hotspots():
    """获取热点方法"""
    limit = request.args.get('limit', 20, type=int)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(DB_PATH)
        try:
            hotspots = profiler.analyze_hotspots(limit)
            return jsonify({"hotspots": hotspots, "count": len(hotspots)})
        finally:
            profiler.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/method/<method_name>", methods=["GET"])
def profile_method(method_name):
    """获取方法详细性能画像"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(DB_PATH)
        try:
            profile = profiler.get_method_profile(method_name)
            if profile:
                return jsonify(profile)
            else:
                return jsonify({"error": "方法未找到"}), 404
        finally:
            profiler.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/flame", methods=["GET"])
def profile_flame():
    """获取火焰图数据"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(DB_PATH)
        try:
            data = profiler.generate_flame_graph_data()
            return jsonify(data)
        finally:
            profiler.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/trace/<method_name>", methods=["GET"])
def profile_trace(method_name):
    """追踪方法调用链"""
    max_depth = request.args.get('max_depth', 5, type=int)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(DB_PATH)
        try:
            chains = profiler.trace_call_chain(method_name, max_depth)
            return jsonify({
                "method": method_name,
                "chains": [
                    {
                        "root": c.root_method,
                        "path": c.path,
                        "estimated_time_ms": c.total_time_ms
                    }
                    for c in chains
                ]
            })
        finally:
            profiler.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# 3D可视化 API
# ============================================================

@app.route("/api/3d/graph", methods=["GET"])
def api_3d_graph():
    """获取3D力导向图谱数据"""
    max_nodes = request.args.get("max_nodes", 500, type=int)
    include_methods = request.args.get("methods", "false").lower() == "true"

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from visualization_3d import Visualization3D

        viz = Visualization3D(DB_PATH)
        try:
            data = viz.get_graph_data(max_nodes, include_methods)
            return jsonify(data)
        finally:
            viz.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/3d/hierarchical", methods=["GET"])
def api_3d_hierarchical():
    """获取层级布局数据（按继承层次）"""
    max_nodes = request.args.get("max_nodes", 300, type=int)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from visualization_3d import Visualization3D

        viz = Visualization3D(DB_PATH)
        try:
            data = viz.get_hierarchical_layout(max_nodes)
            return jsonify(data)
        finally:
            viz.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/3d/cluster", methods=["GET"])
def api_3d_cluster():
    """获取聚类视图数据（按包/命名空间分组）"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from visualization_3d import Visualization3D

        viz = Visualization3D(DB_PATH)
        try:
            data = viz.get_cluster_view()
            return jsonify(data)
        finally:
            viz.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/3d/timeline", methods=["GET"])
def api_3d_timeline():
    """获取时序演化数据（按文件修改时间）"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from visualization_3d import Visualization3D

        viz = Visualization3D(DB_PATH)
        try:
            data = viz.get_timeline_data()
            return jsonify(data)
        finally:
            viz.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/3d/export", methods=["GET"])
def api_3d_export():
    """导出Three.js兼容格式"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from visualization_3d import Visualization3D

        viz = Visualization3D(DB_PATH)
        try:
            result = viz.export_to_threejs()
            return Response(result, mimetype='application/json')
        finally:
            viz.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# AI辅助重构建议 API
# ============================================================

@app.route("/api/refactor/suggestions", methods=["GET"])
def refactor_suggestions():
    """获取所有重构建议"""
    priority = request.args.get("priority")  # 过滤优先级
    category = request.args.get("category")  # 过滤类别
    limit = request.args.get("limit", 50, type=int)

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from refactoring_advisor import RefactoringAdvisor

        advisor = RefactoringAdvisor(DB_PATH)
        try:
            suggestions = advisor.analyze_all()

            # 过滤
            if priority:
                suggestions = [s for s in suggestions if s.priority == priority]
            if category:
                suggestions = [s for s in suggestions if s.category == category]

            suggestions = suggestions[:limit]

            return jsonify({
                "count": len(suggestions),
                "suggestions": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "category": s.category,
                        "priority": s.priority,
                        "file": s.file_path,
                        "line": s.line_number,
                        "entity": s.entity_name,
                        "description": s.description,
                        "current_code": s.current_code,
                        "suggested_code": s.suggested_code,
                        "steps": s.steps,
                        "impact": s.impact,
                        "effort": s.estimated_effort,
                        "references": s.references
                    }
                    for s in suggestions
                ]
            })
        finally:
            advisor.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refactor/entity/<entity_name>", methods=["GET"])
def refactor_entity(entity_name):
    """获取特定实体的重构建议"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from refactoring_advisor import RefactoringAdvisor

        advisor = RefactoringAdvisor(DB_PATH)
        try:
            suggestions = advisor.analyze_entity(entity_name)
            return jsonify({
                "entity": entity_name,
                "count": len(suggestions),
                "suggestions": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "category": s.category,
                        "priority": s.priority,
                        "description": s.description,
                        "steps": s.steps,
                        "impact": s.impact,
                        "effort": s.estimated_effort
                    }
                    for s in suggestions
                ]
            })
        finally:
            advisor.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refactor/summary", methods=["GET"])
def refactor_summary():
    """获取重构建议摘要"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from refactoring_advisor import RefactoringAdvisor

        advisor = RefactoringAdvisor(DB_PATH)
        try:
            summary = advisor.get_summary()
            return jsonify(summary)
        finally:
            advisor.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refactor/categories", methods=["GET"])
def refactor_categories():
    """获取支持的重构类别"""
    categories = [
        {"id": "extract_method", "name": "提取方法", "description": "将过长方法中的逻辑块提取为独立方法"},
        {"id": "extract_class", "name": "提取类", "description": "将大类拆分为多个职责单一的小类"},
        {"id": "rename", "name": "重命名", "description": "修正不符合命名规范的标识符"},
        {"id": "simplify_cond", "name": "简化条件", "description": "简化复杂的条件表达式"},
        {"id": "remove_dup", "name": "消除重复", "description": "识别并消除重复代码"},
        {"id": "reduce_params", "name": "减少参数", "description": "通过参数对象减少方法参数数量"},
        {"id": "introduce_const", "name": "引入常量", "description": "将魔法数字替换为有意义的常量"},
        {"id": "fix_naming", "name": "修正命名", "description": "修正不符合命名规范的类名和方法名"},
        {"id": "add_comments", "name": "添加注释", "description": "为缺少文档的公共API添加注释"},
        {"id": "handle_exception", "name": "改善异常处理", "description": "修复空catch块和过宽的异常捕获"},
        {"id": "decouple", "name": "解耦", "description": "降低类之间的耦合度"},
        {"id": "consolidate", "name": "合并", "description": "合并功能相似的方法或类"},
    ]
    return jsonify({"categories": categories})


# ============================================================
# 团队协作 API
# ============================================================

# 全局协作管理器实例
collab_manager = None

def get_collab_manager():
    """获取协作管理器"""
    global collab_manager
    if collab_manager is None:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from collaboration import CollaborationManager
        collab_manager = CollaborationManager(DB_PATH)
    return collab_manager


@app.route("/api/collab/users", methods=["POST"])
def collab_create_user():
    """创建用户"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()

    if not username or not email:
        return jsonify({"error": "请提供用户名和邮箱"}), 400

    try:
        user = get_collab_manager().create_user(username, email, data.get("avatar", ""))
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at
        })
    except sqlite3.IntegrityError:
        return jsonify({"error": "用户名或邮箱已存在"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collab/annotations", methods=["GET", "POST"])
def collab_annotations():
    """获取或创建标注"""
    if request.method == "GET":
        entity_type = request.args.get("entity_type")
        entity_name = request.args.get("entity_name")
        resolved = request.args.get("resolved", type=lambda x: x.lower() == "true")

        try:
            annotations = get_collab_manager().get_annotations(
                entity_type=entity_type,
                entity_name=entity_name,
                resolved=resolved
            )
            return jsonify({
                "annotations": [
                    {
                        "id": a.id,
                        "entity_type": a.entity_type,
                        "entity_name": a.entity_name,
                        "user_id": a.user_id,
                        "annotation_type": a.annotation_type,
                        "content": a.content,
                        "file_path": a.file_path,
                        "line_number": a.line_number,
                        "created_at": a.created_at,
                        "resolved": a.resolved,
                        "replies": a.replies
                    }
                    for a in annotations
                ]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:  # POST
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        required = ["entity_type", "entity_name", "user_id", "annotation_type", "content"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"缺少必需字段: {field}"}), 400

        try:
            ann = get_collab_manager().add_annotation(
                entity_type=data["entity_type"],
                entity_name=data["entity_name"],
                user_id=data["user_id"],
                annotation_type=data["annotation_type"],
                content=data["content"],
                file_path=data.get("file_path", ""),
                line_number=data.get("line_number", 0)
            )
            return jsonify({
                "id": ann.id,
                "entity_type": ann.entity_type,
                "entity_name": ann.entity_name,
                "created_at": ann.created_at
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/collab/annotations/<annotation_id>", methods=["PUT", "DELETE"])
def collab_annotation_detail(annotation_id):
    """更新或删除标注"""
    if request.method == "PUT":
        data = request.get_json() or {}
        try:
            get_collab_manager().update_annotation(
                annotation_id,
                content=data.get("content"),
                resolved=data.get("resolved")
            )
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:  # DELETE
        try:
            get_collab_manager().delete_annotation(annotation_id)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/collab/annotations/<annotation_id>/replies", methods=["POST"])
def collab_add_reply(annotation_id):
    """添加回复"""
    data = request.get_json()
    if not data or not data.get("user_id") or not data.get("content"):
        return jsonify({"error": "请提供 user_id 和 content"}), 400

    try:
        reply = get_collab_manager().add_reply(
            annotation_id,
            data["user_id"],
            data["content"]
        )
        return jsonify(reply)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collab/snapshots", methods=["GET", "POST"])
def collab_snapshots():
    """获取或创建快照"""
    if request.method == "GET":
        user_id = request.args.get("user_id")
        try:
            snapshots = get_collab_manager().list_snapshots(user_id)
            return jsonify({
                "snapshots": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "created_by": s.created_by,
                        "created_at": s.created_at,
                        "permission": s.permission,
                        "view_count": s.view_count
                    }
                    for s in snapshots
                ]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:  # POST
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        required = ["name", "description", "created_by"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"缺少必需字段: {field}"}), 400

        try:
            snapshot = get_collab_manager().create_snapshot(
                name=data["name"],
                description=data["description"],
                db_path=DB_PATH,
                created_by=data["created_by"],
                permission=data.get("permission", "private")
            )
            return jsonify({
                "id": snapshot.id,
                "name": snapshot.name,
                "share_token": snapshot.share_token,
                "created_at": snapshot.created_at
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/collab/snapshots/<snapshot_id>", methods=["GET", "DELETE"])
def collab_snapshot_detail(snapshot_id):
    """获取或删除快照"""
    if request.method == "GET":
        try:
            snapshot = get_collab_manager().get_snapshot(snapshot_id)
            if snapshot:
                get_collab_manager().increment_view_count(snapshot_id)
                return jsonify({
                    "id": snapshot.id,
                    "name": snapshot.name,
                    "description": snapshot.description,
                    "created_by": snapshot.created_by,
                    "created_at": snapshot.created_at,
                    "permission": snapshot.permission,
                    "view_count": snapshot.view_count
                })
            return jsonify({"error": "快照不存在"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:  # DELETE
        try:
            get_collab_manager().delete_snapshot(snapshot_id)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/collab/share/<token>", methods=["GET"])
def collab_share(token):
    """通过分享令牌访问快照"""
    try:
        snapshot = get_collab_manager().get_snapshot_by_token(token)
        if snapshot:
            get_collab_manager().increment_view_count(snapshot.id)
            return jsonify({
                "id": snapshot.id,
                "name": snapshot.name,
                "description": snapshot.description,
                "created_by": snapshot.created_by,
                "created_at": snapshot.created_at
            })
        return jsonify({"error": "无效的分享链接"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/collab/stats", methods=["GET"])
def collab_stats():
    """获取协作统计"""
    try:
        stats = get_collab_manager().get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# WebSocket 实时更新支持 (Server-Sent Events)
# ============================================================

class DataChangeMonitor:
    """数据库变更监控器"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.last_mtime = 0
        self.clients = []
        self.running = False
        self.lock = Lock()

    def add_client(self, client):
        with self.lock:
            self.clients.append(client)

    def remove_client(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)

    def notify_clients(self, message):
        with self.lock:
            dead_clients = []
            for client in self.clients:
                try:
                    client.put(message)
                except Exception:
                    dead_clients.append(client)
            for dead in dead_clients:
                self.clients.remove(dead)

    def check_changes(self):
        """检查数据库文件变更"""
        try:
            current_mtime = os.path.getmtime(self.db_path)
            if current_mtime > self.last_mtime:
                self.last_mtime = current_mtime
                return True
        except Exception:
            pass
        return False

    def start_monitoring(self):
        """启动监控线程"""
        if self.running:
            return
        self.running = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            if self.check_changes():
                self.notify_clients({
                    'type': 'db_changed',
                    'timestamp': time.time(),
                    'message': '数据库已更新'
                })
            time.sleep(2)  # 每2秒检查一次

    def stop(self):
        self.running = False

# 全局监控器实例
monitor = None


def get_monitor():
    """获取或创建监控器"""
    global monitor
    if monitor is None:
        monitor = DataChangeMonitor(DB_PATH)
        monitor.start_monitoring()
    return monitor


class MessageQueue:
    """简单的消息队列用于SSE"""

    def __init__(self):
        self.messages = []
        self.event = None

    def put(self, message):
        self.messages.append(json.dumps(message))

    def get(self):
        if self.messages:
            return self.messages.pop(0)
        return None


@app.route('/api/events')
def sse_events():
    """Server-Sent Events 端点"""
    def event_stream():
        client = MessageQueue()
        get_monitor().add_client(client)
        try:
            # 发送初始连接消息
            yield f"data: {json.dumps({'type': 'connected', 'message': '已连接到实时更新服务'})}\n\n"

            while True:
                msg = client.get()
                if msg:
                    yield f"data: {msg}\n\n"
                time.sleep(0.5)
        finally:
            get_monitor().remove_client(client)

    return Response(event_stream(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/notify/refresh', methods=['POST'])
def notify_refresh():
    """手动触发数据刷新通知"""
    get_monitor().notify_clients({
        'type': 'manual_refresh',
        'timestamp': time.time(),
        'message': '手动刷新通知'
    })
    return jsonify({'success': True, 'message': '刷新通知已发送'})


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="ArkTS 知识图谱可视化后端服务")
    parser.add_argument(
        "--db",
        default="../test_code.db",
        help="SQLite 数据库文件路径（默认: ../test_code.db）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="服务端口号（默认: 5000）",
    )
    parser.add_argument('--debug', action='store_true', default=False, help='启用调试模式')
    args = parser.parse_args()

    # 设置全局数据库路径
    DB_PATH = args.db

    # 启动监控器
    get_monitor()

    # 启动服务
    print(f"知识图谱可视化服务已启动: http://localhost:{args.port}")
    print(f"WebSocket (SSE) 端点: http://localhost:{args.port}/api/events")
    app.run(host="0.0.0.0", port=args.port, debug=args.debug, threaded=True)
