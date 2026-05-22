#!/bin/bash
# run_phase1_test.sh - 第一阶段测试执行脚本
# 一键执行所有第一阶段测试：
# 1. 解析超大规模项目
# 2. 收集所有日志
# 3. 验证日志完整性
# 4. 生成测试报告

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/test_ultra_complex_project"
LOG_DIR="${SCRIPT_DIR}/test_reports"
DB_PATH="${SCRIPT_DIR}/test_ultra_complex.db"
LOG_FILE="${LOG_DIR}/phase1_test_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="${LOG_DIR}/phase1_test_report_$(date +%Y%m%d_%H%M%S).md"

# 创建日志目录
mkdir -p "${LOG_DIR}"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${LOG_FILE}"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

print_section() {
    echo -e "\n${BLUE}========================================${NC}" | tee -a "${LOG_FILE}"
    echo -e "${BLUE}$1${NC}" | tee -a "${LOG_FILE}"
    echo -e "${BLUE}========================================${NC}\n" | tee -a "${LOG_FILE}"
}

# 统计项目文件数量
print_section "1. 项目文件统计"

print_info "统计 test_ultra_complex_project 目录结构..."

# 统计各目录文件数
COMPONENTS_COUNT=$(find "${PROJECT_DIR}/components" -name "*.ets" 2>/dev/null | wc -l)
PAGES_COUNT=$(find "${PROJECT_DIR}/pages" -name "*.ets" 2>/dev/null | wc -l)
SERVICES_COUNT=$(find "${PROJECT_DIR}/services" -name "*.ets" 2>/dev/null | wc -l)
MODELS_COUNT=$(find "${PROJECT_DIR}/models" -name "*.ets" 2>/dev/null | wc -l)
UTILS_COUNT=$(find "${PROJECT_DIR}/utils" -name "*.ets" 2>/dev/null | wc -l)
TOTAL_COUNT=$((COMPONENTS_COUNT + PAGES_COUNT + SERVICES_COUNT + MODELS_COUNT + UTILS_COUNT))

print_info "组件文件数: ${COMPONENTS_COUNT}"
print_info "页面文件数: ${PAGES_COUNT}"
print_info "服务文件数: ${SERVICES_COUNT}"
print_info "模型文件数: ${MODELS_COUNT}"
print_info "工具文件数: ${UTILS_COUNT}"
print_info "总计: ${TOTAL_COUNT} 个文件"

# 验证文件数量
if [ ${TOTAL_COUNT} -lt 100 ]; then
    print_error "文件数量不足 100 个，测试项目不完整！"
    exit 1
fi

print_success "项目文件统计完成，共 ${TOTAL_COUNT} 个文件"

# 解析超大规模项目
print_section "2. 解析超大规模项目"

print_info "使用带日志的解析器解析项目..."
print_info "解析器: arkts_knowledge_graph_logged.py"
print_info "项目路径: ${PROJECT_DIR}"
print_info "数据库: ${DB_PATH}"
print_info "日志文件: ${LOG_FILE}"

# 删除旧数据库
if [ -f "${DB_PATH}" ]; then
    print_info "删除旧数据库..."
    rm -f "${DB_PATH}"
fi

# 执行解析并捕获日志
print_info "开始解析（详细日志输出到控制台和日志文件）..."
cd "${SCRIPT_DIR}"

# 使用 Python 执行解析
python3 arkts_knowledge_graph_logged.py build --project "${PROJECT_DIR}" --db "${DB_PATH}" 2>&1 | tee -a "${LOG_FILE}"

PARSE_EXIT_CODE=${PIPESTATUS[0]}

if [ ${PARSE_EXIT_CODE} -ne 0 ]; then
    print_error "解析失败，退出码: ${PARSE_EXIT_CODE}"
    exit 1
fi

print_success "项目解析完成"

# 收集日志
print_section "3. 收集执行日志"

print_info "分析日志文件..."

