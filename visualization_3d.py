# -*- coding: utf-8 -*-
"""
3D可视化模块
支持3D力导向图渲染、时序演化动画、交互式探索
输出Three.js兼容的数据格式
"""

import sqlite3
import json
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


@dataclass
class Node3D:
    """3D节点"""
    id: str
    name: str
    type: str              # class, method, component
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0        # 速度
    vy: float = 0.0
    vz: float = 0.0
    size: float = 5.0
    color: str = "#3CDDDD"
    group: int = 0         # 分组ID
    depth: int = 0         # 层级深度


@dataclass
class Edge3D:
    """3D边"""
    source: str
    target: str
    type: str              # call, inherit, component
    weight: float = 1.0
    color: str = "#666666"


@dataclass
class LayoutConfig:
    """布局配置"""
    width: float = 800
    height: float = 600
    depth: float = 400
    link_distance: float = 50
    charge_strength: float = -300
    gravity: float = 0.1
    iterations: int = 100
    cooling_rate: float = 0.95


class ForceDirectedLayout3D:
    """3D力导向布局算法"""

    def __init__(self, config: LayoutConfig = None):
        self.config = config or LayoutConfig()

    def layout(self, nodes: List[Node3D], edges: List[Edge3D]) -> List[Node3D]:
        """执行3D力导向布局"""
        if not nodes:
            return nodes

        # 初始化位置（球形分布）
        self._initialize_positions(nodes)

        # 迭代优化
        temperature = 1.0
        for iteration in range(self.config.iterations):
            # 计算力
            forces = self._compute_forces(nodes, edges)

            # 应用力
            for i, node in enumerate(nodes):
                fx, fy, fz = forces[i]
                node.vx = (node.vx + fx) * temperature
                node.vy = (node.vy + fy) * temperature
                node.vz = (node.vz + fz) * temperature

                node.x += node.vx
                node.y += node.vy
                node.z += node.vz

            # 降温
            temperature *= self.config.cooling_rate

        # 归一化到配置空间
        self._normalize_positions(nodes)

        return nodes

    def _initialize_positions(self, nodes: List[Node3D]):
        """球形初始化位置"""
        n = len(nodes)
        for i, node in enumerate(nodes):
            # 斐波那契球面分布
            phi = math.acos(1 - 2 * (i + 0.5) / n)
            theta = math.pi * (1 + math.sqrt(5)) * i

            r = self.config.width / 3
            node.x = r * math.sin(phi) * math.cos(theta)
            node.y = r * math.sin(phi) * math.sin(theta)
            node.z = r * math.cos(phi)

    def _compute_forces(self, nodes: List[Node3D],
                        edges: List[Edge3D]) -> List[Tuple[float, float, float]]:
        """计算所有节点受到的力"""
        forces = [(0.0, 0.0, 0.0) for _ in nodes]
        node_map = {n.id: i for i, n in enumerate(nodes)}

        # 斥力（节点间）
        for i, n1 in enumerate(nodes):
            fx, fy, fz = forces[i]
            for j, n2 in enumerate(nodes):
                if i == j:
                    continue

                dx = n1.x - n2.x
                dy = n1.y - n2.y
                dz = n1.z - n2.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.1

                # 库仑斥力
                force = self.config.charge_strength / (dist * dist)
                fx += force * dx / dist
                fy += force * dy / dist
                fz += force * dz / dist

            forces[i] = (fx, fy, fz)

        # 引力（边）
        for edge in edges:
            if edge.source not in node_map or edge.target not in node_map:
                continue

            i = node_map[edge.source]
            j = node_map[edge.target]
            n1, n2 = nodes[i], nodes[j]

            dx = n2.x - n1.x
            dy = n2.y - n1.y
            dz = n2.z - n1.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.1

            # 胡克引力
            force = (dist - self.config.link_distance) * 0.1
            fx = force * dx / dist
            fy = force * dy / dist
            fz = force * dz / dist

            forces[i] = (forces[i][0] + fx, forces[i][1] + fy, forces[i][2] + fz)
            forces[j] = (forces[j][0] - fx, forces[j][1] - fy, forces[j][2] - fz)

        # 重力（向中心）
        for i, node in enumerate(nodes):
            fx, fy, fz = forces[i]
            fx -= node.x * self.config.gravity
            fy -= node.y * self.config.gravity
            fz -= node.z * self.config.gravity
            forces[i] = (fx, fy, fz)

        return forces

    def _normalize_positions(self, nodes: List[Node3D]):
        """归一化位置到配置空间"""
        if not nodes:
            return

        # 计算边界
        xs = [n.x for n in nodes]
        ys = [n.y for n in nodes]
        zs = [n.z for n in nodes]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)

        range_x = max_x - min_x or 1
        range_y = max_y - min_y or 1
        range_z = max_z - min_z or 1

        # 归一化
        for node in nodes:
            node.x = (node.x - min_x) / range_x * self.config.width - self.config.width / 2
            node.y = (node.y - min_y) / range_y * self.config.height - self.config.height / 2
            node.z = (node.z - min_z) / range_z * self.config.depth - self.config.depth / 2


