#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS知识图谱可视化Web服务
提供REST API和Web界面
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from arkts_knowledge_graph import KnowledgeGraphBuilder, DatabaseManager, ArkTSParser

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 全局配置
CONFIG = {
    'db_path': None,
    'project_path': None,
    'builder': None
}


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """获取统计信息"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化，请先解析项目'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        stats = db.get_statistics()
        ext_stats = db.get_extended_statistics()
        if ext_stats:
            stats.update(ext_stats)
        db.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/classes')
def get_classes():
    """获取所有类/组件"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT name, file, is_component, is_entry, line_number FROM classes ORDER BY name")
        db.close()
        
        classes = []
        for row in rows:
            classes.append({
                'name': row[0],
                'file': row[1],
                'is_component': bool(row[2]),
                'is_entry': bool(row[3]),
                'line_number': row[4]
            })
        return jsonify(classes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/methods')
def get_methods():
    """获取所有方法"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT name, class_name, file, line_number, is_static, is_private FROM methods ORDER BY class_name, name")
        db.close()
        
        methods = []
        for row in rows:
            methods.append({
                'name': row[0],
                'class_name': row[1],
                'file': row[2],
                'line_number': row[3],
                'is_static': bool(row[4]),
                'is_private': bool(row[5])
            })
        return jsonify(methods)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calls')
def get_calls():
    """获取调用关系"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT caller, caller_class, callee, callee_class, file, line_number FROM calls")
        db.close()
        
        calls = []
        for row in rows:
            calls.append({
                'caller': row[0],
                'caller_class': row[1],
                'callee': row[2],
                'callee_class': row[3],
                'file': row[4],
                'line_number': row[5]
            })
        return jsonify(calls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/components')
def get_components():
    """获取组件嵌套关系"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT parent, child, file, line_number FROM components")
        db.close()
        
        comps = []
        for row in rows:
            comps.append({
                'parent': row[0],
                'child': row[1],
                'file': row[2],
                'line_number': row[3]
            })
        return jsonify(comps)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inherits')
def get_inherits():
    """获取继承关系"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT child_class, parent_class, file, line_number FROM inherits")
        db.close()
        
        inherits = []
        for row in rows:
            inherits.append({
                'child_class': row[0],
                'parent_class': row[1],
                'file': row[2],
                'line_number': row[3]
            })
        return jsonify(inherits)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/files')
