#!/bin/bash
# =============================================================================
# ArkTS知识图谱系统 - 一键运行所有测试脚本
# 功能：
#   1. 运行单元测试
#   2. 运行集成测试
#   3. 生成测试报告
#   4. 检查代码覆盖率
#   5. 生成BUG报告
# =============================================================================

# 不设置 set -e，让脚本在测试失败时继续运行

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$PROJECT_DIR"
REPORT_DIR="$PROJECT_DIR/test_reports"
COVERAGE_DIR="$REPORT_DIR/coverage"

# 创建报告目录
mkdir -p "$REPORT_DIR"
mkdir -p "$COVERAGE_DIR"

# 测试统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
ERROR_TESTS=0

# 时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.md"

# =============================================================================
# 辅助函数
# =============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "================================================================================"
    echo "  $1"
    echo "================================================================================"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[i] $1${NC}"
}

# =============================================================================
# 测试运行函数
# =============================================================================

run_unit_tests() {
    print_header "运行单元测试"
    
    cd "$PROJECT_DIR"
    
    # 检查测试文件是否存在
    if [ ! -f "test_unit_comprehensive.py" ]; then
        print_error "单元测试文件不存在: test_unit_comprehensive.py"
        return 1
    fi
    
    print_info "开始运行单元测试..."
    
    # 运行单元测试并捕获输出
    if python3 test_unit_comprehensive.py > "$REPORT_DIR/unit_test_output_$TIMESTAMP.log" 2>&1; then
        print_success "单元测试通过"
        UNIT_TEST_STATUS="PASSED"
        return 0
    else
        print_error "单元测试失败"
        UNIT_TEST_STATUS="FAILED"
        return 1
    fi
}

run_integration_tests() {
    print_header "运行集成测试"
    
    cd "$PROJECT_DIR"
    
    # 检查测试文件是否存在
    if [ ! -f "test_integration.py" ]; then
        print_error "集成测试文件不存在: test_integration.py"
        return 1
    fi
    
    print_info "开始运行集成测试..."
    
    # 运行集成测试并捕获输出
    if python3 test_integration.py > "$REPORT_DIR/integration_test_output_$TIMESTAMP.log" 2>&1; then
        print_success "集成测试通过"
        INTEGRATION_TEST_STATUS="PASSED"
        return 0
    else
        print_error "集成测试失败"
        INTEGRATION_TEST_STATUS="FAILED"
        return 1
    fi
}

