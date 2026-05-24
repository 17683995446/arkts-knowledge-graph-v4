"""代码复杂度分析插件"""
import sys, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from plugin_system import AnalyzerPlugin, PluginInfo, PluginRegistry

class ComplexityAnalyzer(AnalyzerPlugin):
    def __init__(self):
        self.name = "complexity_analyzer"

    def analyze(self, db_path: str) -> dict:
        conn = sqlite3.connect(db_path)
        # 每个类的方法数
        class_methods = dict(conn.execute(
            "SELECT class_name, COUNT(*) FROM methods GROUP BY class_name"
        ).fetchall())
        # 每个类的调用关系数
        class_calls = dict(conn.execute(
            "SELECT caller_class, COUNT(*) FROM calls WHERE caller_class != '' GROUP BY caller_class"
        ).fetchall())
        # 复杂度评分
        results = []
        for cls, method_count in class_methods.items():
            call_count = class_calls.get(cls, 0)
            score = method_count * 2 + call_count * 3
            results.append({
                'class': cls, 'methods': method_count,
                'calls': call_count, 'complexity_score': score
            })
        results.sort(key=lambda x: x['complexity_score'], reverse=True)
        conn.close()
        return {'top_complex': results[:20], 'total_classes': len(class_methods)}

    def get_report(self, analysis_result: dict) -> str:
        lines = ["# 代码复杂度分析报告\n"]
        lines.append(f"总类数: {analysis_result['total_classes']}\n")
        lines.append("## Top 20 高复杂度类\n")
        for i, r in enumerate(analysis_result['top_complex'], 1):
            lines.append(f"{i}. **{r['class']}** - 方法:{r['methods']} 调用:{r['calls']} 评分:{r['complexity_score']}")
        return '\n'.join(lines)

plugin_info = PluginInfo(
    name="complexity_analyzer", version="1.0.0",
    description="代码复杂度分析插件", author="ArkTS KG",
    plugin_type="analyzer", entry_point="ComplexityAnalyzer"
)

def register(registry):
    registry.register(plugin_info)

def create_plugin():
    return ComplexityAnalyzer()
