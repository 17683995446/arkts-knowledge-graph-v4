# -*- coding: utf-8 -*-
"""
ArkTS 知识图谱可视化 - Flask 后端服务
提供 REST API 接口，用于查询和展示知识图谱数据
"""

import argparse
import csv
import io
import os
import re
import sqlite3
import sys

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


@app.route("/api/ai/query", methods=["POST"])
def ai_query():
    """
    AI 自然语言查询
    请求体：{ "question": "...", "api_key": "..." }
    使用硅基流动 API 将自然语言转 SQL，执行后返回结果
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    question = data.get("question", "").strip()
    api_key = data.get("api_key", "").strip()

    if not question:
        return jsonify({"error": "请提供 question 参数"}), 400
    if not api_key:
        return jsonify({"error": "请提供 api_key 参数"}), 400

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
    try:
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
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI API 请求超时，请稍后重试"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"AI API 请求失败: {str(e)}"}), 502
    except (KeyError, IndexError):
        return jsonify({"error": "AI API 返回格式异常"}), 502

    # 清理 SQL：去除 markdown 代码块标记，只保留纯 SQL
    sql = sql.strip()
    if sql.startswith("```"):
        # 去除首尾的 ``` 标记
        lines = sql.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                continue
            cleaned_lines.append(line)
        sql = "\n".join(cleaned_lines).strip()

    # 去除末尾多余的分号（sqlite3 不需要）
    sql = sql.rstrip(";").strip()

    # SQL 安全检查
    is_safe, error_msg = validate_sql(sql)
    if not is_safe:
        return jsonify({'success': False, 'error': f'SQL安全检查失败: {error_msg}', 'sql': sql})

    # 执行生成的 SQL
    try:
        conn = get_db()
        try:
            cursor = conn.execute(sql)
            columns = [description[0] for description in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify({"sql": sql, "columns": columns, "data": rows, "row_count": len(rows)})
        finally:
            conn.close()
    except sqlite3.Error as e:
        return jsonify({"error": f"SQL 执行失败: {str(e)}", "sql": sql}), 500


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

    # 启动服务
    print(f"知识图谱可视化服务已启动: http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=args.debug)
