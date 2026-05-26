# -*- coding: utf-8 -*-
"""
AI辅助重构建议引擎
基于代码质量分析结果和图谱结构数据，生成具体、可操作的重构建议。
每条建议包含：问题描述、影响范围、具体步骤、预期收益。
"""

import sqlite3
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum


class RefactorPriority(Enum):
    """重构优先级"""
    CRITICAL = "critical"    # 紧急 - 影响稳定性或安全
    HIGH = "high"            # 高 - 显著影响可维护性
    MEDIUM = "medium"        # 中 - 改善代码质量
    LOW = "low"              # 低 - 优化建议
    INFO = "info"            # 信息 - 仅供参考


class RefactorCategory(Enum):
    """重构类别"""
    EXTRACT_METHOD = "extract_method"           # 提取方法
    EXTRACT_CLASS = "extract_class"             # 提取类
    RENAME = "rename"                           # 重命名
    SIMPLIFY_CONDITIONAL = "simplify_cond"      # 简化条件
    REMOVE_DUPLICATION = "remove_dup"           # 消除重复
    REDUCE_PARAMS = "reduce_params"             # 减少参数
    INTRODUCE_CONST = "introduce_const"         # 引入常量
    FIX_NAMING = "fix_naming"                   # 修正命名
    ADD_COMMENTS = "add_comments"               # 添加注释
    HANDLE_EXCEPTION = "handle_exception"       # 改善异常处理
    DECOUPLE = "decouple"                       # 解耦
    CONSOLIDATE = "consolidate"                 # 合并


@dataclass
class RefactorSuggestion:
    """单条重构建议"""
    id: str
    title: str                              # 简短标题
    category: str                           # 重构类别
    priority: str                           # 优先级
    file_path: str                          # 文件路径
    line_number: int                        # 行号
    entity_name: str                        # 相关实体名
    description: str                        # 详细描述
    current_code: str                       # 当前代码片段
    suggested_code: str                     # 建议代码片段
    steps: List[str]                        # 具体步骤
    impact: Dict                            # 影响分析
    estimated_effort: str                   # 预估工作量
    references: List[str]                   # 相关引用