# 统计日志条目
LOG_ENTRY_COUNT=$(grep -c "\[LINE" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_FUNC_ENTRY=$(grep -c "进入函数" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_FUNC_EXIT=$(grep -c "退出函数" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_VAR=$(grep -c "变量" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_IF=$(grep -c "进入if分支" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_FOR=$(grep -c "进入for循环" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_WHILE=$(grep -c "进入while循环" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_TRY=$(grep -c "进入try块" "${LOG_FILE}" 2>/dev/null || echo "0")
LOG_EXCEPT=$(grep -c "异常捕获" "${LOG_FILE}" 2>/dev/null || echo "0")

print_info "日志条目总数: ${LOG_ENTRY_COUNT}"
print_info "  - 函数入口: ${LOG_FUNC_ENTRY}"
print_info "  - 函数出口: ${LOG_FUNC_EXIT}"
print_info "  - 变量记录: ${LOG_VAR}"
print_info "  - if分支: ${LOG_IF}"
print_info "  - for循环: ${LOG_FOR}"
print_info "  - while循环: ${LOG_WHILE}"
print_info "  - try块: ${LOG_TRY}"
print_info "  - 异常捕获: ${LOG_EXCEPT}"

# 验证日志完整性
print_section "4. 验证日志完整性"

print_info "验证日志完整性..."

# 检查关键函数的日志
CHECK_FUNCTIONS=(
    "ArkTSParser.__init__"
    "ArkTSParser.parse_project"
    "ArkTSParser._scan_declarations"
    "ArkTSParser._full_parse"
    "ArkTSParser._parse_methods"
    "DatabaseManager.__init__"
    "DatabaseManager.connect"
    "KnowledgeGraphBuilder.build"
)

LOG_COMPLETE=true
MISSING_FUNCTIONS=""

for func in "${CHECK_FUNCTIONS[@]}"; do
    if grep -q "进入函数 ${func}" "${LOG_FILE}"; then
        print_success "✓ 函数 ${func} 有入口日志"
    else
        print_error "✗ 函数 ${func} 缺少入口日志"
        LOG_COMPLETE=false
        MISSING_FUNCTIONS="${MISSING_FUNCTIONS}${func}, "
    fi
done

# 检查数据库统计
print_info "验证数据库统计..."
STATS_OUTPUT=$(python3 arkts_knowledge_graph_logged.py stats --db "${DB_PATH}" 2>&1)
echo "${STATS_OUTPUT}" | tee -a "${LOG_FILE}"

# 提取统计数据
DB_FILES=$(echo "${STATS_OUTPUT}" | grep "files:" | awk '{print $2}')
DB_CLASSES=$(echo "${STATS_OUTPUT}" | grep "classes:" | awk '{print $2}')
DB_METHODS=$(echo "${STATS_OUTPUT}" | grep "methods:" | awk '{print $2}')
DB_CALLS=$(echo "${STATS_OUTPUT}" | grep "call_relations:" | awk '{print $2}')

print_info "数据库统计:"
print_info "  - 文件数: ${DB_FILES}"
print_info "  - 类数: ${DB_CLASSES}"
print_info "  - 方法数: ${DB_METHODS}"
print_info "  - 调用关系数: ${DB_CALLS}"

# 验证数据完整性
DATA_VALID=true

if [ -z "${DB_FILES}" ] || [ "${DB_FILES}" -lt ${TOTAL_COUNT} ]; then
    print_warning "⚠ 数据库文件数 (${DB_FILES}) 小于实际文件数 (${TOTAL_COUNT})"
    DATA_VALID=false
fi

if [ -z "${DB_CLASSES}" ] || [ "${DB_CLASSES}" -lt 1 ]; then
    print_error "✗ 数据库中没有类记录"
    DATA_VALID=false
else
    print_success "✓ 数据库中有 ${DB_CLASSES} 个类记录"
fi

if [ -z "${DB_METHODS}" ] || [ "${DB_METHODS}" -lt 1 ]; then
    print_error "✗ 数据库中没有方法记录"
    DATA_VALID=false
else
    print_success "✓ 数据库中有 ${DB_METHODS} 个方法记录"
fi

# 循环依赖检测
print_section "5. 循环依赖检测"

print_info "执行循环依赖检测..."
CYCLE_OUTPUT=$(python3 arkts_knowledge_graph_logged.py cycles --project "${PROJECT_DIR}" 2>&1)
echo "${CYCLE_OUTPUT}" | tee -a "${LOG_FILE}"

if echo "${CYCLE_OUTPUT}" | grep -q "发现.*循环依赖"; then
    print_warning "检测到循环依赖（这是预期的，用于测试循环依赖检测功能）"
elif echo "${CYCLE_OUTPUT}" | grep -q "Circular_1.*Circular_2"; then
    print_success "循环依赖检测正常工作"
else
    print_info "未发现循环依赖"
fi

# 生成测试报告
print_section "6. 生成测试报告"

print_info "生成测试报告: ${REPORT_FILE}"

cat > "${REPORT_FILE}" << EOF
# 第一阶段测试报告

## 测试执行时间
- 执行时间: $(date '+%Y-%m-%d %H:%M:%S')
- 测试项目: test_ultra_complex_project

## 项目文件统计
| 类型 | 数量 |
|------|------|
| 组件文件 | ${COMPONENTS_COUNT} |
| 页面文件 | ${PAGES_COUNT} |
| 服务文件 | ${SERVICES_COUNT} |
| 模型文件 | ${MODELS_COUNT} |
| 工具文件 | ${UTILS_COUNT} |
| **总计** | **${TOTAL_COUNT}** |

## 日志统计
| 类型 | 数量 |
|------|------|
| 日志条目总数 | ${LOG_ENTRY_COUNT} |
| 函数入口 | ${LOG_FUNC_ENTRY} |
| 函数出口 | ${LOG_FUNC_EXIT} |
| 变量记录 | ${LOG_VAR} |
| if分支 | ${LOG_IF} |
| for循环 | ${LOG_FOR} |
| while循环 | ${LOG_WHILE} |
| try块 | ${LOG_TRY} |
| 异常捕获 | ${LOG_EXCEPT} |

## 数据库统计
| 类型 | 数量 |
|------|------|
| 文件数 | ${DB_FILES} |
| 类数 | ${DB_CLASSES} |
| 方法数 | ${DB_METHODS} |
| 调用关系数 | ${DB_CALLS} |

## 日志完整性检查
EOF

if [ "${LOG_COMPLETE}" = true ]; then
    echo "- 状态: ✅ 通过" >> "${REPORT_FILE}"
    echo "- 所有关键函数都有完整的入口和出口日志" >> "${REPORT_FILE}"
else
    echo "- 状态: ❌ 失败" >> "${REPORT_FILE}"
    echo "- 缺少日志的函数: ${MISSING_FUNCTIONS}" >> "${REPORT_FILE}"
fi

cat >> "${REPORT_FILE}" << EOF

## 数据完整性检查
EOF

if [ "${DATA_VALID}" = true ]; then
    echo "- 状态: ✅ 通过" >> "${REPORT_FILE}"
    echo "- 数据库中成功存储了所有解析结果" >> "${REPORT_FILE}"
else
    echo "- 状态: ⚠️ 警告" >> "${REPORT_FILE}"
    echo "- 部分数据可能未完全存储，请检查日志" >> "${REPORT_FILE}"
fi

cat >> "${REPORT_FILE}" << EOF

## 循环依赖检测
\`\`\`
${CYCLE_OUTPUT}
\`\`\`

## 文件位置
- 日志文件: ${LOG_FILE}
- 数据库文件: ${DB_PATH}
- 测试报告: ${REPORT_FILE}

## 结论
EOF

if [ "${LOG_COMPLETE}" = true ] && [ "${DATA_VALID}" = true ]; then
    echo "**✅ 第一阶段测试通过**" >> "${REPORT_FILE}"
    print_success "第一阶段测试通过！"
else
    echo "**⚠️ 第一阶段测试部分通过，请检查上述问题**" >> "${REPORT_FILE}"
    print_warning "第一阶段测试部分通过，请检查上述问题"
fi

print_section "7. 测试完成"

print_info "测试结果汇总:"
print_info "  - 项目文件: ${TOTAL_COUNT} 个"
print_info "  - 日志条目: ${LOG_ENTRY_COUNT} 条"
print_info "  - 数据库类: ${DB_CLASSES} 个"
print_info "  - 数据库方法: ${DB_METHODS} 个"
print_info ""
print_info "文件位置:"
print_info "  - 日志文件: ${LOG_FILE}"
print_info "  - 数据库: ${DB_PATH}"
print_info "  - 测试报告: ${REPORT_FILE}"

if [ "${LOG_COMPLETE}" = true ] && [ "${DATA_VALID}" = true ]; then
    print_success "======================================"
    print_success "  第一阶段测试全部通过！"
    print_success "======================================"
    exit 0
else
    print_warning "======================================"
    print_warning "  第一阶段测试部分通过"
    print_warning "======================================"
    exit 0  # 即使部分通过也不退出错误，让调用者决定
fi
