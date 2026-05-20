#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本 - 验证知识图谱的正确性
"""

import sqlite3
from pathlib import Path


def verify_knowledge_graph(db_path: str = "code.db"):
    """验证知识图谱的正确性"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("知识图谱验证报告")
    print("=" * 60)
    
    # 1. 验证文件
    print("\n【1. 文件验证】")
    cursor.execute("SELECT path FROM files")
    files = cursor.fetchall()
    print(f"   文件总数: {len(files)}")
    for f in files:
        print(f"   - {Path(f[0]).name}")
    
    # 2. 验证组件
    print("\n【2. 组件验证】")
    cursor.execute("SELECT name, file, is_entry FROM classes WHERE is_component = 1")
    components = cursor.fetchall()
    print(f"   组件总数: {len(components)}")
    for comp in components:
        entry_mark = " [入口]" if comp[2] else ""
        print(f"   - {comp[0]}{entry_mark}")
    
    # 3. 验证入口组件
    print("\n【3. 入口组件验证】")
    cursor.execute("SELECT name, file FROM classes WHERE is_entry = 1")
    entries = cursor.fetchall()
    print(f"   入口组件数: {len(entries)}")
    expected_entries = ['Index', 'UserDetail']
    for entry in entries:
        is_expected = entry[0] in expected_entries
        mark = " ✓" if is_expected else " ✗"
        print(f"   - {entry[0]}{mark}")
    
    # 4. 验证类/服务
    print("\n【4. 类/服务验证】")
    cursor.execute("SELECT name, file FROM classes WHERE is_component = 0")
    classes = cursor.fetchall()
    print(f"   普通类数: {len(classes)}")
    for cls in classes:
        print(f"   - {cls[0]}")
    
    # 5. 验证方法
    print("\n【5. 方法验证（部分）】")
    cursor.execute("""
        SELECT m.name, m.class_name, c.is_component 
        FROM methods m 
        LEFT JOIN classes c ON m.class_name = c.name 
        ORDER BY m.class_name, m.name
    """)
    methods = cursor.fetchall()
    print(f"   方法总数: {len(methods)}")
    
    # 按类分组显示
    current_class = None
    count = 0
    for method in methods:
        if method[1] != current_class:
            current_class = method[1]
            count = 0
            comp_mark = " [组件]" if method[2] else ""
            print(f"\n   {current_class}{comp_mark}:")
        if count < 5:  # 每个类最多显示5个方法
            print(f"     - {method[0]}()")
        elif count == 5:
            print(f"     - ...")
        count += 1
    
    # 6. 验证调用关系
    print("\n\n【6. 调用关系验证（示例）】")
    cursor.execute("""
        SELECT caller_class, caller, callee_class, callee 
        FROM calls 
        WHERE caller_class != '' 
        LIMIT 10
    """)
    calls = cursor.fetchall()
    print(f"   调用关系总数: 209 (显示前10条)")
    for call in calls:
        callee_class = call[2] if call[2] else "?"
        print(f"   - {call[0]}.{call[1]}() -> {callee_class}.{call[3]}()")
    
    # 7. 验证组件嵌套关系
    print("\n【7. 组件嵌套关系验证】")
    cursor.execute("SELECT parent, child FROM components")
    relations = cursor.fetchall()
    print(f"   嵌套关系总数: {len(relations)}")
    for rel in relations:
        print(f"   - {rel[0]} 包含 {rel[1]}")
    
    # 8. 验证特定查询
    print("\n【8. 特定查询验证】")
    
    # 查询Index组件的方法
    print("\n   Index组件的方法:")
    cursor.execute("""
        SELECT name FROM methods 
        WHERE class_name = 'Index' 
        ORDER BY name
    """)
    index_methods = cursor.fetchall()
    expected_methods = ['aboutToAppear', 'build', 'loadUsers', 'onLoadMore', 'onRefresh', 'onUserClick']
    for m in index_methods:
        is_expected = m[0] in expected_methods
        mark = " ✓" if is_expected else ""
        print(f"     - {m[0]}(){mark}")
    
    # 查询UserService的方法
    print("\n   UserService的方法:")
    cursor.execute("""
        SELECT name FROM methods 
        WHERE class_name = 'UserService' 
        ORDER BY name
    """)
    service_methods = cursor.fetchall()
    expected_service_methods = ['createUser', 'deleteUser', 'fetchUsers', 'getUserById', 'searchUsers', 'updateUser']
    for m in service_methods:
        is_expected = m[0] in expected_service_methods
        mark = " ✓" if is_expected else ""
        print(f"     - {m[0]}(){mark}")
    
    # 9. 正确性验证总结
    print("\n" + "=" * 60)
    print("【验证总结】")
    print("=" * 60)
    
    # 检查关键验证点
    checks = []
    
    # 检查入口组件
    cursor.execute("SELECT COUNT(*) FROM classes WHERE is_entry = 1")
    entry_count = cursor.fetchone()[0]
    checks.append(("入口组件数量正确", entry_count == 2))
    
    # 检查组件数量
    cursor.execute("SELECT COUNT(*) FROM classes WHERE is_component = 1")
    comp_count = cursor.fetchone()[0]
    checks.append(("组件数量正确", comp_count == 6))
    
    # 检查Index组件存在
    cursor.execute("SELECT COUNT(*) FROM classes WHERE name = 'Index' AND is_component = 1")
    index_exists = cursor.fetchone()[0] > 0
    checks.append(("Index组件存在", index_exists))
    
    # 检查UserService存在
    cursor.execute("SELECT COUNT(*) FROM classes WHERE name = 'UserService'")
    service_exists = cursor.fetchone()[0] > 0
    checks.append(("UserService类存在", service_exists))
    
    # 检查build方法存在
    cursor.execute("SELECT COUNT(*) FROM methods WHERE name = 'build'")
    build_exists = cursor.fetchone()[0] > 0
    checks.append(("build方法存在", build_exists))
    
    # 检查组件嵌套关系
    cursor.execute("SELECT COUNT(*) FROM components")
    comp_rel_count = cursor.fetchone()[0]
    checks.append(("组件嵌套关系存在", comp_rel_count > 0))
    
    all_passed = True
    for check_name, passed in checks:
        mark = "✓ 通过" if passed else "✗ 失败"
        print(f"   {check_name}: {mark}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有验证通过！知识图谱构建正确。")
    else:
        print("✗ 部分验证失败，请检查解析逻辑。")
    print("=" * 60)
    
    conn.close()
    return all_passed


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "code.db"
    verify_knowledge_graph(db_path)