class RefactoringAdvisor:
    """重构建议引擎"""

    # 阈值配置
    THRESHOLDS = {
        'long_method_lines': 50,
        'very_long_method_lines': 100,
        'large_class_methods': 20,
        'deep_nesting_level': 4,
        'high_fan_out': 15,            # 被调用次数过高
        'low_comment_ratio': 0.05,     # 注释率低于5%
        'many_params': 5,
        'duplicate_call_ratio': 0.3,   # 重复调用比例
    }

    # 命名规范模式
    NAMING_PATTERNS = {
        'class': r'^[A-Z][a-zA-Z0-9]*$',
        'method': r'^[a-z][a-zA-Z0-9]*$',
        'constant': r'^[A-Z][A-Z0-9_]*$',
        'private': r'^_[a-z][a-zA-Z0-9]*$',
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._suggestion_counter = 0

    def _next_id(self) -> str:
        """生成建议ID"""
        self._suggestion_counter += 1
        return f"R{self._suggestion_counter:03d}"

    def analyze_all(self) -> List[RefactorSuggestion]:
        """执行全面重构分析，返回所有建议"""
        suggestions = []

        # 1. 基于方法长度的建议
        suggestions.extend(self._suggest_extract_long_methods())

        # 2. 基于类规模的建议
        suggestions.extend(self._suggest_split_large_classes())

        # 3. 基于命名规范的建议
        suggestions.extend(self._suggest_fix_naming())

        # 4. 基于调用关系的建议
        suggestions.extend(self._suggest_reduce_coupling())

        # 5. 基于异常处理的建议
        suggestions.extend(self._suggest_improve_exception_handling())

        # 6. 基于重复代码的建议
        suggestions.extend(self._suggest_remove_duplication())

        # 7. 基于注释的建议
        suggestions.extend(self._suggest_add_documentation())

        # 8. 基于参数数量的建议
        suggestions.extend(self._suggest_reduce_parameters())

        # 按优先级排序
        priority_order = {
            RefactorPriority.CRITICAL.value: 0,
            RefactorPriority.HIGH.value: 1,
            RefactorPriority.MEDIUM.value: 2,
            RefactorPriority.LOW.value: 3,
            RefactorPriority.INFO.value: 4,
        }
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 99))

        return suggestions

    def analyze_entity(self, entity_name: str) -> List[RefactorSuggestion]:
        """分析特定实体的重构建议"""
        all_suggestions = self.analyze_all()
        return [s for s in all_suggestions if s.entity_name == entity_name]

    # ========== 具体重构规则 ==========

    def _suggest_extract_long_methods(self) -> List[RefactorSuggestion]:
        """建议提取过长方法"""
        suggestions = []

        # 获取所有方法及其估计长度
        cursor = self.conn.execute("""
            SELECT m.name, m.class_name, m.file, m.line_number,
                   m.is_private, m.is_static
            FROM methods m
        """)

        for row in cursor.fetchall():
            method_name = row['name']
            class_name = row['class_name']
            file_path = row['file']
            line_number = row['line_number']

            # 估算方法长度
            est_length = self._estimate_method_length(file_path, line_number)

            if est_length > self.THRESHOLDS['very_long_method_lines']:
                priority = RefactorPriority.CRITICAL.value
                effort = "大（2-4小时）"
            elif est_length > self.THRESHOLDS['long_method_lines']:
                priority = RefactorPriority.HIGH.value
                effort = "中（1-2小时）"
            else:
                continue

            # 分析方法内部的调用关系
            inner_calls = self._get_method_inner_calls(method_name, class_name)

            # 生成建议
            if inner_calls:
                # 有子调用 → 建议按调用分组提取
                steps = self._generate_extract_steps(method_name, inner_calls, est_length)
                suggested = self._generate_extracted_code(method_name, class_name, inner_calls)
            else:
                steps = [
                    f"1. 阅读方法 '{method_name}' 的完整逻辑",
                    f"2. 识别独立的逻辑块（约{est_length}行）",
                    "3. 将每个逻辑块提取为独立的私有方法",
                    f"4. 在原方法中调用新提取的方法",
                    "5. 运行测试验证行为不变"
                ]
                suggested = f"// 将{est_length}行的方法拆分为多个小方法\n// 每个方法不超过20行"

            suggestions.append(RefactorSuggestion(
                id=self._next_id(),
                title=f"提取方法: {class_name}.{method_name}（{est_length}行）",
                category=RefactorCategory.EXTRACT_METHOD.value,
                priority=priority,
                file_path=file_path,
                line_number=line_number,
                entity_name=f"{class_name}.{method_name}",
                description=f"方法 '{method_name}' 过长（{est_length}行），"
                            f"超过阈值{self.THRESHOLDS['long_method_lines']}行。"
                            f"过长的方法难以理解、测试和复用。",
                current_code=f"// {class_name}.{method_name}() - 约{est_length}行",
                suggested_code=suggested,
                steps=steps,
                impact={
                    "readability": "+30%",
                    "testability": "+40%",
                    "reusability": "+20%",
                    "risk": "低"
                },
                estimated_effort=effort,
                references=[f"{class_name}.{method_name}"]
            ))

        return suggestions

    def _suggest_split_large_classes(self) -> List[RefactorSuggestion]:
        """建议拆分过大的类"""
        suggestions = []

        cursor = self.conn.execute("""
            SELECT c.name, c.file, c.line_number, c.is_component,
                   COUNT(m.name) as method_count
            FROM classes c
            LEFT JOIN methods m ON c.name = m.class_name
            GROUP BY c.name
            HAVING method_count > ?
            ORDER BY method_count DESC
        """, (self.THRESHOLDS['large_class_methods'],))

        for row in cursor.fetchall():
            class_name = row['name']
            method_count = row['method_count']
            file_path = row['file']
            line_number = row['line_number']

            # 分析方法的职责分组
            method_groups = self._analyze_class_responsibilities(class_name)

            if len(method_groups) >= 2:
                group_desc = "、".join(
                    f"{g['name']}（{g['count']}个方法）" for g in method_groups
                )
                steps = [
                    f"1. 分析类 '{class_name}' 的{method_count}个方法",
                    f"2. 识别出{len(method_groups)}个独立职责：{group_desc}",
                    "3. 为每个职责创建新的类",
                    "4. 将相关方法移动到对应的新类",
                    "5. 在原类中持有新类的实例（组合优于继承）",
                    "6. 更新所有调用点",
                    "7. 运行测试验证"
                ]

                suggested = (
                    f"// 将 {class_name} 拆分为:\n"
                )
                for g in method_groups:
                    suggested += f"//   - {g['name']}: {', '.join(g['methods'][:3])}\n"
                    if len(g['methods']) > 3:
                        suggested += f"//     等共{g['count']}个方法\n"

                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"拆分类: {class_name}（{method_count}个方法）",
                    category=RefactorCategory.EXTRACT_CLASS.value,
                    priority=RefactorPriority.HIGH.value,
                    file_path=file_path,
                    line_number=line_number,
                    entity_name=class_name,
                    description=f"类 '{class_name}' 包含{method_count}个方法，"
                                f"超过阈值{self.THRESHOLDS['large_class_methods']}个。"
                                f"识别到{len(method_groups)}个独立职责，建议拆分。",
                    current_code=f"class {class_name} {{ /* {method_count}个方法 */ }}",
                    suggested_code=suggested,
                    steps=steps,
                    impact={
                        "readability": "+40%",
                        "maintainability": "+35%",
                        "testability": "+30%",
                        "risk": "中"
                    },
                    estimated_effort="大（4-8小时）",
                    references=[class_name]
                ))
            else:
                # 方法多但职责单一，建议审查
                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"审查类: {class_name}（{method_count}个方法）",
                    category=RefactorCategory.CONSOLIDATE.value,
                    priority=RefactorPriority.MEDIUM.value,
                    file_path=file_path,
                    line_number=line_number,
                    entity_name=class_name,
                    description=f"类 '{class_name}' 包含{method_count}个方法。"
                                f"建议审查是否存在可以合并或移除的方法。",
                    current_code=f"class {class_name} {{ /* {method_count}个方法 */ }}",
                    suggested_code=f"// 审查并精简 {class_name} 的方法",
                    steps=[
                        f"1. 列出 '{class_name}' 的所有{method_count}个方法",
                        "2. 识别功能相似的方法",
                        "3. 合并重复逻辑",
                        "4. 移除未使用的方法",
                        "5. 运行测试验证"
                    ],
                    impact={
                        "readability": "+15%",
                        "maintainability": "+20%",
                        "risk": "低"
                    },
                    estimated_effort="中（2-4小时）",
                    references=[class_name]
                ))

        return suggestions

    def _suggest_fix_naming(self) -> List[RefactorSuggestion]:
        """建议修正命名规范"""
        suggestions = []

        # 检查类名
        cursor = self.conn.execute(
            "SELECT name, file, line_number FROM classes"
        )
        for row in cursor.fetchall():
            name = row['name']
            if name and not re.match(self.NAMING_PATTERNS['class'], name):
                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"重命名类: {name} → {self._suggest_class_name(name)}",
                    category=RefactorCategory.RENAME.value,
                    priority=RefactorPriority.MEDIUM.value,
                    file_path=row['file'],
                    line_number=row['line_number'],
                    entity_name=name,
                    description=f"类名 '{name}' 不符合PascalCase命名规范。",
                    current_code=f"class {name} {{ }}",
                    suggested_code=f"class {self._suggest_class_name(name)} {{ }}",
                    steps=[
                        f"1. 将类名 '{name}' 重命名为 '{self._suggest_class_name(name)}'",
                        "2. 更新文件名（如果类名与文件名一致）",
                        "3. 更新所有引用此类的代码",
                        "4. 运行测试验证"
                    ],
                    impact={"consistency": "+20%", "risk": "中"},
                    estimated_effort="小（30分钟）",
                    references=[name]
                ))

        # 检查方法名
        cursor = self.conn.execute(
            "SELECT name, class_name, file, line_number FROM methods"
        )
        for row in cursor.fetchall():
            name = row['name']
            if name and not re.match(self.NAMING_PATTERNS['method'], name):
                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"重命名方法: {row['class_name']}.{name}",
                    category=RefactorCategory.FIX_NAMING.value,
                    priority=RefactorPriority.LOW.value,
                    file_path=row['file'],
                    line_number=row['line_number'],
                    entity_name=f"{row['class_name']}.{name}",
                    description=f"方法名 '{name}' 不符合camelCase命名规范。",
                    current_code=f"// {name}()",
                    suggested_code=f"// {self._suggest_method_name(name)}()",
                    steps=[
                        f"1. 将方法名 '{name}' 重命名为 '{self._suggest_method_name(name)}'",
                        "2. 更新所有调用此方法的地方",
                        "3. 运行测试验证"
                    ],
                    impact={"consistency": "+10%", "risk": "低"},
                    estimated_effort="小（15分钟）",
                    references=[f"{row['class_name']}.{name}"]
                ))

        return suggestions

    def _suggest_reduce_coupling(self) -> List[RefactorSuggestion]:
        """建议降低耦合度"""
        suggestions = []

        # 找出被过多其他类调用的方法（高扇入）
        cursor = self.conn.execute("""
            SELECT callee, callee_class, COUNT(DISTINCT caller_class) as caller_classes,
                   COUNT(*) as total_calls
            FROM calls
            WHERE callee_class IS NOT NULL AND callee_class != ''
            GROUP BY callee, callee_class
            HAVING caller_classes > ?
            ORDER BY total_calls DESC
            LIMIT 20
        """, (5,))

        for row in cursor.fetchall():
            method_name = row['callee']
            class_name = row['callee_class']
            caller_count = row['caller_classes']
            total_calls = row['total_calls']

            # 获取调用者列表
            callers = self.conn.execute("""
                SELECT DISTINCT caller_class FROM calls
                WHERE callee = ? AND callee_class = ?
                LIMIT 10
            """, (method_name, class_name)).fetchall()

            caller_names = [r['caller_class'] for r in callers if r['caller_class']]

            suggestions.append(RefactorSuggestion(
                id=self._next_id(),
                title=f"解耦: {class_name}.{method_name}（被{caller_count}个类调用）",
                category=RefactorCategory.DECOUPLE.value,
                priority=RefactorPriority.MEDIUM.value,
                file_path="",
                line_number=0,
                entity_name=f"{class_name}.{method_name}",
                description=f"方法 '{class_name}.{method_name}' 被{caller_count}个不同的类调用"
                            f"（共{total_calls}次）。高耦合度意味着修改此方法会影响多个类。",
                current_code=f"// {class_name}.{method_name}() - 被{caller_count}个类依赖",
                suggested_code=(
                    f"// 考虑引入接口或事件机制解耦\n"
                    f"// interface I{class_name} {{\n"
                    f"//   {method_name}(): void;\n"
                    f"// }}\n"
                    f"// 调用方依赖接口而非具体实现"
                ),
                steps=[
                    f"1. 为 '{class_name}.{method_name}' 定义接口",
                    "2. 让调用方依赖接口而非具体实现",
                    "3. 考虑使用依赖注入",
                    "4. 运行测试验证"
                ],
                impact={
                    "coupling": "-30%",
                    "flexibility": "+25%",
                    "risk": "中"
                },
                estimated_effort="中（2-4小时）",
                references=[f"{class_name}.{method_name}"] + caller_names[:5]
            ))

        return suggestions

    def _suggest_improve_exception_handling(self) -> List[RefactorSuggestion]:
        """建议改善异常处理"""
        suggestions = []

        # 从数据库获取文件列表
        cursor = self.conn.execute("SELECT DISTINCT file FROM methods")
        files = [row['file'] for row in cursor.fetchall()]

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            # 检测空catch块
            empty_catch_pattern = r'catch\s*\([^)]*\)\s*\{\s*\}'
            for match in re.finditer(empty_catch_pattern, content):
                line_num = content[:match.start()].count('\n') + 1

                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"修复空异常处理（{file_path}:{line_num}）",
                    category=RefactorCategory.HANDLE_EXCEPTION.value,
                    priority=RefactorPriority.HIGH.value,
                    file_path=file_path,
                    line_number=line_num,
                    entity_name=file_path,
                    description="发现空的catch块，异常被静默吞没。"
                                "这会隐藏潜在的错误，使调试变得困难。",
                    current_code="catch (e) { }",
                    suggested_code=(
                        "catch (e) {\n"
                        "  console.error('操作失败:', e.message);\n"
                        "  // 或: logger.error('操作失败', e);\n"
                        "}"
                    ),
                    steps=[
                        "1. 确定异常的类型和来源",
                        "2. 添加适当的错误日志",
                        "3. 考虑是否需要向上抛出",
                        "4. 添加恢复逻辑（如果适用）"
                    ],
                    impact={
                        "debuggability": "+50%",
                        "reliability": "+30%",
                        "risk": "低"
                    },
                    estimated_effort="小（15-30分钟）",
                    references=[file_path]
                ))

            # 检测过宽的catch
            broad_catch_pattern = r'catch\s*\(\s*(?:Error|Exception|any|e)\s*\)\s*\{'
            for match in re.finditer(broad_catch_pattern, content):
                line_num = content[:match.start()].count('\n') + 1

                # 跳过已经被标记为空catch的
                is_empty = False
                start = match.end()
                end = content.find('}', start)
                if end > start:
                    block = content[start:end].strip()
                    if not block:
                        is_empty = True

                if not is_empty:
                    suggestions.append(RefactorSuggestion(
                        id=self._next_id(),
                        title=f"细化异常捕获（{file_path}:{line_num}）",
                        category=RefactorCategory.HANDLE_EXCEPTION.value,
                        priority=RefactorPriority.LOW.value,
                        file_path=file_path,
                        line_number=line_num,
                        entity_name=file_path,
                        description="发现过宽的异常捕获，建议捕获具体的异常类型以提高代码精确性。",
                        current_code="catch (e) { ... }",
                        suggested_code=(
                            "catch (e) {\n"
                            "  if (e instanceof SpecificError) {\n"
                            "    // 处理特定错误\n"
                            "  } else {\n"
                            "    throw e; // 重新抛出未知异常\n"
                            "  }\n"
                            "}"
                        ),
                        steps=[
                            "1. 分析catch块中实际处理的异常类型",
                            "2. 将通用catch替换为具体异常类型",
                            "3. 对无法处理的异常重新抛出",
                            "4. 运行测试验证"
                        ],
                        impact={
                            "precision": "+20%",
                            "debuggability": "+15%",
                            "risk": "低"
                        },
                        estimated_effort="小（30分钟）",
                        references=[file_path]
                    ))

        return suggestions

    def _suggest_remove_duplication(self) -> List[RefactorSuggestion]:
        """建议消除重复代码"""
        suggestions = []

        # 找出被多处调用的相同模式
        cursor = self.conn.execute("""
            SELECT caller, caller_class, callee, callee_class,
                   COUNT(*) as call_count, COUNT(DISTINCT file) as file_count
            FROM calls
            GROUP BY caller, caller_class, callee, callee_class
            HAVING call_count > 3 AND file_count > 1
            ORDER BY call_count DESC
            LIMIT 15
        """)

        for row in cursor.fetchall():
            caller = row['caller']
            callee = row['callee']
            call_count = row['call_count']
            file_count = row['file_count']

            suggestions.append(RefactorSuggestion(
                id=self._next_id(),
                title=f"消除重复: '{callee}'在{file_count}个文件中被调用{call_count}次",
                category=RefactorCategory.REMOVE_DUPLICATION.value,
                priority=RefactorPriority.MEDIUM.value,
                file_path="",
                line_number=0,
                entity_name=callee,
                description=f"方法 '{callee}' 在{file_count}个不同文件中被重复调用{call_count}次。"
                            f"考虑是否可以统一调用方式或提取公共逻辑。",
                current_code=f"// '{callee}' 在多个文件中重复调用",
                suggested_code=(
                    f"// 考虑引入工具类或服务层统一管理\n"
                    f"// class {callee}Helper {{\n"
                    f"//   static {callee}() {{ ... }}\n"
                    f"// }}"
                ),
                steps=[
                    f"1. 分析 '{callee}' 的{call_count}处调用",
                    "2. 检查调用逻辑是否相同",
                    "3. 如果相同，提取为公共方法",
                    "4. 如果相似但有差异，考虑模板方法模式",
                    "5. 运行测试验证"
                ],
                impact={
                    "maintainability": "+25%",
                    "consistency": "+20%",
                    "risk": "中"
                },
                estimated_effort="中（1-3小时）",
                references=[callee]
            ))

        return suggestions

    def _suggest_add_documentation(self) -> List[RefactorSuggestion]:
        """建议添加文档注释"""
        suggestions = []

        # 找出没有注释的公共方法（通过TODO/FIXME缺失来推断）
        cursor = self.conn.execute("""
            SELECT m.name, m.class_name, m.file, m.line_number, m.is_private
            FROM methods m
            WHERE m.is_private = 0
            ORDER BY m.class_name, m.line_number
        """)

        # 按类分组
        class_methods = {}
        for row in cursor.fetchall():
            cls = row['class_name']
            if cls not in class_methods:
                class_methods[cls] = []
            class_methods[cls].append(row)

        for class_name, methods in class_methods.items():
            if len(methods) < 3:
                continue

            file_path = methods[0]['file']

            # 检查文件是否有足够的注释
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.split('\n')
                code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('//'))
                comment_lines = sum(1 for line in lines if line.strip().startswith('//'))
                comment_ratio = comment_lines / max(code_lines, 1)
            except Exception:
                comment_ratio = 0

            if comment_ratio < self.THRESHOLDS['low_comment_ratio']:
                method_names = [m['name'] for m in methods[:5]]
                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"添加文档: {class_name}（{len(methods)}个公共方法）",
                    category=RefactorCategory.ADD_COMMENTS.value,
                    priority=RefactorPriority.LOW.value,
                    file_path=file_path,
                    line_number=methods[0]['line_number'],
                    entity_name=class_name,
                    description=f"类 '{class_name}' 有{len(methods)}个公共方法，"
                                f"但注释率仅{comment_ratio*100:.1f}%。"
                                f"建议为公共API添加文档注释。",
                    current_code=f"// {class_name} - 注释率 {comment_ratio*100:.1f}%",
                    suggested_code=(
                        f"/**\n"
                        f" * {class_name} 类的描述\n"
                        f" *\n"
                        f" * @since 1.0.0\n"
                        f" */\n"
                        f"class {class_name} {{\n"
                        f"  /**\n"
                        f"   * {method_names[0]} 方法的描述\n"
                        f"   * @param params 参数说明\n"
                        f"   * @returns 返回值说明\n"
                        f"   */\n"
                        f"  {method_names[0]}() {{ }}\n"
                        f"}}"
                    ),
                    steps=[
                        f"1. 为类 '{class_name}' 添加类级别的文档注释",
                        "2. 为每个公共方法添加JSDoc风格的注释",
                        "3. 记录参数、返回值和异常",
                        "4. 添加使用示例（如果复杂）"
                    ],
                    impact={
                        "documentation": "+50%",
                        "onboarding": "+30%",
                        "risk": "无"
                    },
                    estimated_effort="小（30-60分钟）",
                    references=[class_name]
                ))

        return suggestions

    def _suggest_reduce_parameters(self) -> List[RefactorSuggestion]:
        """建议减少参数数量"""
        suggestions = []

        # 通过方法名模式推断可能参数过多的方法
        cursor = self.conn.execute("""
            SELECT m.name, m.class_name, m.file, m.line_number
            FROM methods m
        """)

        for row in cursor.fetchall():
            method_name = row['name']
            class_name = row['class_name']
            file_path = row['file']
            line_number = row['line_number']

            # 尝试从源码中读取参数数量
            param_count = self._count_method_params(file_path, line_number, method_name)

            if param_count > self.THRESHOLDS['many_params']:
                suggestions.append(RefactorSuggestion(
                    id=self._next_id(),
                    title=f"减少参数: {class_name}.{method_name}（{param_count}个参数）",
                    category=RefactorCategory.REDUCE_PARAMS.value,
                    priority=RefactorPriority.MEDIUM.value,
                    file_path=file_path,
                    line_number=line_number,
                    entity_name=f"{class_name}.{method_name}",
                    description=f"方法 '{method_name}' 有{param_count}个参数，"
                                f"超过阈值{self.THRESHOLDS['many_params']}个。"
                                f"参数过多会降低可读性和可测试性。",
                    current_code=f"{method_name}(p1, p2, p3, p4, p5, p6) {{ }}",
                    suggested_code=(
                        f"// 方案1: 引入参数对象\n"
                        f"class {method_name}Params {{\n"
                        f"  p1: string;\n"
                        f"  p2: number;\n"
                        f"  // ...\n"
                        f"}}\n"
                        f"{method_name}(params: {method_name}Params) {{ }}\n\n"
                        f"// 方案2: 使用Builder模式\n"
                        f"{method_name}()\n"
                        f"  .setP1(value)\n"
                        f"  .setP2(value)\n"
                        f"  .build();"
                    ),
                    steps=[
                        f"1. 分析 '{method_name}' 的{param_count}个参数",
                        "2. 识别相关的参数组",
                        "3. 创建参数对象（DTO）",
                        "4. 更新方法签名和调用点",
                        "5. 运行测试验证"
                    ],
                    impact={
                        "readability": "+20%",
                        "testability": "+30%",
                        "risk": "中"
                    },
                    estimated_effort="中（1-2小时）",
                    references=[f"{class_name}.{method_name}"]
                ))

        return suggestions

    # ========== 辅助方法 ==========

    def _estimate_method_length(self, file_path: str, line_number: int) -> int:
        """估算方法长度"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_number > len(lines) or line_number < 1:
                return 0

            brace_count = 0
            line_count = 0
            started = False

            for i in range(line_number - 1, min(len(lines), line_number + 300)):
                line = lines[i]
                line_count += 1

                if '{' in line:
                    brace_count += line.count('{')
                    started = True
                if '}' in line:
                    brace_count -= line.count('}')

                if started and brace_count == 0:
                    break

            return line_count
        except Exception:
            return 0

    def _get_method_inner_calls(self, method_name: str, class_name: str) -> List[Dict]:
        """获取方法内部的调用"""
        cursor = self.conn.execute("""
            SELECT callee, callee_class, COUNT(*) as count
            FROM calls
            WHERE caller = ? AND caller_class = ?
            GROUP BY callee, callee_class
            ORDER BY count DESC
        """, (method_name, class_name))

        return [dict(row) for row in cursor.fetchall()]

    def _analyze_class_responsibilities(self, class_name: str) -> List[Dict]:
        """分析类的职责分组"""
        cursor = self.conn.execute("""
            SELECT name, file FROM methods WHERE class_name = ?
        """, (class_name,))

        methods = [dict(row) for row in cursor.fetchall()]
        if len(methods) < 5:
            return []

        # 基于方法名前缀分组
        groups = {}
        for m in methods:
            # 提取方法名前缀（on/get/set/is/handle/build/create等）
            name = m['name']
            parts = re.split(r'(?=[A-Z])', name)
            prefix = parts[0].lower() if parts else name

            # 归类
            if prefix in ('on', 'handle'):
                group_name = "事件处理"
            elif prefix in ('get', 'fetch', 'load', 'query'):
                group_name = "数据获取"
            elif prefix in ('set', 'update', 'save', 'write'):
                group_name = "数据修改"
            elif prefix in ('is', 'has', 'can', 'check', 'validate'):
                group_name = "条件判断"
            elif prefix in ('create', 'build', 'make', 'init'):
                group_name = "构建创建"
            elif prefix in ('render', 'draw', 'display', 'show'):
                group_name = "渲染展示"
            elif prefix in ('about', 'did'):
                group_name = "生命周期"
            else:
                group_name = "其他逻辑"

            if group_name not in groups:
                groups[group_name] = {'name': group_name, 'count': 0, 'methods': []}
            groups[group_name]['count'] += 1
            groups[group_name]['methods'].append(name)

        # 只返回有意义的分组（>=2个方法）
        return [g for g in groups.values() if g['count'] >= 2]

    def _generate_extract_steps(self, method_name: str, inner_calls: List[Dict],
                                 est_length: int) -> List[str]:
        """生成提取方法的步骤"""
        steps = [
            f"1. 分析方法 '{method_name}'（{est_length}行）的完整逻辑",
        ]

        if inner_calls:
            steps.append("2. 识别以下子调用可以作为独立方法提取:")
            for call in inner_calls[:5]:
                steps.append(f"   - {call['callee']}（调用{call['count']}次）")

        steps.extend([
            "3. 为每个子逻辑创建私有方法（以 _ 开头）",
            "4. 在原方法中用调用替换内联逻辑",
            "5. 确保提取后的方法有清晰的命名",
            "6. 运行测试验证行为不变"
        ])

        return steps

    def _generate_extracted_code(self, method_name: str, class_name: str,
                                  inner_calls: List[Dict]) -> str:
        """生成提取后的代码示例"""
        code = f"// {class_name} - 重构后的结构:\n"
        code += f"  {method_name}() {{\n"
        code += f"    this._prepareData();\n"

        for call in inner_calls[:4]:
            code += f"    this._{call['callee']}();\n"

        code += f"    this._cleanup();\n"
        code += f"  }}\n\n"

        for call in inner_calls[:3]:
            code += f"  private _{call['callee']}() {{\n"
            code += f"    // 从 {method_name} 中提取的逻辑\n"
            code += f"  }}\n"

        return code

    def _suggest_class_name(self, name: str) -> str:
        """建议类名"""
        # 简单的命名建议
        parts = re.split(r'[_\-\s]+', name)
        return ''.join(p.capitalize() for p in parts if p)

    def _suggest_method_name(self, name: str) -> str:
        """建议方法名"""
        parts = re.split(r'[_\-\s]+', name)
        if not parts:
            return name
        return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:] if p)

    def _count_method_params(self, file_path: str, line_number: int,
                              method_name: str) -> int:
        """从源码中计算方法参数数量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 搜索方法签名
            for i in range(max(0, line_number - 2), min(len(lines), line_number + 5)):
                line = lines[i]
                if method_name in line and '(' in line:
                    # 提取括号内的参数
                    match = re.search(r'\(([^)]*)\)', line)
                    if match:
                        params = match.group(1).strip()
                        if not params:
                            return 0
                        return len([p.strip() for p in params.split(',') if p.strip()])
        except Exception:
            pass
        return 0

    def get_summary(self) -> Dict:
        """获取重构建议摘要"""
        suggestions = self.analyze_all()

        by_priority = {}
        by_category = {}
        for s in suggestions:
            by_priority[s.priority] = by_priority.get(s.priority, 0) + 1
            by_category[s.category] = by_category.get(s.category, 0) + 1

        return {
            "total_suggestions": len(suggestions),
            "by_priority": by_priority,
            "by_category": by_category,
            "critical_count": by_priority.get(RefactorPriority.CRITICAL.value, 0),
            "high_count": by_priority.get(RefactorPriority.HIGH.value, 0),
            "estimated_total_effort": self._estimate_total_effort(suggestions)
        }

    def _estimate_total_effort(self, suggestions: List[RefactorSuggestion]) -> str:
        """估算总工作量"""
        hours = 0
        for s in suggestions:
            if "大" in s.estimated_effort:
                hours += 6
            elif "中" in s.estimated_effort:
                hours += 2
            elif "小" in s.estimated_effort:
                hours += 0.5

        if hours >= 40:
            return f"约{hours/8:.0f}个工作日（{hours:.0f}小时）"
        return f"约{hours:.0f}小时"

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def analyze_refactoring(db_path: str) -> Dict:
    """便捷函数：分析重构建议"""
    advisor = RefactoringAdvisor(db_path)
    try:
        suggestions = advisor.analyze_all()
        summary = advisor.get_summary()
        return {
            "summary": summary,
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
                    "steps": s.steps,
                    "impact": s.impact,
                    "effort": s.estimated_effort
                }
                for s in suggestions
            ]
        }
    finally:
        advisor.close()


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python refactoring_advisor.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    result = analyze_refactoring(db_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