class Visualization3D:
    """3D可视化主类"""

    # 节点类型颜色映射
    TYPE_COLORS = {
        'class': '#4ECDC4',
        'component': '#FF6B6B',
        'method': '#45B7D1',
        'entry': '#F7DC6F',
        'service': '#BB8FCE',
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_graph_data(self, max_nodes: int = 500,
                        include_methods: bool = True) -> Dict:
        """获取图谱数据用于3D渲染"""
        nodes = []
        edges = []
        node_ids = set()

        # 获取类/组件
        cursor = self.conn.execute("""
            SELECT name, file, line_number, is_component, is_entry
            FROM classes
            LIMIT ?
        """, (max_nodes,))

        for row in cursor.fetchall():
            node_type = 'component' if row['is_component'] else 'class'
            if row['is_entry']:
                node_type = 'entry'

            nodes.append(Node3D(
                id=row['name'],
                name=row['name'],
                type=node_type,
                size=8 if node_type in ('component', 'entry') else 5,
                color=self.TYPE_COLORS.get(node_type, '#3CDDDD')
            ))
            node_ids.add(row['name'])

        # 获取方法（可选）
        if include_methods and len(nodes) < max_nodes:
            cursor = self.conn.execute("""
                SELECT name, class_name, file, line_number
                FROM methods
                LIMIT ?
            """, (max_nodes - len(nodes),))

            for row in cursor.fetchall():
                full_name = f"{row['class_name']}.{row['name']}"
                nodes.append(Node3D(
                    id=full_name,
                    name=row['name'],
                    type='method',
                    size=3,
                    color=self.TYPE_COLORS['method']
                ))
                node_ids.add(full_name)

        # 获取调用关系
        cursor = self.conn.execute("""
            SELECT caller, callee, caller_class, callee_class
            FROM calls
            LIMIT 2000
        """)

        for row in cursor.fetchall():
            source = row['caller_class'] or row['caller']
            target = row['callee_class'] or row['callee']

            if source in node_ids and target in node_ids:
                edges.append(Edge3D(
                    source=source,
                    target=target,
                    type='call',
                    weight=1.0,
                    color='rgba(102,102,102,0.4)'
                ))

        # 获取继承关系
        cursor = self.conn.execute("""
            SELECT child_class, parent_class
            FROM inherits
        """)

        for row in cursor.fetchall():
            if row['child_class'] in node_ids and row['parent_class'] in node_ids:
                edges.append(Edge3D(
                    source=row['child_class'],
                    target=row['parent_class'],
                    type='inherit',
                    weight=2.0,
                    color='rgba(255,107,107,0.6)'
                ))

        # 执行布局
        layout = ForceDirectedLayout3D()
        nodes = layout.layout(nodes, edges)

        # 转换为JSON格式
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "x": round(n.x, 2),
                    "y": round(n.y, 2),
                    "z": round(n.z, 2),
                    "size": n.size,
                    "color": n.color
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.type,
                    "weight": e.weight,
                    "color": e.color
                }
                for e in edges
            ],
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "layout": "force-directed-3d"
            }
        }

    def get_hierarchical_layout(self, max_nodes: int = 300) -> Dict:
        """获取层级布局数据（按继承层次分层）"""
        nodes = []
        edges = []
        node_ids = set()

        # 计算每个类的继承深度
        depth_map = self._compute_inheritance_depth()

        # 获取类/组件
        cursor = self.conn.execute("""
            SELECT name, is_component, is_entry
            FROM classes
            LIMIT ?
        """, (max_nodes,))

        classes = list(cursor.fetchall())

        # 按深度分组
        depth_groups = defaultdict(list)
        for row in classes:
            depth = depth_map.get(row['name'], 0)
            depth_groups[depth].append(row)

        # 为每层分配位置
        max_depth = max(depth_groups.keys()) if depth_groups else 0

        for depth, group in depth_groups.items():
            n = len(group)
            for i, row in enumerate(group):
                # 圆形分布
                angle = 2 * math.pi * i / max(n, 1)
                radius = 100 + depth * 80

                node_type = 'component' if row['is_component'] else 'class'
                if row['is_entry']:
                    node_type = 'entry'

                nodes.append(Node3D(
                    id=row['name'],
                    name=row['name'],
                    type=node_type,
                    x=radius * math.cos(angle),
                    y=depth * 100 - max_depth * 50,  # Y轴表示深度
                    z=radius * math.sin(angle),
                    size=8 if node_type in ('component', 'entry') else 5,
                    color=self.TYPE_COLORS.get(node_type, '#3CDDDD'),
                    depth=depth
                ))
                node_ids.add(row['name'])

        # 获取继承关系
        cursor = self.conn.execute("""
            SELECT child_class, parent_class FROM inherits
        """)
        for row in cursor.fetchall():
            if row['child_class'] in node_ids and row['parent_class'] in node_ids:
                edges.append(Edge3D(
                    source=row['child_class'],
                    target=row['parent_class'],
                    type='inherit',
                    color='rgba(255,107,107,0.8)'
                ))

        return {
            "nodes": [
                {
                    "id": n.id, "name": n.name, "type": n.type,
                    "x": round(n.x, 2), "y": round(n.y, 2), "z": round(n.z, 2),
                    "size": n.size, "color": n.color, "depth": n.depth
                }
                for n in nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "type": e.type, "color": e.color}
                for e in edges
            ],
            "layout": "hierarchical",
            "max_depth": max_depth
        }

    def _compute_inheritance_depth(self) -> Dict[str, int]:
        """计算继承深度"""
        cursor = self.conn.execute("""
            SELECT child_class, parent_class FROM inherits
        """)

        # 构建继承图
        children = defaultdict(list)
        parents = {}
        for row in cursor.fetchall():
            children[row['parent_class']].append(row['child_class'])
            parents[row['child_class']] = row['parent_class']

        # BFS计算深度
        depth = {}
        queue = []

        # 找到根节点（没有父类的类）
        all_classes = set(children.keys()) | set(parents.keys())
        roots = all_classes - set(parents.keys())

        for root in roots:
            depth[root] = 0
            queue.append(root)

        while queue:
            current = queue.pop(0)
            for child in children[current]:
                if child not in depth:
                    depth[child] = depth[current] + 1
                    queue.append(child)

        return depth

    def get_timeline_data(self) -> Dict:
        """获取时序演化数据（按文件修改时间）"""
        import os

        cursor = self.conn.execute("SELECT path FROM files")
        files = [row[0] for row in cursor.fetchall()]

        # 按修改时间分组
        timeline = defaultdict(list)

        for file_path in files:
            try:
                mtime = os.path.getmtime(file_path)
                # 按天分组
                day = int(mtime // 86400)
                timeline[day].append(file_path)
            except Exception:
                continue

        if not timeline:
            return {"events": [], "message": "无文件时间信息"}

        # 生成事件序列
        events = []
        min_day = min(timeline.keys())
        max_day = max(timeline.keys())

        for day in sorted(timeline.keys()):
            # 获取当天修改的类
            classes = []
            for file_path in timeline[day]:
                cursor = self.conn.execute(
                    "SELECT name FROM classes WHERE file = ?",
                    (file_path,)
                )
                classes.extend([r[0] for r in cursor.fetchall()])

            events.append({
                "day": day - min_day,  # 相对天数
                "date": day,
                "files": len(timeline[day]),
                "classes": classes[:20],  # 限制数量
                "class_count": len(classes)
            })

        return {
            "events": events,
            "total_days": max_day - min_day + 1,
            "total_events": len(events)
        }

    def get_cluster_view(self) -> Dict:
        """获取聚类视图（按命名空间/包分组）"""
        cursor = self.conn.execute("""
            SELECT name, file, is_component
            FROM classes
        """)

        clusters = defaultdict(list)

        for row in cursor.fetchall():
            # 从文件路径提取包名
            file_path = row['file'] or ''
            parts = file_path.replace('\\', '/').split('/')
            if len(parts) > 1:
                package = '/'.join(parts[:-1])
            else:
                package = 'default'

            clusters[package].append({
                "name": row['name'],
                "is_component": row['is_component']
            })

        # 为每个聚类生成位置
        nodes = []
        edges = []
        n_clusters = len(clusters)

        for i, (package, classes) in enumerate(clusters.items()):
            # 聚类中心位置
            angle = 2 * math.pi * i / max(n_clusters, 1)
            cx = 200 * math.cos(angle)
            cy = 0
            cz = 200 * math.sin(angle)

            # 聚类内的类
            for j, cls in enumerate(classes):
                # 在聚类中心周围分布
                a = 2 * math.pi * j / max(len(classes), 1)
                r = 30

                nodes.append({
                    "id": cls['name'],
                    "name": cls['name'],
                    "cluster": package,
                    "x": round(cx + r * math.cos(a), 2),
                    "y": round(cy + (j - len(classes)/2) * 10, 2),
                    "z": round(cz + r * math.sin(a), 2),
                    "size": 5,
                    "color": self.TYPE_COLORS.get(
                        'component' if cls['is_component'] else 'class',
                        '#3CDDDD'
                    )
                })

        return {
            "nodes": nodes,
            "clusters": [
                {"name": pkg, "count": len(cls_list)}
                for pkg, cls_list in clusters.items()
            ],
            "layout": "cluster"
        }

    def export_to_threejs(self, output_path: str = None) -> str:
        """导出Three.js兼容格式"""
        data = self.get_graph_data()

        # Three.js场景格式
        scene = {
            "metadata": {
                "version": 4.5,
                "type": "Object",
                "generator": "ArkTS-KG-3D"
            },
            "geometries": [],
            "materials": [],
            "object": {
                "type": "Scene",
                "name": "KnowledgeGraph3D",
                "children": []
            }
        }

        # 添加节点
        for node in data['nodes']:
            scene['object']['children'].append({
                "type": "Mesh",
                "name": node['id'],
                "position": [node['x'], node['y'], node['z']],
                "geometry": f"sphere_{node['size']}",
                "material": f"material_{node['color']}"
            })

        # 添加边（线条）
        for edge in data['edges']:
            src = next((n for n in data['nodes'] if n['id'] == edge['source']), None)
            tgt = next((n for n in data['nodes'] if n['id'] == edge['target']), None)

            if src and tgt:
                scene['object']['children'].append({
                    "type": "Line",
                    "name": f"{edge['source']}->{edge['target']}",
                    "vertices": [
                        [src['x'], src['y'], src['z']],
                        [tgt['x'], tgt['y'], tgt['z']]
                    ],
                    "material": f"line_{edge['type']}"
                })

        result = json.dumps(scene, indent=2)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(result)

        return result

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# 便捷函数
def get_3d_graph(db_path: str, max_nodes: int = 500) -> Dict:
    """获取3D图谱数据"""
    viz = Visualization3D(db_path)
    try:
        return viz.get_graph_data(max_nodes)
    finally:
        viz.close()


def get_hierarchical_graph(db_path: str) -> Dict:
    """获取层级布局数据"""
    viz = Visualization3D(db_path)
    try:
        return viz.get_hierarchical_layout()
    finally:
        viz.close()


def get_timeline_graph(db_path: str) -> Dict:
    """获取时序演化数据"""
    viz = Visualization3D(db_path)
    try:
        return viz.get_timeline_data()
    finally:
        viz.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python visualization_3d.py <db_path> [layout]")
        print("  layout: force (default), hierarchical, cluster, timeline")
        sys.exit(1)

    db_path = sys.argv[1]
    layout_type = sys.argv[2] if len(sys.argv) > 2 else 'force'

    viz = Visualization3D(db_path)
    try:
        if layout_type == 'hierarchical':
            data = viz.get_hierarchical_layout()
        elif layout_type == 'cluster':
            data = viz.get_cluster_view()
        elif layout_type == 'timeline':
            data = viz.get_timeline_data()
        else:
            data = viz.get_graph_data()

        print(json.dumps(data, indent=2, ensure_ascii=False))
    finally:
        viz.close()
