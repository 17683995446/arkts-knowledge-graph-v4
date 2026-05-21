#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS知识图谱系统 - 集成测试
测试模块间的集成：
- 解析器 → 数据库的完整流程
- 多文件并行解析
- 数据库事务一致性
- 错误传播和恢复
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arkts_knowledge_graph import (
    DatabaseManager,
    ArkTSParser,
    FileInfo,
    ClassInfo,
    MethodInfo,
    CallRelation,
    ComponentRelation,
    InheritRelation,
    KnowledgeGraphBuilder
)


# ============================================================================
# 测试工具类
# ============================================================================

class TestProjectBuilder:
    """构建测试项目"""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def create_simple_project(self):
        """创建简单项目"""
        # 创建目录
        components = os.path.join(self.base_dir, 'components')
        pages = os.path.join(self.base_dir, 'pages')
        os.makedirs(components, exist_ok=True)
        os.makedirs(pages, exist_ok=True)

        # Header组件
        with open(os.path.join(components, 'Header.ets'), 'w', encoding='utf-8') as f:
            f.write('''
@Component
struct Header {
  @State title: string = 'Header';

  build() {
    Row() {
      Text(this.title)
    }
  }
}
''')

        # Footer组件
        with open(os.path.join(components, 'Footer.ets'), 'w', encoding='utf-8') as f:
            f.write('''
@Component
struct Footer {
  @State copyright: string = '2024';

  build() {
    Row() {
      Text(this.copyright)
    }
  }
}
''')

        # 主页
        with open(os.path.join(pages, 'Index.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';

@Entry
@Component
struct Index {
  build() {
    Column() {
      Header()
      Text('Main Content')
      Footer()
    }
  }
}
''')

    def create_complex_project(self):
        """创建复杂项目（带继承和调用链）"""
        # 创建目录
        base = os.path.join(self.base_dir, 'base')
        features = os.path.join(self.base_dir, 'features')
        os.makedirs(base, exist_ok=True)
        os.makedirs(features, exist_ok=True)

        # 基类
        with open(os.path.join(base, 'BaseComponent.ets'), 'w', encoding='utf-8') as f:
            f.write('''
@Component
struct BaseComponent {
  @State protected data: string = '';

  protected updateData(newData: string): void {
    this.data = newData;
  }

  build() {
    Column() {}
  }
}
''')

        # 继承基类的组件
        with open(os.path.join(features, 'FeatureA.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { BaseComponent } from '../base/BaseComponent';

@Component
struct FeatureA extends BaseComponent {
  private handleClick(): void {
    this.updateData('clicked');
  }

  build() {
    Column() {
      Text(this.data)
        .onClick(() => this.handleClick())
    }
  }
}
''')

        with open(os.path.join(features, 'FeatureB.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { BaseComponent } from '../base/BaseComponent';

@Component
struct FeatureB extends BaseComponent {
  private processData(): void {
    this.updateData('processed');
  }

  build() {
    Column() {
      Button('Process')
        .onClick(() => this.processData())
    }
  }
}
''')

        # 主页面
        with open(os.path.join(self.base_dir, 'Main.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { FeatureA } from './features/FeatureA';
import { FeatureB } from './features/FeatureB';

@Entry
@Component
struct Main {
  build() {
    Column() {
      FeatureA()
      FeatureB()
    }
  }
}
''')

    def create_circular_dependency_project(self):
        """创建循环依赖项目"""
        os.makedirs(self.base_dir, exist_ok=True)

        with open(os.path.join(self.base_dir, 'A.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { B } from './B';

@Component
struct A {
  @State refB: B | null = null;

  useB(): void {
    if (this.refB) {
      this.refB.methodFromA();
    }
  }

  build() {
    Column() {
      B()
    }
  }
}
''')

        with open(os.path.join(self.base_dir, 'B.ets'), 'w', encoding='utf-8') as f:
            f.write('''
import { A } from './A';

@Component
struct B {
  @State refA: A | null = null;

  methodFromA(): void {
    console.log('Called from A');
  }

  useA(): void {
    if (this.refA) {
      this.refA.useB();
    }
  }

  build() {
    Column() {}
  }
}
''')

    def create_error_project(self):
        """创建包含错误的项目"""
        os.makedirs(self.base_dir, exist_ok=True)

        # 语法错误的文件
        with open(os.path.join(self.base_dir, 'Error.ets'), 'w', encoding='utf-8') as f:
            f.write('''
@Component
struct ErrorComponent {
  // 不完整的代码
  method(): void {
    if (true) {
      console.log('missing brace')
  // 缺少闭合括号

  build() {
    Column() {}
  }
}
''')

        # 正常文件
        with open(os.path.join(self.base_dir, 'Normal.ets'), 'w', encoding='utf-8') as f:
            f.write('''
@Component
struct NormalComponent {
  build() {
    Column() {
      Text('Normal')
    }
  }
}
''')

    def create_large_project(self, num_files: int = 50):
        """创建大型项目"""
        os.makedirs(self.base_dir, exist_ok=True)

        for i in range(num_files):
            with open(os.path.join(self.base_dir, f'Component{i}.ets'), 'w', encoding='utf-8') as f:
                f.write(f'''
@Component
struct Component{i} {{
  @State count: number = 0;

  increment(): void {{
    this.count++;
  }}

  build() {{
    Column() {{
      Text(`Count: ${{this.count}}`)
    }}
  }}
}}
''')


# ============================================================================
# 集成测试类
# ============================================================================

class TestParserToDatabaseIntegration(unittest.TestCase):
    """测试解析器到数据库的集成"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.project_builder = TestProjectBuilder(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_simple_project_pipeline(self):
        """测试简单项目的完整流程"""
        # 创建项目
        self.project_builder.create_simple_project()

        # 构建知识图谱
        builder = KnowledgeGraphBuilder(self.db_path)
        stats = builder.build(self.temp_dir)
        builder.close()

        # 验证统计信息
        self.assertEqual(stats['files'], 3)
        self.assertEqual(stats['classes'], 3)
        self.assertEqual(stats['components'], 3)
        self.assertEqual(stats['entry_components'], 1)

        # 验证数据库内容
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM classes")
        class_names = {row[0] for row in cursor.fetchall()}
        self.assertIn('Header', class_names)
        self.assertIn('Footer', class_names)
        self.assertIn('Index', class_names)

        conn.close()

    def test_complex_project_with_inheritance(self):
        """测试带继承的复杂项目"""
        self.project_builder.create_complex_project()

        builder = KnowledgeGraphBuilder(self.db_path)
        stats = builder.build(self.temp_dir)
        builder.close()

        # 验证继承关系
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT child_class, parent_class FROM inherits")
        inherits = cursor.fetchall()
        self.assertGreater(len(inherits), 0)

        inherit_pairs = {(row[0], row[1]) for row in inherits}
        self.assertIn(('FeatureA', 'BaseComponent'), inherit_pairs)
        self.assertIn(('FeatureB', 'BaseComponent'), inherit_pairs)

        conn.close()

    def test_circular_dependency_handling(self):
        """测试循环依赖处理"""
        self.project_builder.create_circular_dependency_project()

        # 解析不应崩溃
        parser = ArkTSParser()
        try:
            result = parser.parse_project(self.temp_dir)
            # 应该能解析两个组件
            class_names = [c.name for c in result['classes']]
            self.assertIn('A', class_names)
            self.assertIn('B', class_names)
        except Exception as e:
            self.fail(f"解析器不应在循环依赖时崩溃: {e}")

    def test_error_recovery(self):
        """测试错误恢复"""
        self.project_builder.create_error_project()

        # 构建不应崩溃
        builder = KnowledgeGraphBuilder(self.db_path)
        try:
            stats = builder.build(self.temp_dir)
            builder.close()

            # 应该能解析正常文件
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM classes")
            class_names = {row[0] for row in cursor.fetchall()}
            conn.close()

            self.assertIn('NormalComponent', class_names)
        except Exception as e:
            self.fail(f"构建器不应在错误文件时崩溃: {e}")


class TestMultiFileParsing(unittest.TestCase):
    """测试多文件并行解析"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.project_builder = TestProjectBuilder(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_large_project_performance(self):
        """测试大型项目性能"""
        self.project_builder.create_large_project(50)

        builder = KnowledgeGraphBuilder(self.db_path)
        start_time = time.time()
        stats = builder.build(self.temp_dir)
        elapsed_time = time.time() - start_time
        builder.close()

        # 验证所有文件都被处理
        self.assertEqual(stats['files'], 50)
        self.assertEqual(stats['classes'], 50)

        # 性能检查（应该在合理时间内完成）
        self.assertLess(elapsed_time, 30, "处理50个文件应该少于30秒")

    def test_parallel_parsing_consistency(self):
        """测试并行解析一致性"""
        self.project_builder.create_simple_project()

        # 多次解析，验证结果一致
        results = []
        for _ in range(3):
            parser = ArkTSParser()
            result = parser.parse_project(self.temp_dir)
            results.append({
                'files': len(result['files']),
                'classes': len(result['classes']),
                'methods': len(result['methods'])
            })

        # 所有结果应该相同
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])


class TestDatabaseTransactionConsistency(unittest.TestCase):
    """测试数据库事务一致性"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.project_builder = TestProjectBuilder(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_transaction_rollback(self):
        """测试事务回滚"""
        db = DatabaseManager(self.db_path)
        db.connect()
        db.create_tables()

        # 开始事务
        db.conn.execute('BEGIN')

        # 插入数据
        db.insert_file(FileInfo(path='/test/file.ets'))

        # 回滚
        db.conn.rollback()

        # 验证数据未提交
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)

        db.close()

    def test_transaction_commit(self):
        """测试事务提交"""
        db = DatabaseManager(self.db_path)
        db.connect()
        db.create_tables()

        # 插入数据
        db.insert_file(FileInfo(path='/test/file.ets'))
        db.insert_class(ClassInfo(name='Test', file='/test/file.ets'))

        # 关闭（会自动提交）
        db.close()

        # 重新连接，验证数据存在
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        self.assertEqual(cursor.fetchone()[0], 1)
        cursor.execute("SELECT COUNT(*) FROM classes")
        self.assertEqual(cursor.fetchone()[0], 1)
        conn.close()

    def test_clear_tables_transaction(self):
        """测试清空表的事务性"""
        db = DatabaseManager(self.db_path)
        db.connect()
        db.create_tables()

        # 插入数据
        db.insert_file(FileInfo(path='/test/file.ets'))
        db.insert_class(ClassInfo(name='Test', file='/test/file.ets'))

        # 清空表
        db.clear_tables()

        # 验证所有表都为空
        cursor = db.conn.cursor()
        for table in ['files', 'classes', 'methods', 'calls', 'components', 'inherits']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            self.assertEqual(cursor.fetchone()[0], 0)

        db.close()


class TestErrorPropagation(unittest.TestCase):
    """测试错误传播"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parser_error_handling(self):
        """测试解析器错误处理"""
        parser = ArkTSParser()

        # 测试不存在的目录
        result = parser.parse_project('/nonexistent/directory')
        self.assertEqual(result['files'], [])
        self.assertEqual(result['classes'], [])

        # 测试空目录
        result = parser.parse_project(self.temp_dir)
        self.assertEqual(result['files'], [])
        self.assertEqual(result['classes'], [])

    def test_database_error_handling(self):
        """测试数据库错误处理"""
        # 测试无效的数据库路径
        with self.assertRaises(Exception):
            db = DatabaseManager('/invalid/path/to/db.sqlite')
            db.connect()

    def test_builder_error_handling(self):
        """测试构建器错误处理"""
        builder = KnowledgeGraphBuilder(self.db_path)

        # 测试不存在的项目目录
        stats = builder.build('/nonexistent/project')
        self.assertEqual(stats['files'], 0)

        builder.close()


class TestDataIntegrity(unittest.TestCase):
    """测试数据完整性"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.project_builder = TestProjectBuilder(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_foreign_key_integrity(self):
        """测试外键完整性"""
        self.project_builder.create_simple_project()

        builder = KnowledgeGraphBuilder(self.db_path)
        stats = builder.build(self.temp_dir)
        builder.close()

        # 验证所有方法都关联到有效的类
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT m.name, m.class_name 
            FROM methods m 
            LEFT JOIN classes c ON m.class_name = c.name 
            WHERE c.name IS NULL
        ''')
        orphaned_methods = cursor.fetchall()
        self.assertEqual(len(orphaned_methods), 0, "存在孤立的方法")

        conn.close()

    def test_line_number_consistency(self):
        """测试行号一致性"""
        self.project_builder.create_simple_project()

        builder = KnowledgeGraphBuilder(self.db_path)
        builder.build(self.temp_dir)
        builder.close()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 验证所有行号都是正数
        cursor.execute("SELECT line_number FROM classes WHERE line_number <= 0")
        self.assertEqual(len(cursor.fetchall()), 0)

        cursor.execute("SELECT line_number FROM methods WHERE line_number <= 0")
        self.assertEqual(len(cursor.fetchall()), 0)

        conn.close()

    def test_unique_constraints(self):
        """测试唯一性约束"""
        db = DatabaseManager(self.db_path)
        db.connect()
        db.create_tables()

        # 插入重复文件应该处理
        db.insert_file(FileInfo(path='/test/file.ets'))
        # 再次插入相同的文件（不应该报错，应该替换或忽略）
        db.insert_file(FileInfo(path='/test/file.ets'))

        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files WHERE path = '/test/file.ets'")
        count = cursor.fetchone()[0]
        # 应该只有一条记录
        self.assertEqual(count, 1)

        db.close()


# ============================================================================
# 性能测试
# ============================================================================

class TestPerformance(unittest.TestCase):
    """性能测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.project_builder = TestProjectBuilder(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parsing_performance(self):
        """测试解析性能"""
        self.project_builder.create_large_project(100)

        parser = ArkTSParser()
        start_time = time.time()
        result = parser.parse_project(self.temp_dir)
        elapsed_time = time.time() - start_time

        # 验证结果
        self.assertEqual(len(result['files']), 100)
        self.assertEqual(len(result['classes']), 100)

        # 性能指标
        print(f"\n解析100个文件耗时: {elapsed_time:.2f}秒")
        self.assertLess(elapsed_time, 60, "解析100个文件应该少于60秒")

    def test_database_insertion_performance(self):
        """测试数据库插入性能"""
        db = DatabaseManager(self.db_path)
        db.connect()
        db.create_tables()

        # 批量插入
        start_time = time.time()
        for i in range(1000):
            db.insert_class(ClassInfo(
                name=f'Class{i}',
                file=f'/test/file{i}.ets',
                line_number=i
            ))
        elapsed_time = time.time() - start_time

        print(f"\n插入1000个类耗时: {elapsed_time:.2f}秒")
        self.assertLess(elapsed_time, 10, "插入1000个类应该少于10秒")

        db.close()


# ============================================================================
# 主程序
# ============================================================================

if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestParserToDatabaseIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiFileParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseTransactionConsistency))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorPropagation))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "="*70)
    print("集成测试总结")
    print("="*70)
    print(f"运行测试数: {result.testsRun}")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, trace in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n错误的测试:")
        for test, trace in result.errors:
            print(f"  - {test}")

    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)