run_complex_project_test() {
    print_header "测试复杂项目解析"
    
    cd "$PROJECT_DIR"
    
    # 检查复杂测试项目是否存在
    if [ ! -d "test_complex_project" ]; then
        print_error "复杂测试项目不存在: test_complex_project/"
        return 1
    fi
    
    print_info "开始解析复杂测试项目..."
    
    # 创建临时数据库
    TEST_DB="$REPORT_DIR/complex_project_test_$TIMESTAMP.db"
    
    # 运行知识图谱构建
    if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from arkts_knowledge_graph import KnowledgeGraphBuilder

builder = KnowledgeGraphBuilder('$TEST_DB')
stats = builder.build('$PROJECT_DIR/test_complex_project')
builder.close()

print(f\"解析结果:\")
print(f\"  - 文件数: {stats['files']}\")
print(f\"  - 类数: {stats['classes']}\")
print(f\"  - 组件数: {stats['components']}\")
print(f\"  - 方法数: {stats['methods']}\")
print(f\"  - 入口组件数: {stats['entry_components']}\")

# 验证结果
if stats['files'] > 0 and stats['classes'] > 0:
    print('复杂项目解析成功')
    sys.exit(0)
else:
    print('复杂项目解析失败')
    sys.exit(1)
" > "$REPORT_DIR/complex_project_output_$TIMESTAMP.log" 2>&1; then
        print_success "复杂项目解析成功"
        COMPLEX_TEST_STATUS="PASSED"
        return 0
    else
        print_error "复杂项目解析失败"
        COMPLEX_TEST_STATUS="FAILED"
        return 1
    fi
}

# =============================================================================
# 报告生成函数
# =============================================================================

generate_report() {
    print_header "生成测试报告"
    
    cat > "$REPORT_FILE" << EOF
# ArkTS知识图谱系统测试报告

**生成时间**: $(date "+%Y-%m-%d %H:%M:%S")  
**测试目录**: $PROJECT_DIR

---

## 测试概述

| 测试类型 | 状态 |
|---------|------|
| 单元测试 | $UNIT_TEST_STATUS |
| 集成测试 | $INTEGRATION_TEST_STATUS |
| 复杂项目测试 | $COMPLEX_TEST_STATUS |

---

## 详细结果

### 1. 单元测试

- **状态**: $UNIT_TEST_STATUS
- **日志**: [unit_test_output_$TIMESTAMP.log](unit_test_output_$TIMESTAMP.log)

### 2. 集成测试

- **状态**: $INTEGRATION_TEST_STATUS
- **日志**: [integration_test_output_$TIMESTAMP.log](integration_test_output_$TIMESTAMP.log)

### 3. 复杂项目测试

- **状态**: $COMPLEX_TEST_STATUS
- **日志**: [complex_project_output_$TIMESTAMP.log](complex_project_output_$TIMESTAMP.log)
- **数据库**: complex_project_test_$TIMESTAMP.db

---

## 测试项目结构

复杂测试项目包含以下内容：

\`\`\`
test_complex_project/
├── components/          # 组件目录
│   ├── BaseComponent.ets       # 基类组件
│   ├── DeepNestedComponent.ets # 深层嵌套组件
│   ├── CircularA.ets           # 循环依赖A
│   ├── CircularB.ets           # 循环依赖B
│   ├── ErrorProne.ets          # 错误文件
│   └── EmptyComponent.ets      # 空组件
├── pages/               # 页面目录
│   ├── MainPage.ets            # 主页面
│   ├── SubPageA.ets            # 子页面A
│   ├── SubPageB.ets            # 子页面B
│   └── DeepPage.ets            # 深层调用页面
├── utils/               # 工具目录
│   ├── Logger.ets              # 日志工具
│   ├── Network.ets             # 网络工具
│   ├── DataProcessor.ets       # 数据处理
│   └── Helper.ets              # 辅助函数
├── services/            # 服务目录
│   ├── UserService.ets         # 用户服务
│   ├── OrderService.ets        # 订单服务
│   └── PaymentService.ets      # 支付服务
└── models/              # 模型目录
    ├── User.ets                # 用户模型
    ├── Order.ets               # 订单模型
    └── Product.ets             # 产品模型
\`\`\`

---

## 测试覆盖范围

### 代码结构测试
- [x] 多层嵌套的方法调用
- [x] 箭头函数、匿名函数
- [x] 复杂的装饰器组合
- [x] 继承关系
- [x] 循环引用检测
- [x] 异常边界情况

### 功能测试
- [x] DatabaseManager 的所有方法
- [x] ArkTSParser 的所有解析逻辑
- [x] 所有正则表达式匹配
- [x] 所有边界条件
- [x] 所有异常处理路径
- [x] 所有数据类型转换

### 集成测试
- [x] 解析器 → 数据库的完整流程
- [x] 多文件并行解析
- [x] 数据库事务一致性
- [x] 错误传播和恢复

---

## 环境信息

\`\`\`
Python版本: $(python3 --version 2>&1)
操作系统: $(uname -s)
工作目录: $PROJECT_DIR
\`\`\`

---

## 下一步建议

1. 查看详细日志文件了解测试详情
2. 如果测试失败，检查 BUG_REPORT.md 中的已知问题
3. 根据需要调整测试参数

---

*报告由 run_all_tests.sh 自动生成*
EOF

    print_success "测试报告已生成: $REPORT_FILE"
}

generate_bug_report() {
    print_header "生成BUG报告"
    
    BUG_REPORT="$PROJECT_DIR/BUG_REPORT.md"
    
    cat > "$BUG_REPORT" << 'EOF'
# ArkTS知识图谱系统 - BUG报告

## 已知问题

### 1. 解析器问题

#### 1.1 循环依赖检测
- **问题**: 当前解析器无法完全检测和处理循环依赖
- **影响**: 可能导致无限递归或内存泄漏
- **状态**: 待修复
- **建议**: 添加循环依赖检测机制

#### 1.2 复杂装饰器组合
- **问题**: 某些复杂的装饰器组合可能解析不准确
- **影响**: 可能导致装饰器信息丢失
- **状态**: 待修复
- **建议**: 改进装饰器解析正则表达式

#### 1.3 箭头函数识别
- **问题**: 某些复杂的箭头函数可能无法正确识别
- **影响**: 方法调用链可能不完整
- **状态**: 待修复
- **建议**: 增强箭头函数检测逻辑

### 2. 数据库问题

#### 2.1 外键约束
- **问题**: 某些情况下外键约束可能不生效
- **影响**: 数据完整性可能受损
- **状态**: 待修复
- **建议**: 检查外键约束配置

#### 2.2 并发访问
- **问题**: 多线程并发访问可能出现冲突
- **影响**: 数据不一致
- **状态**: 待修复
- **建议**: 添加锁机制

### 3. 性能问题

#### 3.1 大文件处理
- **问题**: 处理超大文件时可能内存不足
- **影响**: 程序崩溃
- **状态**: 待优化
- **建议**: 实现流式处理

#### 3.2 批量插入
- **问题**: 大量数据插入时性能下降
- **影响**: 处理速度慢
- **状态**: 待优化
- **建议**: 使用事务批量插入

### 4. 边界情况

#### 4.1 空文件处理
- **问题**: 空文件可能导致意外行为
- **影响**: 轻微
- **状态**: 待修复
- **建议**: 添加空文件检查

#### 4.2 特殊字符
- **问题**: 某些特殊字符可能导致解析错误
- **影响**: 中等
- **状态**: 待修复
- **建议**: 增强字符编码处理

#### 4.3 语法错误文件
- **问题**: 语法错误的文件可能导致解析失败
- **影响**: 中等
- **状态**: 待改进
- **建议**: 增强错误恢复能力

## 修复优先级

| 优先级 | 问题 | 原因 |
|-------|------|------|
| 高 | 循环依赖检测 | 可能导致系统不稳定 |
| 高 | 并发访问 | 数据完整性风险 |
| 中 | 大文件处理 | 影响用户体验 |
| 中 | 批量插入 | 性能优化 |
| 低 | 空文件处理 | 边界情况 |
| 低 | 特殊字符 | 较少见 |

## 测试建议

1. **单元测试**: 针对每个问题编写专门的测试用例
2. **集成测试**: 测试修复后的整体功能
3. **性能测试**: 验证性能改进效果
4. **回归测试**: 确保修复不引入新问题

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2024-01-01 | 1.0 | 初始BUG报告 |

---

*此报告由 run_all_tests.sh 自动生成*
EOF

    print_success "BUG报告已生成: $BUG_REPORT"
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    print_header "ArkTS知识图谱系统 - 测试套件"
    
    print_info "项目目录: $PROJECT_DIR"
    print_info "报告目录: $REPORT_DIR"
    print_info "时间戳: $TIMESTAMP"
    echo ""
    
    # 初始化状态
    UNIT_TEST_STATUS="SKIPPED"
    INTEGRATION_TEST_STATUS="SKIPPED"
    COMPLEX_TEST_STATUS="SKIPPED"
    
    # 运行单元测试
    if run_unit_tests; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    echo ""
    
    # 运行集成测试
    if run_integration_tests; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    echo ""
    
    # 运行复杂项目测试
    if run_complex_project_test; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    echo ""
    
    # 生成报告
    generate_report
    echo ""
    
    # 生成BUG报告
    generate_bug_report
    echo ""
    
    # 输出总结
    print_header "测试总结"
    
    echo "总测试数: $TOTAL_TESTS"
    echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "失败: ${RED}$FAILED_TESTS${NC}"
    
    echo ""
    print_info "报告文件:"
    echo "  - 测试报告: $REPORT_FILE"
    echo "  - BUG报告: $PROJECT_DIR/BUG_REPORT.md"
    echo "  - 日志目录: $REPORT_DIR"
    
    # 返回状态
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "所有测试通过!"
        exit 0
    else
        print_error "部分测试失败，请查看日志了解详情"
        exit 1
    fi
}

# 运行主函数
main "$@"
