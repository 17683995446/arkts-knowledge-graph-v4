# -*- coding: utf-8 -*-
"""
性能剖析集成模块
支持运行时性能数据集成、热点方法识别、调用链路追踪
"""

import sqlite3
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time


@dataclass
class PerformanceMetric:
    """性能指标"""
    method_name: str
    class_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    max_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    self_time_ms: float = 0.0  # 不包含子调用的时间


@dataclass
class CallChain:
    """调用链"""
    root_method: str
    path: List[str] = field(default_factory=list)
    total_time_ms: float = 0.0
    call_count: int = 0


class PerformanceProfiler:
    """性能剖析器"""

    def __init__(self, db_path: str, profile_data_path: Optional[str] = None):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.profile_data = self._load_profile_data(profile_data_path)

    def _load_profile_data(self, path: Optional[str]) -> Dict:
        """加载性能剖析数据"""
        if not path:
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def analyze_hotspots(self, top_n: int = 20) -> List[Dict]:
        """分析热点方法"""
        hotspots = []

        # 基于调用频率的热点
        cursor = self.conn.execute("""
            SELECT callee, callee_class, COUNT(*) as call_count,
                   COUNT(DISTINCT caller) as unique_callers
            FROM calls
            GROUP BY callee, callee_class
            ORDER BY call_count DESC
            LIMIT ?
        """, (top_n,))

        for row in cursor.fetchall():
            # 计算预估执行时间（模拟）
            estimated_time = self._estimate_execution_time(
                row['callee'], row['call_count']
            )

            hotspots.append({
                'method': f"{row['callee_class']}.{row['callee']}" if row['callee_class'] else row['callee'],
                'call_count': row['call_count'],
                'unique_callers': row['unique_callers'],
                'estimated_time_ms': round(estimated_time, 2),
                'hotspot_type': 'frequency'
            })

        # 基于复杂度的热点
        complexity_hotspots = self._analyze_complexity_hotspots(top_n // 2)
        hotspots.extend(complexity_hotspots)

        # 排序并去重
        seen = set()
        unique_hotspots = []
        for h in sorted(hotspots, key=lambda x: x['call_count'], reverse=True):
            key = h['method']
            if key not in seen:
                seen.add(key)
                unique_hotspots.append(h)

        return unique_hotspots[:top_n]

    def _estimate_execution_time(self, method_name: str, call_count: int) -> float:
        """估算方法执行时间"""
        # 基础时间 + 调用次数因子
        base_time = 0.1  # 0.1ms 基础开销

        # 根据方法名特征调整
        if method_name.startswith('on') or method_name.startswith('handle'):
            base_time = 0.5  # 事件处理器通常更耗时
        elif 'render' in method_name.lower() or 'draw' in method_name.lower():
            base_time = 2.0  # 渲染方法
        elif 'fetch' in method_name.lower() or 'load' in method_name.lower():
            base_time = 10.0  # 网络请求

        return base_time * call_count

    def _analyze_complexity_hotspots(self, top_n: int) -> List[Dict]:
        """分析复杂度热点"""
        hotspots = []

        # 查找高复杂度方法（基于调用图深度）
        cursor = self.conn.execute("""
            SELECT m.name, m.class_name, COUNT(c.callee) as outgoing_calls
            FROM methods m
            LEFT JOIN calls c ON m.name = c.caller
            GROUP BY m.name, m.class_name
            HAVING outgoing_calls > 5
            ORDER BY outgoing_calls DESC
            LIMIT ?
        """, (top_n,))

        for row in cursor.fetchall():
            hotspots.append({
                'method': f"{row['class_name']}.{row['name']}" if row['class_name'] else row['name'],
                'call_count': row['outgoing_calls'] * 10,  # 加权
                'unique_callers': row['outgoing_calls'],
                'estimated_time_ms': row['outgoing_calls'] * 0.5,
                'hotspot_type': 'complexity'
            })

        return hotspots

    def trace_call_chain(self, method_name: str, max_depth: int = 5) -> List[CallChain]:
        """追踪调用链"""
        chains = []

        # 查找调用此方法的所有路径
        self._trace_upward(method_name, [], chains, max_depth)

        return chains

    def _trace_upward(self, method: str, current_path: List[str],
                      chains: List[CallChain], max_depth: int):
        """向上追踪调用者"""
        if len(current_path) >= max_depth:
            return

        cursor = self.conn.execute(
            "SELECT DISTINCT caller, caller_class FROM calls WHERE callee = ?",
            (method,)
        )

        callers = cursor.fetchall()
        if not callers:
            # 到达调用链顶端
            if current_path:
                chains.append(CallChain(
                    root_method=current_path[-1],
                    path=list(reversed(current_path + [method])),
                    total_time_ms=len(current_path) * 0.5,  # 估算
                    call_count=1
                ))
            return

        for row in callers:
            caller = f"{row['caller_class']}.{row['caller']}" if row['caller_class'] else row['caller']
            self._trace_upward(row['caller'], current_path + [method], chains, max_depth)

    def get_method_profile(self, method_name: str) -> Optional[Dict]:
        """获取方法的详细性能画像"""
        # 从数据库获取方法信息
        cursor = self.conn.execute(
            "SELECT * FROM methods WHERE name = ?",
            (method_name,)
        )
        method = cursor.fetchone()

        if not method:
            return None

        # 获取调用统计
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM calls WHERE callee = ?",
            (method_name,)
        )
        incoming_calls = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM calls WHERE caller = ?",
            (method_name,)
        )
        outgoing_calls = cursor.fetchone()[0]

        # 获取调用者列表
        cursor = self.conn.execute(
            """SELECT DISTINCT caller, caller_class, COUNT(*) as count
               FROM calls WHERE callee = ? GROUP BY caller, caller_class""",
            (method_name,)
        )
        callers = [
            {
                'method': f"{r['caller_class']}.{r['caller']}" if r['caller_class'] else r['caller'],
                'count': r['count']
            }
            for r in cursor.fetchall()
        ]

        # 获取被调用者列表
        cursor = self.conn.execute(
            """SELECT DISTINCT callee, callee_class, COUNT(*) as count
               FROM calls WHERE caller = ? GROUP BY callee, callee_class""",
            (method_name,)
        )
        callees = [
            {
                'method': f"{r['callee_class']}.{r['callee']}" if r['callee_class'] else r['callee'],
                'count': r['count']
            }
            for r in cursor.fetchall()
        ]

        # 计算性能指标
        estimated_time = self._estimate_execution_time(method_name, incoming_calls)

        return {
            'method_name': method_name,
            'class_name': method['class_name'],
            'file': method['file'],
            'line': method['line_number'],
            'incoming_calls': incoming_calls,
            'outgoing_calls': outgoing_calls,
            'estimated_time_ms': round(estimated_time, 2),
            'complexity_score': min(100, outgoing_calls * 5),
            'callers': callers[:10],  # 前10个调用者
            'callees': callees[:10],  # 前10个被调用者
            'is_hotspot': incoming_calls > 20 or outgoing_calls > 10
        }

    def generate_flame_graph_data(self) -> List[Dict]:
        """生成火焰图数据"""
        # 获取调用栈数据
        cursor = self.conn.execute("""
            SELECT caller, callee, COUNT(*) as count
            FROM calls
            GROUP BY caller, callee
            ORDER BY count DESC
            LIMIT 100
        """)

        nodes = {}
        edges = []

        for row in cursor.fetchall():
            caller = row['caller']
            callee = row['callee']
            count = row['count']

            if caller not in nodes:
                nodes[caller] = {'name': caller, 'value': 0}
            if callee not in nodes:
                nodes[callee] = {'name': callee, 'value': 0}

            nodes[callee]['value'] += count
            edges.append({'source': caller, 'target': callee, 'value': count})

        return {
            'nodes': list(nodes.values()),
            'edges': edges
        }

    def get_performance_summary(self) -> Dict:
        """获取性能概要"""
        # 总体统计
        cursor = self.conn.execute("SELECT COUNT(*) FROM methods")
        total_methods = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM calls")
        total_calls = cursor.fetchone()[0]

        # 热点方法数
        hotspots = self.analyze_hotspots(50)
        hotspot_count = len([h for h in hotspots if h['call_count'] > 10])

        # 平均调用深度估算
        cursor = self.conn.execute("""
            SELECT AVG(call_count) FROM (
                SELECT caller, COUNT(*) as call_count
                FROM calls GROUP BY caller
            )
        """)
        avg_out_degree = cursor.fetchone()[0] or 0

        return {
            'total_methods': total_methods,
            'total_calls': total_calls,
            'hotspot_count': hotspot_count,
            'avg_out_degree': round(avg_out_degree, 2),
            'call_density': round(total_calls / max(total_methods, 1), 2),
            'hotspots': hotspots[:10],
            'timestamp': time.time()
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def analyze_performance(db_path: str, profile_data_path: Optional[str] = None) -> Dict:
    """便捷函数：分析性能"""
    profiler = PerformanceProfiler(db_path, profile_data_path)
    try:
        return profiler.get_performance_summary()
    finally:
        profiler.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python performance_profiler.py <db_path> [profile_data.json]")
        sys.exit(1)

    db_path = sys.argv[1]
    profile_path = sys.argv[2] if len(sys.argv) > 2 else None

    profiler = PerformanceProfiler(db_path, profile_path)
    try:
        summary = profiler.get_performance_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    finally:
        profiler.close()
