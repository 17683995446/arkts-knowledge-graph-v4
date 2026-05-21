#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试框架 - 发现系统bug并修复
包含：详细日志、复杂场景、边界测试、异常测试
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import time
import traceback
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/workspace/arkts-knowledge-graph-v4/test_debug.log', mode='w')
    ]
)
logger = logging.getLogger('comprehensive_test')

# 导入被测系统
sys.path.insert(0, '/workspace/arkts-knowledge-graph-v4')
from arkts_knowledge_graph import (
    DatabaseManager, ArkTSParser, KnowledgeGraphBuilder,
    FileInfo, ClassInfo, MethodInfo, CallRelation
)
from smart_filter import SmartFilter
from incremental_parser import IncrementalParser
from coverage_validator import CoverageValidator
from extended_extractors import (
    DecoratorExtractor, EntityTypeExtractor,
    ImportExtractor, StateRelationExtractor
)


class TestResult:
    """测试结果记录"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = {}
    
    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name} ({self.duration:.2f}s)"


class ComprehensiveTester:
    """全面测试器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.temp_dir = None
        self.test_project_path = None
        
    def setup(self):
        """测试前置准备"""
        logger.info("=" * 80)
        logger.info("开始全面测试")
        logger.info("=" * 80)
        
        # 创建临时测试目录
        self.temp_dir = tempfile.mkdtemp(prefix="arkts_test_")
        self.test_project_path = Path(self.temp_dir) / "test_project"
        self.test_project_path.mkdir()
        logger.info(f"创建临时测试目录: {self.test_project_path}")
        
    def teardown(self):
        """测试后置清理"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"清理临时目录: {self.temp_dir}")
    
    def run_all_tests(self):
        """运行所有测试"""
        self.setup()
        
        try:
            # 1. 基础功能测试
            self.test_basic_parsing()
            self.test_database_operations()
            self.test_smart_filter()
            
            # 2. 复杂场景测试
            self.test_complex_nesting()
            self.test_circular_dependencies()
            self.test_large_file_handling()
            self.test_special_characters()
            
            # 3. 边界测试
            self.test_empty_files()
            self.test_malformed_code()
            self.test_unicode_content()
            self.test_very_long_names()
            
            # 4. 异常测试
            self.test_missing_files()
            self.test_invalid_paths()
            self.test_database_corruption()
            
            # 5. 增量解析测试
            self.test_incremental_parsing()
            
            # 6. 性能测试
            self.test_performance_with_many_files()
            
            # 7. 覆盖率验证
            self.test_coverage_validation()
            
        finally:
            self.teardown()
            self.print_summary()
    
    def _create_test_file(self, relative_path: str, content: str):
        """创建测试文件"""
        file_path = self.test_project_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"创建测试文件: {file_path}")
        return file_path
    
    def test_basic_parsing(self):
        """测试基础解析功能"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 基础解析功能")
        logger.info("=" * 60)
        
        result = TestResult("基础解析功能")
        start = time.time()
        
        try:
            # 创建简单组件
            self._create_test_file("pages/Index.ets", '''
@Entry
@Component
struct Index {
  build() {
    Column() {
      Text("Hello")
    }
  }
}
''')
            
            # 解析
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            # 验证
            assert len(result_data['files']) == 1, f"期望1个文件，实际{len(result_data['files'])}"
            assert len(result_data['classes']) == 1, f"期望1个类，实际{len(result_data['classes'])}"
            assert result_data['classes'][0].name == 'Index', f"类名错误: {result_data['classes'][0].name}"
            
            result.passed = True
            result.details['files'] = len(result_data['files'])
            result.details['classes'] = len(result_data['classes'])
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_database_operations(self):
        """测试数据库操作"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 数据库操作")
        logger.info("=" * 60)
        
        result = TestResult("数据库操作")
        start = time.time()
        
        try:
            db_path = os.path.join(self.temp_dir, "test.db")
            db = DatabaseManager(db_path)
            db.connect()
            db.create_tables()
            
            # 测试插入
            db.insert_file(FileInfo(path="/test/file.ets"))
            db.insert_class(ClassInfo(name="TestClass", file="/test/file.ets"))
            
            # 测试查询
            stats = db.get_statistics()
            assert stats['files'] == 1, f"期望1个文件，实际{stats['files']}"
            assert stats['classes'] == 1, f"期望1个类，实际{stats['classes']}"
            
            db.close()
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_smart_filter(self):
        """测试智能过滤器"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 智能过滤器")
        logger.info("=" * 60)
        
        result = TestResult("智能过滤器")
        start = time.time()
        
        try:
            # 创建独立的测试目录
            filter_test_dir = self.test_project_path / "filter_test"
            filter_test_dir.mkdir(exist_ok=True)
            
            # 创建第三方库文件
            node_modules = filter_test_dir / "node_modules" / "some-lib"
            node_modules.mkdir(parents=True)
            (node_modules / "index.ts").write_text("export class Lib {}")
            
            # 创建业务文件
            src_dir = filter_test_dir / "src"
            src_dir.mkdir(exist_ok=True)
            (src_dir / "Main.ets").write_text("@Component struct Main {}")
            
            # 测试过滤
            filter_obj = SmartFilter(str(filter_test_dir))
            filtered = filter_obj.filter()
            
            # node_modules 应该被过滤掉，只保留 Main.ets
            assert len(filtered) == 1, f"期望1个文件，实际{len(filtered)}: {filtered}"
            assert "Main.ets" in filtered[0], f"应该保留Main.ets: {filtered}"
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_complex_nesting(self):
        """测试复杂嵌套场景"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 复杂嵌套场景")
        logger.info("=" * 60)
        
        result = TestResult("复杂嵌套场景")
        start = time.time()
        
        try:
            # 创建深度嵌套的组件
            self._create_test_file("pages/DeepNest.ets", '''
@Entry
@Component
struct DeepNest {
  @State private count: number = 0
  @Prop title: string
  
  @Builder
  buildHeader() {
    Row() {
      Text(this.title)
        .fontSize(20)
        .onClick(() => {
          this.count++
        })
    }
  }
  
  build() {
    Column() {
      this.buildHeader()
      ForEach([1,2,3], (item) => {
        Row() {
          Column() {
            Text(item.toString())
          }
        }
      })
    }
  }
}
''')
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            # 验证能正确解析复杂结构
            assert len(result_data['classes']) >= 1, "应该解析出类"
            
            result.passed = True
            result.details['classes'] = len(result_data['classes'])
            result.details['methods'] = len(result_data['methods'])
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_circular_dependencies(self):
        """测试循环依赖"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 循环依赖")
        logger.info("=" * 60)
        
        result = TestResult("循环依赖")
        start = time.time()
        
        try:
            # 创建独立的测试目录
            circular_test_dir = self.test_project_path / "circular_test"
            circular_test_dir.mkdir(exist_ok=True)
            
            # 创建循环依赖的文件
            (circular_test_dir / "A.ets").write_text('''
import { B } from './B'
@Component struct A { 
  build() { B() } 
}
''')
            (circular_test_dir / "B.ets").write_text('''
import { C } from './C'
@Component struct B { 
  build() { C() } 
}
''')
            (circular_test_dir / "C.ets").write_text('''
import { A } from './A'
@Component struct C { 
  build() { A() } 
}
''')
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(circular_test_dir))
            
            # 应该能处理循环依赖而不死循环
            assert len(result_data['files']) == 3, f"期望3个文件，实际{len(result_data['files'])}: {[f.path for f in result_data['files']]}"
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_large_file_handling(self):
        """测试大文件处理"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 大文件处理")
        logger.info("=" * 60)
        
        result = TestResult("大文件处理")
        start = time.time()
        
        try:
            # 创建大文件（1000行）
            lines = ['@Component struct Large {'] + [
                f'  method{i}() {{ return {i}; }}'
                for i in range(1000)
            ] + ['}']
            
            self._create_test_file("Large.ets", '\n'.join(lines))
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            # 验证能处理大文件
            assert len(result_data['classes']) >= 1, "应该解析出Large类"
            
            result.passed = True
            result.details['methods'] = len(result_data['methods'])
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_special_characters(self):
        """测试特殊字符"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 特殊字符")
        logger.info("=" * 60)
        
        result = TestResult("特殊字符")
        start = time.time()
        
        try:
            # 包含特殊字符的文件
            self._create_test_file("Special.ets", '''
@Component
struct Special {
  // 中文注释
  /* 多行
     注释 */
  method_with_中文() {}
  
  // 模板字符串
  template = `hello ${name}`
  
  // 正则表达式
  regex = /\\d+/g
  
  build() {
    Text("特殊字符: ©®™")
  }
}
''')
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_empty_files(self):
        """测试空文件"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 空文件")
        logger.info("=" * 60)
        
        result = TestResult("空文件")
        start = time.time()
        
        try:
            # 创建空文件
            self._create_test_file("Empty.ets", "")
            self._create_test_file("Whitespace.ets", "   \n\n   ")
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            # 应该能处理空文件而不崩溃
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_malformed_code(self):
        """测试畸形代码"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 畸形代码")
        logger.info("=" * 60)
        
        result = TestResult("畸形代码")
        start = time.time()
        
        try:
            # 创建语法错误的文件
            self._create_test_file("Malformed.ets", '''
@Component
struct Broken {
  build() {
    // 不完整的代码
    Text(
  }
  
  // 不匹配的括号
  method() {
    return (1 + 2
  }
}
''')
            
            parser = ArkTSParser()
            # 应该能处理而不崩溃
            result_data = parser.parse_project(str(self.test_project_path))
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_unicode_content(self):
        """测试Unicode内容"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: Unicode内容")
        logger.info("=" * 60)
        
        result = TestResult("Unicode内容")
        start = time.time()
        
        try:
            # 各种Unicode字符
            self._create_test_file("Unicode.ets", '''
@Component
struct Unicode {
  // Emoji
  emoji = "😀🎉🚀"
  
  // 中文变量名
  用户名 = "张三"
  
  // 阿拉伯文
  arabic = "مرحبا"
  
  // 日文
  japanese = "こんにちは"
  
  build() {
    Text("Unicode测试: 🌍🌎🌏")
  }
}
''')
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_very_long_names(self):
        """测试超长名称"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 超长名称")
        logger.info("=" * 60)
        
        result = TestResult("超长名称")
        start = time.time()
        
        try:
            # 超长类名和方法名
            long_name = "A" * 200
            self._create_test_file("LongNames.ets", f'''
@Component
struct {long_name} {{
  {long_name}Method() {{}}
  
  build() {{
    Text("test")
  }}
}}
''')
            
            parser = ArkTSParser()
            result_data = parser.parse_project(str(self.test_project_path))
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_missing_files(self):
        """测试缺失文件"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 缺失文件")
        logger.info("=" * 60)
        
        result = TestResult("缺失文件")
        start = time.time()
        
        try:
            # 引用不存在的文件
            self._create_test_file("MissingRef.ets", '''
import { NonExistent } from './NonExistent'
@Component struct Test {}
''')
            
            parser = ArkTSParser()
            # 应该能处理而不崩溃
            result_data = parser.parse_project(str(self.test_project_path))
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_invalid_paths(self):
        """测试无效路径"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 无效路径")
        logger.info("=" * 60)
        
        result = TestResult("无效路径")
        start = time.time()
        
        try:
            parser = ArkTSParser()
            
            # 测试不存在的路径
            try:
                result_data = parser.parse_project("/nonexistent/path")
                result.error = "应该抛出FileNotFoundError"
            except FileNotFoundError:
                result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_database_corruption(self):
        """测试数据库损坏处理"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 数据库损坏处理")
        logger.info("=" * 60)
        
        result = TestResult("数据库损坏处理")
        start = time.time()
        
        try:
            # 创建损坏的数据库文件
            db_path = os.path.join(self.temp_dir, "corrupt.db")
            with open(db_path, 'w') as f:
                f.write("This is not a valid SQLite database")
            
            # 尝试连接
            try:
                db = DatabaseManager(db_path)
                db.connect()
                result.error = "应该检测到损坏的数据库"
            except Exception:
                # 期望抛出异常
                result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_incremental_parsing(self):
        """测试增量解析"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 增量解析")
        logger.info("=" * 60)
        
        result = TestResult("增量解析")
        start = time.time()
        
        try:
            # 创建初始文件
            self._create_test_file("Stable.ets", "@Component struct Stable {}")
            self._create_test_file("Changing.ets", "@Component struct Changing { v1() {} }")
            
            # 首次全量构建
            db_path = os.path.join(self.temp_dir, "incremental.db")
            builder = KnowledgeGraphBuilder(db_path)
            builder.build(str(self.test_project_path))
            
            # 修改一个文件
            time.sleep(0.1)  # 确保时间戳变化
            self._create_test_file("Changing.ets", "@Component struct Changing { v2() {} }")
            
            # 增量构建
            builder2 = KnowledgeGraphBuilder(db_path)
            builder2.build(str(self.test_project_path), incremental=True)
            
            result.passed = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_performance_with_many_files(self):
        """测试大量文件性能"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 大量文件性能")
        logger.info("=" * 60)
        
        result = TestResult("大量文件性能")
        start = time.time()
        
        try:
            # 创建100个文件
            for i in range(100):
                self._create_test_file(f"components/Component{i}.ets", f'''
@Component
struct Component{i} {{
  build() {{
    Text("Component {i}")
  }}
}}
''')
            
            parser = ArkTSParser()
            parse_start = time.time()
            result_data = parser.parse_project(str(self.test_project_path))
            parse_time = time.time() - parse_start
            
            result.passed = True
            result.details['file_count'] = 100
            result.details['parse_time'] = f"{parse_time:.2f}s"
            result.details['classes_found'] = len(result_data['classes'])
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def test_coverage_validation(self):
        """测试覆盖率验证"""
        logger.info("\n" + "=" * 60)
        logger.info("测试: 覆盖率验证")
        logger.info("=" * 60)
        
        result = TestResult("覆盖率验证")
        start = time.time()
        
        try:
            # 创建测试项目
            self._create_test_file("Main.ets", '''
@Entry
@Component
struct Main {
  build() {
    Text("Main")
  }
}
''')
            
            # 构建并验证
            db_path = os.path.join(self.temp_dir, "coverage.db")
            builder = KnowledgeGraphBuilder(db_path)
            builder.build(str(self.test_project_path))
            
            validator = CoverageValidator(db_path)
            validator.connect()
            report = validator.validate_all(str(self.test_project_path))
            validator.close()
            
            # 检查覆盖率
            file_coverage = next((c for c in report['checks'] if c['name'] == 'file_coverage'), None)
            if file_coverage and file_coverage.get('coverage', 0) >= 95:
                result.passed = True
            else:
                result.error = f"覆盖率不足: {file_coverage}"
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"测试失败: {traceback.format_exc()}")
        
        result.duration = time.time() - start
        self.results.append(result)
        logger.info(f"结果: {result}")
    
    def print_summary(self):
        """打印测试摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("测试摘要")
        logger.info("=" * 80)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        logger.info(f"总计: {total} 个测试")
        logger.info(f"通过: {passed} 个")
        logger.info(f"失败: {failed} 个")
        logger.info(f"通过率: {passed/total*100:.1f}%")
        
        if failed > 0:
            logger.info("\n失败的测试:")
            for r in self.results:
                if not r.passed:
                    logger.info(f"  - {r.name}: {r.error}")
        
        logger.info("=" * 80)
        
        # 写入结果文件
        with open('/workspace/arkts-knowledge-graph-v4/test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_rate': passed/total*100 if total > 0 else 0
                },
                'results': [
                    {
                        'name': r.name,
                        'passed': r.passed,
                        'error': r.error,
                        'duration': r.duration,
                        'details': r.details
                    }
                    for r in self.results
                ]
            }, f, indent=2)


if __name__ == "__main__":
    tester = ComprehensiveTester()
    tester.run_all_tests()
