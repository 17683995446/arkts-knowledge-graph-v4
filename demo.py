#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS代码知识图谱系统 - 使用示例

本脚本演示如何使用知识图谱系统进行代码查询
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arkts_knowledge_graph import (
    DatabaseManager, 
    AIQueryInterface,
    KnowledgeGraphBuilder,
    build_knowledge_graph,
    ask_ai
)


def demo_without_ai(db_path: str = "code.db"):
    """演示不使用AI的直接SQL查询"""
    print("\n" + "=" * 60)
    print("直接SQL查询示例（无需AI）")
    print("=" * 60)
    
    db = DatabaseManager(db_path)
    db.connect()
    
    # 示例查询
    queries = [
        ("查询所有组件", 
         "SELECT name, file FROM classes WHERE is_component = 1"),
        
        ("查询入口组件", 
         "SELECT name FROM classes WHERE is_entry = 1"),
        
        ("查询UserService的所有方法", 
         "SELECT name, line_number FROM methods WHERE class_name = 'UserService'"),
        
        ("查询Index组件包含的子组件", 
         "SELECT child FROM components WHERE parent = 'Index'"),
        
        ("查询所有文件", 
         "SELECT path FROM files"),
        
        ("统计每个类的方法数量", 
         "SELECT class_name, COUNT(*) as method_count FROM methods GROUP BY class_name ORDER BY method_count DESC"),
        
        ("查询build方法所属的组件", 
         "SELECT m.class_name, c.is_component FROM methods m LEFT JOIN classes c ON m.class_name = c.name WHERE m.name = 'build'"),
    ]
    
    for title, sql in queries:
        print(f"\n【{title}】")
        print(f"SQL: {sql}")
        print("-" * 40)
        
        try:
            results = db.execute_query(sql)
            if results:
                for row in results:
                    print(f"  {row}")
            else:
                print("  (无结果)")
        except Exception as e:
            print(f"  错误: {e}")
    
    db.close()


def demo_with_ai(api_key: str, db_path: str = "code.db"):
    """演示使用AI的自然语言查询"""
    print("\n" + "=" * 60)
    print("AI自然语言查询示例")
    print("=" * 60)
    
    db = DatabaseManager(db_path)
    db.connect()
    
    ai = AIQueryInterface(api_key, db)
    
    # 自然语言问题
    questions = [
        "有哪些组件？",
        "Index组件包含哪些子组件？",
        "UserService有哪些方法？",
        "有多少个入口组件？",
        "列出所有文件",
    ]
    
    for question in questions:
        print(f"\n【问题】{question}")
        result = ai.ask(question)
        print(ai.format_result(result))
        print()
    
    db.close()


def interactive_query(api_key: str, db_path: str = "code.db"):
    """交互式查询模式"""
    print("\n" + "=" * 60)
    print("交互式查询模式（输入 'quit' 退出）")
    print("=" * 60)
    
    db = DatabaseManager(db_path)
    db.connect()
    
    ai = AIQueryInterface(api_key, db)
    
    while True:
        try:
            question = input("\n请输入问题: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if not question:
                continue
            
            result = ai.ask(question)
            print(ai.format_result(result))
            
        except KeyboardInterrupt:
            print("\n退出交互模式")
            break
    
    db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ArkTS代码知识图谱使用示例")
    parser.add_argument("--db", "-d", default="code.db", help="数据库路径")
    parser.add_argument("--api-key", "-k", help="硅基流动API密钥（用于AI查询）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式查询模式")
    
    args = parser.parse_args()
    
    # 检查数据库是否存在
    if not os.path.exists(args.db):
        print(f"错误: 数据库文件不存在: {args.db}")
        print("请先运行构建命令创建数据库:")
        print("  python arkts_knowledge_graph.py build --project <项目路径>")
        return
    
    if args.interactive:
        if not args.api_key:
            print("错误: 交互模式需要提供API密钥 --api-key")
            return
        interactive_query(args.api_key, args.db)
    else:
        # 演示直接SQL查询
        demo_without_ai(args.db)
        
        # 如果提供了API密钥，演示AI查询
        if args.api_key:
            demo_with_ai(args.api_key, args.db)
        else:
            print("\n" + "=" * 60)
            print("提示: 提供 --api-key 参数可启用AI自然语言查询")
            print("示例: python demo.py --api-key YOUR_API_KEY")
            print("=" * 60)


if __name__ == "__main__":
    main()
