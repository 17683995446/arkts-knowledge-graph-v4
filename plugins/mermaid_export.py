"""Mermaid 类图导出插件"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from plugin_system import ExportPlugin, PluginInfo, PluginRegistry

class MermaidExport(ExportPlugin):
    def __init__(self):
        self.name = "mermaid_export"
        self.format_name = "Mermaid"

    def export(self, data: dict, output_path: str) -> str:
        lines = ["classDiagram"]
        # 继承关系
        for inh in data.get('inherits', []):
            lines.append(f"    {inh['parent_class']} <|-- {inh['child_class']}")
        # 类和方法
        for cls in data.get('classes', []):
            for m in cls.get('methods', [])[:5]:
                lines.append(f"    {cls['name']} : {m['name']}()")
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        return output_path

    def get_file_extension(self):
        return ".mmd"

plugin_info = PluginInfo(
    name="mermaid_export", version="1.0.0",
    description="Mermaid 类图导出插件", author="ArkTS KG",
    plugin_type="export", entry_point="MermaidExport"
)

def register(registry):
    registry.register(plugin_info)

def create_plugin():
    return MermaidExport()
