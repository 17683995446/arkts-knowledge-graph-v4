#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArkTS知识图谱系统 - 全面单元测试
测试目标：100% 代码分支覆盖

测试范围：
1. DatabaseManager 的所有方法
2. ArkTSParser 的所有解析逻辑
3. 所有正则表达式匹配
4. 所有边界条件（空文件、大文件、特殊字符）
5. 所有异常处理路径
6. 所有数据类型转换
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

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
# 测试数据生成器
# ============================================================================

class TestDataGenerator:
    """生成各种测试数据"""

    @staticmethod
    def generate_simple_component() -> str:
        """生成简单组件代码"""
        return '''
@Component
struct SimpleComponent {
  @State count: number = 0;

  increment(): void {
    this.count++;
  }

  build() {
    Column() {
      Text(`${this.count}`)
    }
  }
}
'''

    @staticmethod
    def generate_complex_component() -> str:
        """生成复杂组件代码"""
        return '''
@Entry
@Component
struct ComplexComponent {
  @State private data: string = '';
  @Prop @Watch('onChange') value: number = 0;
  @StorageLink('theme') theme: string = 'light';

  aboutToAppear(): void {
    this.initialize();
  }

  private initialize(): void {
    this.data = 'initialized';
  }

  private onChange(): void {
    console.log('changed');
  }

  public async fetchData(): Promise<void> {
    const result = await this.apiCall();
    this.data = result;
  }

  private apiCall(): Promise<string> {
    return Promise.resolve('data');
  }

  static helper(): void {
    console.log('helper');
  }

  build() {
    Column() {
      Text(this.data)
    }
  }
}
'''

    @staticmethod
    def generate_inheritance_code() -> str:
        """生成继承关系代码"""
        return '''
abstract struct BaseClass {
  abstract abstractMethod(): void;

  concreteMethod(): void {
    console.log('concrete');
  }
}

@Component
struct ChildClass extends BaseClass {
  abstractMethod(): void {
    console.log('implemented');
  }
}

interface IInterface {
  interfaceMethod(): void;
}

@Component
struct Implementor implements IInterface {
  interfaceMethod(): void {
    console.log('implemented');
  }
}
'''

    @staticmethod
    def generate_arrow_functions() -> str:
        """生成箭头函数代码"""
        return '''
@Component
struct ArrowComponent {
  handler = (event: Event): void => {
    this.process(event);
  };

  callback = async (data: string): Promise<void> => {
    await this.save(data);
  };

  private process(event: Event): void {}
  private async save(data: string): Promise<void> {}

  build() {
    Column() {}
  }
}
'''

    @staticmethod
    def generate_edge_cases() -> str:
        """生成边界情况代码"""
        return '''
// 空组件
@Component
struct EmptyComponent {
  build() {}
}

// 只有注释的组件
@Component
struct CommentOnlyComponent {
  // This is a comment
  /* Multi-line
     comment */
  build() {
    Text('test');
  }
}

// 包含特殊字符
@Component
struct SpecialCharsComponent {
  @State data: string = "test\\n\\t\"quoted\"";

  method(): void {
    const regex = /\\w+/g;
    const template = `Hello ${this.data}`;
  }

  build() {
    Text(this.data)
  }
}

// 深层嵌套
@Component
struct DeepComponent {
  build() {
    Column() {
      Row() {
        Stack() {
          Grid() {
            GridItem() {
              Text('deep')
            }
          }
        }
      }
    }
  }
}
'''

    @staticmethod
    def generate_unicode_code() -> str:
        """生成包含Unicode的代码"""
        return '''
// 中文注释
@Component
struct 中文组件 {
  @State 名称: string = '测试';

  方法(): void {
    console.log('中文输出');
  }

  build() {
    Text(this.名称)
  }
}

// 日文
@Component
struct 日本語コンポーネント {
  @State 名前: string = 'テスト';
}

// 韩文
@Component
struct 한국어컴포넌트 {
  @State 이름: string = '테스트';
}
'''


# ============================================================================
# DatabaseManager 测试
# ============================================================================