def get_files():
    """获取所有文件"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT path, line_count, md5_hash FROM files ORDER BY path")
        db.close()
        
        files = []
        for row in rows:
            files.append({
                'path': row[0],
                'line_count': row[1] or 0,
                'md5_hash': row[2] or ''
            })
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/decorators')
def get_decorators():
    """获取装饰器"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query("SELECT name, dec_type, target_type, target_name, target_class, argument, file, line_number FROM decorators")
        db.close()
        
        decs = []
        for row in rows:
            decs.append({
                'name': row[0],
                'dec_type': row[1],
                'target_type': row[2],
                'target_name': row[3],
                'target_class': row[4],
                'argument': row[5],
                'file': row[6],
                'line_number': row[7]
            })
        return jsonify(decs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph')
def get_graph():
    """获取完整图谱数据（用于可视化）"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        
        # 获取所有类
        class_rows = db.execute_query("SELECT name, file, is_component, is_entry FROM classes")
        
        # 获取组件关系
        comp_rows = db.execute_query("SELECT parent, child FROM components")
        
        # 获取继承关系
        inherit_rows = db.execute_query("SELECT child_class, parent_class FROM inherits")
        
        # 获取调用关系（聚合）
        call_rows = db.execute_query("""
            SELECT caller_class, callee_class, COUNT(*) as cnt 
            FROM calls 
            WHERE caller_class != '' AND callee_class != ''
            GROUP BY caller_class, callee_class
        """)
        
        db.close()
        
        # 构建节点
        nodes = []
        node_set = set()
        
        for row in class_rows:
            name = row[0]
            if name not in node_set:
                node_set.add(name)
                nodes.append({
                    'id': name,
                    'name': name,
                    'category': 'component' if row[2] else 'class',
                    'is_entry': bool(row[3]),
                    'symbolSize': 50 if row[3] else (40 if row[2] else 30)
                })
        
        # 构建边
        links = []
        
        # 组件嵌套关系
        for row in comp_rows:
            links.append({
                'source': row[0],
                'target': row[1],
                'type': 'component',
                'value': '包含'
            })
        
        # 继承关系
        for row in inherit_rows:
            links.append({
                'source': row[0],
                'target': row[1],
                'type': 'inherit',
                'value': '继承'
            })
        
        # 调用关系
        for row in call_rows:
            links.append({
                'source': row[0],
                'target': row[1],
                'type': 'call',
                'value': f'调用x{row[2]}'
            })
        
        return jsonify({
            'nodes': nodes,
            'links': links
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/build', methods=['POST'])
def build_project():
    """解析项目构建知识图谱"""
    data = request.get_json()
    project_path = data.get('project_path')
    use_filter = data.get('filter', False)
    incremental = data.get('incremental', False)
    
    if not project_path or not os.path.exists(project_path):
        return jsonify({'error': f'项目路径不存在: {project_path}'}), 400
    
    try:
        # 设置数据库路径
        CONFIG['db_path'] = os.path.join(project_path, '.arkts_kg.db')
        CONFIG['project_path'] = project_path
        
        # 构建知识图谱
        builder = KnowledgeGraphBuilder(CONFIG['db_path'])
        stats = builder.build(project_path, 
                             exclude_third_party=use_filter,
                             incremental=incremental)
        builder.close()
        
        CONFIG['builder'] = builder
        
        return jsonify({
            'success': True,
            'message': '知识图谱构建完成',
            'stats': stats,
            'db_path': CONFIG['db_path']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query', methods=['POST'])
def execute_query():
    """执行自定义SQL查询"""
    data = request.get_json()
    sql = data.get('sql')
    
    if not sql:
        return jsonify({'error': 'SQL语句不能为空'}), 400
    
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        rows = db.execute_query(sql)
        
        # 获取列名
        cursor = db.conn.cursor()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        db.close()
        
        return jsonify({
            'columns': columns,
            'rows': rows,
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/class/<class_name>')
def get_class_detail(class_name):
    """获取类的详细信息"""
    if not CONFIG['db_path'] or not os.path.exists(CONFIG['db_path']):
        return jsonify({'error': '数据库未初始化'}), 400
    
    try:
        db = DatabaseManager(CONFIG['db_path'])
        db.connect()
        
        # 类信息
        class_row = db.execute_query(f"SELECT name, file, is_component, is_entry, line_number FROM classes WHERE name = '{class_name}'")
        
        # 方法
        method_rows = db.execute_query(f"SELECT name, line_number, is_static, is_private FROM methods WHERE class_name = '{class_name}'")
        
        # 调用的方法
        call_out_rows = db.execute_query(f"SELECT callee, callee_class, line_number FROM calls WHERE caller_class = '{class_name}'")
        
        # 被调用的方法
        call_in_rows = db.execute_query(f"SELECT caller, caller_class, line_number FROM calls WHERE callee_class = '{class_name}'")
        
        # 子组件
        comp_child_rows = db.execute_query(f"SELECT child FROM components WHERE parent = '{class_name}'")
        
        # 父组件
        comp_parent_rows = db.execute_query(f"SELECT parent FROM components WHERE child = '{class_name}'")
        
        # 继承
        inherit_rows = db.execute_query(f"SELECT parent_class FROM inherits WHERE child_class = '{class_name}'")
        
        # 被继承
        inherited_rows = db.execute_query(f"SELECT child_class FROM inherits WHERE parent_class = '{class_name}'")
        
        db.close()
        
        return jsonify({
            'class': {
                'name': class_row[0][0] if class_row else class_name,
                'file': class_row[0][1] if class_row else '',
                'is_component': bool(class_row[0][2]) if class_row else False,
                'is_entry': bool(class_row[0][3]) if class_row else False,
                'line_number': class_row[0][4] if class_row else 0
            },
            'methods': [{'name': r[0], 'line_number': r[1], 'is_static': bool(r[2]), 'is_private': bool(r[3])} for r in method_rows],
            'calls_out': [{'callee': r[0], 'callee_class': r[1], 'line_number': r[2]} for r in call_out_rows],
            'calls_in': [{'caller': r[0], 'caller_class': r[1], 'line_number': r[2]} for r in call_in_rows],
            'component_children': [r[0] for r in comp_child_rows],
            'component_parents': [r[0] for r in comp_parent_rows],
            'inherits': [r[0] for r in inherit_rows],
            'inherited_by': [r[0] for r in inherited_rows]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_server(host='0.0.0.0', port=5000, db_path=None, project_path=None):
    """启动Web服务器"""
    CONFIG['db_path'] = db_path
    CONFIG['project_path'] = project_path
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║       ArkTS 知识图谱可视化系统                              ║
╠══════════════════════════════════════════════════════════╣
║  访问地址: http://{host}:{port}                              ║
║  数据库: {db_path or '未设置'}                                ║
║  项目: {project_path or '未设置'}                            ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ArkTS知识图谱可视化Web服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--db', help='数据库路径')
    parser.add_argument('--project', help='项目路径')
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, db_path=args.db, project_path=args.project)
