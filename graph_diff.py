# -*- coding: utf-8 -*-
"""
图谱对比与差异分析模块
支持两个数据库的图谱对比，可视化展示代码变更影响
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import json


class ChangeType(Enum):
    """变更类型"""
    ADDED = "added"          # 新增
    REMOVED = "removed"      # 删除
    MODIFIED = "modified"    # 修改
    UNCHANGED = "unchanged"  # 未变更


@dataclass
class EntityDiff:
    """实体差异"""
    name: str
    entity_type: str  # class, method, component
    change_type: ChangeType
    old_file: Optional[str] = None
    new_file: Optional[str] = None
    old_line: Optional[int] = None
    new_line: Optional[int] = None
    properties_changed: List[str] = field(default_factory=list)


@dataclass
class RelationDiff:
    """关系差异"""
    source: str
    target: str
    relation_type: str  # call, inherit, component
    change_type: ChangeType
    old_count: int = 0
    new_count: int = 0


@dataclass
class GraphDiff:
    """图谱差异结果"""
    old_db: str
    new_db: str
    entity_diffs: List[EntityDiff] = field(default_factory=list)
    relation_diffs: List[RelationDiff] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)


class GraphComparator:
    """图谱比较器"""

    def __init__(self, old_db: str, new_db: str):
        self.old_db = old_db
        self.new_db = new_db
        self.old_conn = sqlite3.connect(old_db)
        self.new_conn = sqlite3.connect(new_db)
        self.old_conn.row_factory = sqlite3.Row
        self.new_conn.row_factory = sqlite3.Row

    def compare_classes(self) -> List[EntityDiff]:
        """比较类/组件差异"""
        diffs = []

        # 获取两边的类
        old_classes = {
            row['name']: dict(row)
            for row in self.old_conn.execute(
                "SELECT name, file, line_number, is_component, is_entry FROM classes"
            ).fetchall()
        }
        new_classes = {
            row['name']: dict(row)
            for row in self.new_conn.execute(
                "SELECT name, file, line_number, is_component, is_entry FROM classes"
            ).fetchall()
        }

        old_names = set(old_classes.keys())
        new_names = set(new_classes.keys())

        # 新增的类
        for name in new_names - old_names:
            cls = new_classes[name]
            diffs.append(EntityDiff(
                name=name,
                entity_type="component" if cls.get('is_component') else "class",
                change_type=ChangeType.ADDED,
                new_file=cls.get('file'),
                new_line=cls.get('line_number')
            ))

        # 删除的类
        for name in old_names - new_names:
            cls = old_classes[name]
            diffs.append(EntityDiff(
                name=name,
                entity_type="component" if cls.get('is_component') else "class",
                change_type=ChangeType.REMOVED,
                old_file=cls.get('file'),
                old_line=cls.get('line_number')
            ))

        # 修改的类（文件或行号变化）
        for name in old_names & new_names:
            old_cls = old_classes[name]
            new_cls = new_classes[name]

            props_changed = []
            if old_cls.get('file') != new_cls.get('file'):
                props_changed.append('file')
            if old_cls.get('line_number') != new_cls.get('line_number'):
                props_changed.append('line_number')
            if old_cls.get('is_component') != new_cls.get('is_component'):
                props_changed.append('is_component')

            if props_changed:
                diffs.append(EntityDiff(
                    name=name,
                    entity_type="component" if new_cls.get('is_component') else "class",
                    change_type=ChangeType.MODIFIED,
                    old_file=old_cls.get('file'),
                    new_file=new_cls.get('file'),
                    old_line=old_cls.get('line_number'),
                    new_line=new_cls.get('line_number'),
                    properties_changed=props_changed
                ))
            else:
                diffs.append(EntityDiff(
                    name=name,
                    entity_type="component" if new_cls.get('is_component') else "class",
                    change_type=ChangeType.UNCHANGED,
                    old_file=old_cls.get('file'),
                    new_file=new_cls.get('file'),
                    old_line=old_cls.get('line_number'),
                    new_line=new_cls.get('line_number')
                ))

        return diffs

    def compare_methods(self) -> List[EntityDiff]:
        """比较方法差异"""
        diffs = []

        # 获取两边的方法
        old_methods = {
            (row['name'], row['class_name']): dict(row)
            for row in self.old_conn.execute(
                "SELECT name, class_name, file, line_number, is_static, is_private FROM methods"
            ).fetchall()
        }
        new_methods = {
            (row['name'], row['class_name']): dict(row)
            for row in self.new_conn.execute(
                "SELECT name, class_name, file, line_number, is_static, is_private FROM methods"
            ).fetchall()
        }

        old_keys = set(old_methods.keys())
        new_keys = set(new_methods.keys())

        # 新增的方法
        for key in new_keys - old_keys:
            method = new_methods[key]
            diffs.append(EntityDiff(
                name=f"{key[1]}.{key[0]}",
                entity_type="method",
                change_type=ChangeType.ADDED,
                new_file=method.get('file'),
                new_line=method.get('line_number')
            ))

        # 删除的方法
        for key in old_keys - new_keys:
            method = old_methods[key]
            diffs.append(EntityDiff(
                name=f"{key[1]}.{key[0]}",
                entity_type="method",
                change_type=ChangeType.REMOVED,
                old_file=method.get('file'),
                old_line=method.get('line_number')
            ))

        # 修改的方法
        for key in old_keys & new_keys:
            old_method = old_methods[key]
            new_method = new_methods[key]

            props_changed = []
            if old_method.get('file') != new_method.get('file'):
                props_changed.append('file')
            if old_method.get('line_number') != new_method.get('line_number'):
                props_changed.append('line_number')

            if props_changed:
                diffs.append(EntityDiff(
                    name=f"{key[1]}.{key[0]}",
                    entity_type="method",
                    change_type=ChangeType.MODIFIED,
                    old_file=old_method.get('file'),
                    new_file=new_method.get('file'),
                    old_line=old_method.get('line_number'),
                    new_line=new_method.get('line_number'),
                    properties_changed=props_changed
                ))

        return diffs

    def compare_calls(self) -> List[RelationDiff]:
        """比较调用关系差异"""
        diffs = []

        # 获取调用关系计数
        old_calls = {}
        for row in self.old_conn.execute(
            "SELECT caller, callee, COUNT(*) as cnt FROM calls GROUP BY caller, callee"
        ).fetchall():
            old_calls[(row['caller'], row['callee'])] = row['cnt']

        new_calls = {}
        for row in self.new_conn.execute(
            "SELECT caller, callee, COUNT(*) as cnt FROM calls GROUP BY caller, callee"
        ).fetchall():
            new_calls[(row['caller'], row['callee'])] = row['cnt']

        old_keys = set(old_calls.keys())
        new_keys = set(new_calls.keys())

        # 新增的调用
        for key in new_keys - old_keys:
            diffs.append(RelationDiff(
                source=key[0],
                target=key[1],
                relation_type="call",
                change_type=ChangeType.ADDED,
                new_count=new_calls[key]
            ))

        # 删除的调用
        for key in old_keys - new_keys:
            diffs.append(RelationDiff(
                source=key[0],
                target=key[1],
                relation_type="call",
                change_type=ChangeType.REMOVED,
                old_count=old_calls[key]
            ))

        # 调用次数变化
        for key in old_keys & new_keys:
            old_cnt = old_calls[key]
            new_cnt = new_calls[key]
            if old_cnt != new_cnt:
                diffs.append(RelationDiff(
                    source=key[0],
                    target=key[1],
                    relation_type="call",
                    change_type=ChangeType.MODIFIED,
                    old_count=old_cnt,
                    new_count=new_cnt
                ))

        return diffs

    def compare_inherits(self) -> List[RelationDiff]:
        """比较继承关系差异"""
        diffs = []

        old_inherits = set(
            (row['child_class'], row['parent_class'])
            for row in self.old_conn.execute(
                "SELECT child_class, parent_class FROM inherits"
            ).fetchall()
        )
        new_inherits = set(
            (row['child_class'], row['parent_class'])
            for row in self.new_conn.execute(
                "SELECT child_class, parent_class FROM inherits"
            ).fetchall()
        )

        # 新增的继承
        for child, parent in new_inherits - old_inherits:
            diffs.append(RelationDiff(
                source=child,
                target=parent,
                relation_type="inherit",
                change_type=ChangeType.ADDED
            ))

        # 删除的继承
        for child, parent in old_inherits - new_inherits:
            diffs.append(RelationDiff(
                source=child,
                target=parent,
                relation_type="inherit",
                change_type=ChangeType.REMOVED
            ))

        return diffs

    def compare_components(self) -> List[RelationDiff]:
        """比较组件嵌套关系差异"""
        diffs = []

        old_comps = set(
            (row['parent'], row['child'])
            for row in self.old_conn.execute(
                "SELECT parent, child FROM components"
            ).fetchall()
        )
        new_comps = set(
            (row['parent'], row['child'])
            for row in self.new_conn.execute(
                "SELECT parent, child FROM components"
            ).fetchall()
        )

        # 新增的嵌套
        for parent, child in new_comps - old_comps:
            diffs.append(RelationDiff(
                source=parent,
                target=child,
                relation_type="component",
                change_type=ChangeType.ADDED
            ))

        # 删除的嵌套
        for parent, child in old_comps - new_comps:
            diffs.append(RelationDiff(
                source=parent,
                target=child,
                relation_type="component",
                change_type=ChangeType.REMOVED
            ))

        return diffs

    def compare(self) -> GraphDiff:
        """执行完整对比"""
        class_diffs = self.compare_classes()
        method_diffs = self.compare_methods()
        call_diffs = self.compare_calls()
        inherit_diffs = self.compare_inherits()
        component_diffs = self.compare_components()

        # 计算统计
        all_entity_diffs = class_diffs + method_diffs
        all_relation_diffs = call_diffs + inherit_diffs + component_diffs

        summary = {
            "classes": {
                "total_old": len([d for d in class_diffs if d.change_type != ChangeType.ADDED]),
                "total_new": len([d for d in class_diffs if d.change_type != ChangeType.REMOVED]),
                "added": len([d for d in class_diffs if d.change_type == ChangeType.ADDED]),
                "removed": len([d for d in class_diffs if d.change_type == ChangeType.REMOVED]),
                "modified": len([d for d in class_diffs if d.change_type == ChangeType.MODIFIED]),
            },
            "methods": {
                "added": len([d for d in method_diffs if d.change_type == ChangeType.ADDED]),
                "removed": len([d for d in method_diffs if d.change_type == ChangeType.REMOVED]),
                "modified": len([d for d in method_diffs if d.change_type == ChangeType.MODIFIED]),
            },
            "relations": {
                "calls_added": len([d for d in call_diffs if d.change_type == ChangeType.ADDED]),
                "calls_removed": len([d for d in call_diffs if d.change_type == ChangeType.REMOVED]),
                "inherits_added": len([d for d in inherit_diffs if d.change_type == ChangeType.ADDED]),
                "inherits_removed": len([d for d in inherit_diffs if d.change_type == ChangeType.REMOVED]),
                "components_added": len([d for d in component_diffs if d.change_type == ChangeType.ADDED]),
                "components_removed": len([d for d in component_diffs if d.change_type == ChangeType.REMOVED]),
            },
            "impact_score": self._calculate_impact_score(all_entity_diffs, all_relation_diffs)
        }

        return GraphDiff(
            old_db=self.old_db,
            new_db=self.new_db,
            entity_diffs=all_entity_diffs,
            relation_diffs=all_relation_diffs,
            summary=summary
        )

    def _calculate_impact_score(self, entity_diffs: List[EntityDiff],
                                 relation_diffs: List[RelationDiff]) -> float:
        """计算变更影响分数 (0-100)"""
        score = 0

        # 实体变更权重
        for diff in entity_diffs:
            if diff.change_type == ChangeType.ADDED:
                score += 1
            elif diff.change_type == ChangeType.REMOVED:
                score += 3  # 删除影响更大
            elif diff.change_type == ChangeType.MODIFIED:
                score += 2

        # 关系变更权重
        for diff in relation_diffs:
            if diff.change_type == ChangeType.ADDED:
                score += 0.5
            elif diff.change_type == ChangeType.REMOVED:
                score += 1.5

        # 归一化到0-100
        return min(100, score * 2)

    def close(self):
        """关闭数据库连接"""
        self.old_conn.close()
        self.new_conn.close()


def diff_to_dict(diff: GraphDiff) -> dict:
    """将差异结果转换为字典"""
    return {
        "old_db": diff.old_db,
        "new_db": diff.new_db,
        "summary": diff.summary,
        "entities": [
            {
                "name": d.name,
                "type": d.entity_type,
                "change": d.change_type.value,
                "old_file": d.old_file,
                "new_file": d.new_file,
                "old_line": d.old_line,
                "new_line": d.new_line,
                "properties_changed": d.properties_changed
            }
            for d in diff.entity_diffs
        ],
        "relations": [
            {
                "source": d.source,
                "target": d.target,
                "type": d.relation_type,
                "change": d.change_type.value,
                "old_count": d.old_count,
                "new_count": d.new_count
            }
            for d in diff.relation_diffs
        ]
    }


def compare_graphs(old_db: str, new_db: str) -> dict:
    """对比两个图谱并返回结果字典"""
    comparator = GraphComparator(old_db, new_db)
    try:
        diff = comparator.compare()
        return diff_to_dict(diff)
    finally:
        comparator.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python graph_diff.py <old_db> <new_db>")
        sys.exit(1)

    old_db, new_db = sys.argv[1], sys.argv[2]
    result = compare_graphs(old_db, new_db)
    print(json.dumps(result, indent=2, ensure_ascii=False))