class TestDatabaseManager(unittest.TestCase):
    """测试数据库管理器"""

    def setUp(self):
        """每个测试前执行"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = DatabaseManager(self.db_path)
        self.db.connect()
        self.db.create_tables()

    def tearDown(self):
        """每个测试后执行"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_connection(self):
        """测试数据库连接"""
        # 验证连接成功
        self.assertIsNotNone(self.db.conn)
        # 验证外键约束已启用
        cursor = self.db.conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)

    def test_create_tables(self):
        """测试创建表"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {'files', 'classes', 'methods', 'calls', 'components', 'inherits'}
        self.assertTrue(expected_tables.issubset(tables))

    def test_insert_file(self):
        """测试插入文件"""
        file_info = FileInfo(path='/test/file.ets')
        self.db.insert_file(file_info)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT path FROM files WHERE path = ?", ('/test/file.ets',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], '/test/file.ets')

    def test_insert_class(self):
        """测试插入类"""
        class_info = ClassInfo(
            name='TestClass',
            file='/test/file.ets',
            is_component=True,
            is_entry=False,
            line_number=10
        )
        self.db.insert_class(class_info)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name, is_component, line_number FROM classes WHERE name = ?", ('TestClass',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'TestClass')
        self.assertEqual(result[1], 1)
        self.assertEqual(result[2], 10)

    def test_insert_method(self):
        """测试插入方法"""
        method_info = MethodInfo(
            name='testMethod',
            class_name='TestClass',
            file='/test/file.ets',
            line_number=20,
            is_static=True,
            is_private=False
        )
        self.db.insert_method(method_info)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name, is_static, is_private FROM methods WHERE name = ?", ('testMethod',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'testMethod')
        self.assertEqual(result[1], 1)
        self.assertEqual(result[2], 0)

    def test_insert_call(self):
        """测试插入调用关系"""
        call = CallRelation(
            caller='methodA',
            caller_class='ClassA',
            callee='methodB',
            callee_class='ClassB',
            file='/test/file.ets',
            line_number=30
        )
        self.db.insert_call(call)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT caller, callee FROM calls WHERE caller = ?", ('methodA',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'methodA')
        self.assertEqual(result[1], 'methodB')

    def test_insert_component_relation(self):
        """测试插入组件关系"""
        comp = ComponentRelation(
            parent='ParentComponent',
            child='ChildComponent',
            file='/test/file.ets',
            line_number=40
        )
        self.db.insert_component_relation(comp)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT parent, child FROM components WHERE parent = ?", ('ParentComponent',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'ParentComponent')
        self.assertEqual(result[1], 'ChildComponent')

    def test_insert_inherit(self):
        """测试插入继承关系"""
        inherit = InheritRelation(
            child_class='ChildClass',
            parent_class='ParentClass',
            file='/test/file.ets',
            line_number=50
        )
        self.db.insert_inherit(inherit)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT child_class, parent_class FROM inherits WHERE child_class = ?", ('ChildClass',))
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'ChildClass')
        self.assertEqual(result[1], 'ParentClass')

    def test_clear_tables(self):
        """测试清空表"""
        # 插入测试数据
        self.db.insert_file(FileInfo(path='/test/file.ets'))
        self.db.insert_class(ClassInfo(name='Test', file='/test/file.ets'))
        
        # 清空表
        self.db.clear_tables()
        
        # 验证数据已清空
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        self.assertEqual(cursor.fetchone()[0], 0)
        cursor.execute("SELECT COUNT(*) FROM classes")
        self.assertEqual(cursor.fetchone()[0], 0)

    def test_get_statistics(self):
        """测试获取统计信息"""
        # 插入测试数据
        self.db.insert_file(FileInfo(path='/test/file.ets'))
        self.db.insert_class(ClassInfo(name='Test', file='/test/file.ets', is_component=True, is_entry=True))
        self.db.insert_method(MethodInfo(name='test', class_name='Test', file='/test/file.ets'))
        
        stats = self.db.get_statistics()
        
        self.assertEqual(stats['files'], 1)
        self.assertEqual(stats['classes'], 1)
        self.assertEqual(stats['components'], 1)
        self.assertEqual(stats['entry_components'], 1)
        self.assertEqual(stats['methods'], 1)

    def test_execute_query(self):
        """测试执行查询"""
        self.db.insert_file(FileInfo(path='/test/file.ets'))
        
        results = self.db.execute_query("SELECT path FROM files")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], '/test/file.ets')

    def test_get_schema_description(self):
        """测试获取Schema描述"""
        schema = self.db.get_schema_description()
        
        # 验证包含所有表名
        self.assertIn('files', schema)
        self.assertIn('classes', schema)
        self.assertIn('methods', schema)
        self.assertIn('calls', schema)
        self.assertIn('components', schema)
        self.assertIn('inherits', schema)


# ============================================================================
# ArkTSParser 测试
# ============================================================================

class TestArkTSParser(unittest.TestCase):
    """测试ArkTS解析器"""

    def setUp(self):
        """每个测试前执行"""
        self.parser = ArkTSParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """每个测试后执行"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, filename: str, content: str) -> str:
        """创建测试文件"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_strip_comments_and_strings(self):
        """测试移除注释和字符串"""
        content = '''
// Single line comment
const str1 = "string with // comment inside";
const str2 = 'another string';
/* Multi-line
   comment */
const template = `template ${value} string`;
const code = "actual code";
'''
        stripped = self.parser._strip_comments_and_strings(content)
        
        # 验证注释被移除
        self.assertNotIn('// Single', stripped)
        self.assertNotIn('/* Multi-line', stripped)
        # 验证字符串被替换为空格
        self.assertNotIn('"string with', stripped)
        self.assertNotIn("'another string'", stripped)
        # 验证代码保留
        self.assertIn('const code', stripped)

    def test_parse_simple_component(self):
        """测试解析简单组件"""
        content = TestDataGenerator.generate_simple_component()
        filepath = self.create_test_file('Simple.ets', content)
        
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证解析到类
        class_names = [c.name for c in result['classes']]
        self.assertIn('SimpleComponent', class_names)
        
        # 验证解析到方法
        method_names = [m.name for m in result['methods']]
        self.assertIn('increment', method_names)
        self.assertIn('build', method_names)

    def test_parse_complex_decorators(self):
        """测试解析复杂装饰器"""
        content = '''
@Entry
@Component
@Preview
struct DecoratedComponent {
  @State @Watch('onChange') value: number = 0;
  @StorageProp('token') token: string = '';
  @Provide context: any = {};

  onChange(): void {}

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('Decorated.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证组件被识别
        components = [c for c in result['classes'] if c.is_component]
        self.assertEqual(len(components), 1)
        self.assertTrue(components[0].is_entry)

    def test_parse_inheritance(self):
        """测试解析继承关系"""
        content = TestDataGenerator.generate_inheritance_code()
        self.create_test_file('Inheritance.ets', content)
        
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证继承关系
        inherit_names = [(i.child_class, i.parent_class) for i in result['inherits']]
        self.assertIn(('ChildClass', 'BaseClass'), inherit_names)

    def test_parse_arrow_functions(self):
        """测试解析箭头函数"""
        content = TestDataGenerator.generate_arrow_functions()
        self.create_test_file('Arrow.ets', content)
        
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证箭头函数属性被识别为方法
        method_names = [m.name for m in result['methods']]
        self.assertIn('handler', method_names)
        self.assertIn('callback', method_names)

    def test_parse_static_methods(self):
        """测试解析静态方法"""
        content = '''
@Component
struct StaticComponent {
  static staticMethod(): void {
    console.log('static');
  }

  private instanceMethod(): void {}

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('Static.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证静态方法
        static_methods = [m for m in result['methods'] if m.is_static]
        self.assertEqual(len(static_methods), 1)
        self.assertEqual(static_methods[0].name, 'staticMethod')

    def test_parse_private_methods(self):
        """测试解析私有方法"""
        content = '''
@Component
struct PrivateComponent {
  private privateMethod(): void {}
  public publicMethod(): void {}
  protected protectedMethod(): void {}

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('Private.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证私有方法
        private_methods = [m for m in result['methods'] if m.is_private]
        self.assertEqual(len(private_methods), 1)
        self.assertEqual(private_methods[0].name, 'privateMethod')

    def test_parse_call_relations(self):
        """测试解析调用关系"""
        content = '''
@Component
struct CallComponent {
  methodA(): void {
    this.methodB();
    helper.externalCall();
  }

  methodB(): void {
    console.log('B');
  }

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('Call.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证调用关系
        calls = [(c.caller, c.callee) for c in result['calls']]
        self.assertIn(('methodA', 'methodB'), calls)

    def test_parse_unicode(self):
        """测试解析Unicode代码"""
        content = TestDataGenerator.generate_unicode_code()
        self.create_test_file('Unicode.ets', content)
        
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证Unicode类名被解析
        class_names = [c.name for c in result['classes']]
        self.assertIn('中文组件', class_names)

    def test_parse_empty_file(self):
        """测试解析空文件"""
        self.create_test_file('Empty.ets', '')
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证没有错误
        self.assertEqual(len(result['classes']), 0)
        self.assertEqual(len(result['methods']), 0)

    def test_parse_file_with_only_comments(self):
        """测试解析只有注释的文件"""
        content = '''
// This is a comment
/* Multi-line
   comment */
'''
        self.create_test_file('Comments.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证没有解析出内容
        self.assertEqual(len(result['classes']), 0)

    def test_skip_identifiers(self):
        """测试跳过内置标识符"""
        content = '''
@Component
struct SkipComponent {
  build() {
    console.log('test');
    Math.abs(-1);
    Array.from([1, 2, 3]);
    Promise.resolve();
  }
}
'''
        self.create_test_file('Skip.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证内置方法不被记录为调用
        call_callees = [c.callee for c in result['calls']]
        self.assertNotIn('log', call_callees)
        self.assertNotIn('abs', call_callees)

    def test_find_matching_brace(self):
        """测试查找匹配的大括号"""
        content = '{ outer { inner } }'
        stripped = self.parser._strip_comments_and_strings(content)
        pos = stripped.find('{')
        end_pos = self.parser._find_matching_brace(stripped, pos)
        self.assertEqual(stripped[end_pos], '}')


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases(unittest.TestCase):
    """测试边界条件"""

    def setUp(self):
        self.parser = ArkTSParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def test_very_long_file(self):
        """测试超长文件"""
        # 生成大量重复代码
        methods = '\n'.join([f'  method{i}(): void {{}}' for i in range(100)])
        content = f'''
@Component
struct LongComponent {{
{methods}

  build() {{
    Column() {{}}
  }}
}}
'''
        self.create_test_file('Long.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证所有方法都被解析
        self.assertEqual(len(result['methods']), 101)  # 100 + build

    def test_deeply_nested_calls(self):
        """测试深层嵌套调用"""
        content = '''
@Component
struct DeepCallComponent {
  level1(): void {
    this.level2();
  }
  level2(): void {
    this.level3();
  }
  level3(): void {
    this.level4();
  }
  level4(): void {
    console.log('deep');
  }

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('DeepCall.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证调用链
        calls = [(c.caller, c.callee) for c in result['calls']]
        self.assertIn(('level1', 'level2'), calls)
        self.assertIn(('level2', 'level3'), calls)
        self.assertIn(('level3', 'level4'), calls)

    def test_special_characters_in_strings(self):
        """测试字符串中的特殊字符"""
        content = '''
@Component
struct SpecialComponent {
  @State data: string = "line1\\nline2\\ttab\\\"quote\\\"";

  build() {
    Text(this.data)
  }
}
'''
        self.create_test_file('Special.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证组件被正确解析
        self.assertEqual(len(result['classes']), 1)

    def test_malformed_code(self):
        """测试格式错误的代码"""
        content = '''
@Component
struct BrokenComponent {
  method(): void {
    // 不完整的代码
    if (true) {
      console.log('missing brace')
  }

  build() {
    Column() {}
  }
}
'''
        self.create_test_file('Broken.ets', content)
        
        # 验证解析器不会崩溃
        try:
            result = self.parser.parse_project(self.temp_dir)
            # 即使代码有问题，也应该能解析部分内容
            self.assertGreaterEqual(len(result['classes']), 0)
        except Exception as e:
            self.fail(f"Parser should not crash on malformed code: {e}")

    def test_multiple_classes_in_file(self):
        """测试单个文件中的多个类"""
        content = '''
@Component
struct ComponentA {
  build() {
    Column() {}
  }
}

@Component
struct ComponentB {
  build() {
    Row() {}
  }
}

class RegularClass {
  method(): void {}
}
'''
        self.create_test_file('Multiple.ets', content)
        result = self.parser.parse_project(self.temp_dir)
        
        # 验证所有类都被解析
        class_names = [c.name for c in result['classes']]
        self.assertIn('ComponentA', class_names)
        self.assertIn('ComponentB', class_names)
        self.assertIn('RegularClass', class_names)


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'integration.db')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_project(self):
        """创建测试项目"""
        # 创建目录结构
        components_dir = os.path.join(self.temp_dir, 'components')
        pages_dir = os.path.join(self.temp_dir, 'pages')
        os.makedirs(components_dir)
        os.makedirs(pages_dir)

        # 创建组件文件
        with open(os.path.join(components_dir, 'Header.ets'), 'w') as f:
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

        # 创建页面文件
        with open(os.path.join(pages_dir, 'Index.ets'), 'w') as f:
            f.write('''
import { Header } from '../components/Header';

@Entry
@Component
struct Index {
  build() {
    Column() {
      Header()
      Text('Content')
    }
  }
}
''')

    def test_full_pipeline(self):
        """测试完整流程"""
        self.create_test_project()
        
        # 构建知识图谱
        builder = KnowledgeGraphBuilder(self.db_path)
        stats = builder.build(self.temp_dir)
        
        # 验证统计信息
        self.assertGreater(stats['files'], 0)
        self.assertGreater(stats['classes'], 0)
        
        builder.close()

        # 验证数据库内容
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM files")
        self.assertGreater(cursor.fetchone()[0], 0)
        
        cursor.execute("SELECT COUNT(*) FROM classes")
        self.assertGreater(cursor.fetchone()[0], 0)
        
        conn.close()


# ============================================================================
# 主程序
# ============================================================================

if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    suite.addTests(loader.loadTestsFromTestCase(TestArkTSParser))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*70)
    print("测试总结")
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
