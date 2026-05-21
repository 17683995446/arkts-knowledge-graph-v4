#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量解析器 - Phase 3.3
基于文件MD5哈希的变更检测，只解析修改过的文件
"""

import os
import re
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class IncrementalParser:
    """增量解析器: 只解析变更的文件"""

    def __init__(self, db_path: str = "code.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        # 确保有 md5_hash 列
        self._ensure_hash_column()
        return self

    def close(self):
        if self.conn:
            self.conn.close()

    def _ensure_hash_column(self):
        """确保 files 表有 md5_hash 列"""
        try:
            self.conn.execute("SELECT md5_hash FROM files LIMIT 1")
        except sqlite3.OperationalError:
            self.conn.execute("ALTER TABLE files ADD COLUMN md5_hash TEXT")
            self.conn.commit()

    @staticmethod
    def compute_hash(file_path: str) -> str:
        """计算文件MD5哈希"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def get_stored_hashes(self) -> Dict[str, str]:
        """获取数据库中已存储的文件哈希"""
        try:
            rows = self.conn.execute(
                "SELECT path, md5_hash FROM files"
            ).fetchall()
            return {row[0]: row[1] for row in rows if row[1]}
        except sqlite3.OperationalError:
            return {}

    def get_all_stored_files(self) -> Set[str]:
        """获取数据库中所有文件路径"""
        try:
            rows = self.conn.execute("SELECT path FROM files").fetchall()
            return {row[0] for row in rows}
        except sqlite3.OperationalError:
            return set()

    def detect_changes(self, project_path: str,
                       exclude_patterns: List[str] = None) -> Tuple[List[str], List[str], List[str]]:
        """检测变更

        Returns:
            (新增文件, 修改文件, 删除文件)
        """
        project = Path(project_path).resolve()

        # 收集当前所有源文件
        current_files = {}
        for ext in ['*.ets', '*.ts']:
            for f in project.rglob(ext):
                fp = str(f)
                if self._is_excluded(fp):
                    continue
                current_files[fp] = self.compute_hash(fp)

        # 获取存储的哈希
        stored_hashes = self.get_stored_hashes()
        stored_files = set(stored_hashes.keys())

        # 新增文件
        added = [f for f in current_files if f not in stored_files]

        # 修改文件（哈希变化）
        modified = [
            f for f in current_files
            if f in stored_files and current_files[f] != stored_hashes[f]
        ]

        # 删除文件
        deleted = [f for f in stored_files if f not in current_files]

        return added, modified, deleted

    def update_file_hash(self, file_path: str, file_hash: str):
        """更新文件的哈希值"""
        self.conn.execute(
            "UPDATE files SET md5_hash = ? WHERE path = ?",
            (file_hash, file_path)
        )

    def delete_file_records(self, file_path: str):
        """删除文件相关的所有记录"""
        # 删除 calls
        self.conn.execute("DELETE FROM calls WHERE file = ?", (file_path,))
        # 删除 methods
        self.conn.execute("DELETE FROM methods WHERE file = ?", (file_path,))
        # 删除 classes
        self.conn.execute("DELETE FROM classes WHERE file = ?", (file_path,))
        # 删除 components
        self.conn.execute("DELETE FROM components WHERE file = ?", (file_path,))
        # 删除 inherits
        self.conn.execute("DELETE FROM inherits WHERE file = ?", (file_path,))
        # 删除 decorators
        self.conn.execute("DELETE FROM decorators WHERE file = ?", (file_path,))
        # 删除 imports
        self.conn.execute("DELETE FROM imports WHERE source_file = ?", (file_path,))
        # 删除 state_relations
        self.conn.execute("DELETE FROM state_relations WHERE file = ?", (file_path,))
        # 删除 interfaces
        self.conn.execute("DELETE FROM interfaces WHERE file = ?", (file_path,))
        # 删除 enums
        self.conn.execute("DELETE FROM enums WHERE file = ?", (file_path,))
        # 删除 type_aliases
        self.conn.execute("DELETE FROM type_aliases WHERE file = ?", (file_path,))
        # 最后删除文件记录
        self.conn.execute("DELETE FROM files WHERE path = ?", (file_path,))

    def should_full_rebuild(self, project_path: str) -> bool:
        """判断是否需要全量重建

        条件:
        1. 数据库不存在
        2. files 表为空
        3. 项目结构发生重大变化（如 oh_modules 变化）
        """
        if not os.path.exists(self.db_path):
            return True

        try:
            rows = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()
            if rows[0] == 0:
                return True
        except sqlite3.OperationalError:
            return True

        return False

    @staticmethod
    def _is_excluded(file_path: str) -> bool:
        """排除非业务文件"""
        excluded = {'node_modules', 'oh_modules', '.git', '.ohos', 'build', 'dist', '.preview'}
        parts = Path(file_path).parts
        return any(p.lower() in excluded for p in parts)

    def print_change_summary(self, added: List[str], modified: List[str], deleted: List[str]):
        """打印变更摘要"""
        total = len(added) + len(modified) + len(deleted)
        if total == 0:
            print("  增量检测: 无变更，跳过解析")
        else:
            print(f"  增量检测: +{len(added)} 新增, ~{len(modified)} 修改, -{len(deleted)} 删除")
            if added:
                print(f"    新增: {[Path(f).name for f in added[:5]]}")
            if modified:
                print(f"    修改: {[Path(f).name for f in modified[:5]]}")
            if deleted:
                print(f"    删除: {[Path(f).name for f in deleted[:5]]}")
