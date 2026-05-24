#!/usr/bin/env python3
"""插件系统验证测试"""
import sys, os, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from plugin_system import PluginManager

def test_plugins():
    print("=" * 50)
    print("插件系统验证")
    print("=" * 50)

    pm = PluginManager('plugins')

    # 1. 发现插件
    plugins = pm.list_available_plugins()
    r1 = len(plugins) >= 2  # 至少有 mermaid_export 和 complexity_analyzer
    print(f"\n[1] 插件发现: {'PASS' if r1 else 'FAIL'} ({len(plugins)} 个)")
    for p in plugins:
        print(f"    - {p['name']} ({p['type']}): {p['description']}")

    # 2. 实例化导出插件
    try:
        exporter = pm.get_instance('mermaid_export')
        result = exporter.export(
            {'inherits': [{'parent_class': 'A', 'child_class': 'B'}], 'classes': []},
            os.path.join(tempfile.gettempdir(), 'test.mmd')
        )
        r2 = os.path.exists(result)
        print(f"[2] Mermaid导出: {'PASS' if r2 else 'FAIL'}")
        if r2:
            os.unlink(result)
    except Exception as e:
        r2 = False
        print(f"[2] Mermaid导出: FAIL ({e})")

    # 3. 实例化分析插件
    try:
        analyzer = pm.get_instance('complexity_analyzer')
        report = analyzer.get_report({'top_complex': [], 'total_classes': 0})
        r3 = len(report) > 0
        print(f"[3] 复杂度分析: {'PASS' if r3 else 'FAIL'}")
    except Exception as e:
        r3 = False
        print(f"[3] 复杂度分析: FAIL ({e})")

    all_pass = r1 and r2 and r3
    print(f"\n总体: {'ALL PASS' if all_pass else 'HAS FAILURES'}")
    return all_pass

if __name__ == '__main__':
    success = test_plugins()
    sys.exit(0 if success else 1)
