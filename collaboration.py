# -*- coding: utf-8 -*-
"""
团队协作功能模块
支持用户标注、评论、分享图谱快照、团队知识库集成
"""

import sqlite3
import json
import uuid
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import os


class AnnotationType(Enum):
    """标注类型"""
    NOTE = "note"           # 普通备注
    TODO = "todo"           # 待办事项
    QUESTION = "question"   # 疑问
    ISSUE = "issue"         # 问题
    IDEA = "idea"           # 想法


class SharePermission(Enum):
    """分享权限"""
    PRIVATE = "private"     # 私有
    TEAM = "team"           # 团队可见
    PUBLIC = "public"       # 公开


@dataclass
class User:
    """用户"""
    id: str
    username: str
    email: str
    avatar: str = ""
    created_at: str = ""


@dataclass
class Annotation:
    """标注"""
    id: str
    entity_type: str      # class, method, file
    entity_name: str
    user_id: str
    annotation_type: str
    content: str
    file_path: str
    line_number: int
    created_at: str
    updated_at: str
    resolved: bool = False
    replies: List[Dict] = None

    def __post_init__(self):
        if self.replies is None:
            self.replies = []


@dataclass
class Snapshot:
    """图谱快照"""
    id: str
    name: str
    description: str
    db_path: str
    created_by: str
    created_at: str
    permission: str
    share_token: str
    view_count: int = 0


class CollaborationManager:
    """协作管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data_dir = os.path.join(os.path.dirname(db_path), ".kg_collab")
        os.makedirs(self.data_dir, exist_ok=True)

        self.annotations_db = os.path.join(self.data_dir, "annotations.db")
        self.users_db = os.path.join(self.data_dir, "users.db")
        self.snapshots_dir = os.path.join(self.data_dir, "snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)

        self._init_databases()

    def _init_databases(self):
        """初始化数据库"""
        # 标注数据库
        conn = sqlite3.connect(self.annotations_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                annotation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS replies (
                id TEXT PRIMARY KEY,
                annotation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (annotation_id) REFERENCES annotations(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_annotations_entity 
            ON annotations(entity_type, entity_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_annotations_user 
            ON annotations(user_id)
        """)
        conn.commit()
        conn.close()

        # 用户数据库
        conn = sqlite3.connect(self.users_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                avatar TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _generate_id(self) -> str:
        """生成唯一ID"""
        return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:16]

    def _now(self) -> str:
        """当前时间"""
        return datetime.now().isoformat()

    # ========== 用户管理 ==========

    def create_user(self, username: str, email: str, avatar: str = "") -> User:
        """创建用户"""
        user = User(
            id=self._generate_id(),
            username=username,
            email=email,
            avatar=avatar,
            created_at=self._now()
        )

        conn = sqlite3.connect(self.users_db)
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
            (user.id, user.username, user.email, user.avatar, user.created_at)
        )
        conn.commit()
        conn.close()

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        conn = sqlite3.connect(self.users_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()

        if row:
            return User(**dict(row))
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        conn = sqlite3.connect(self.users_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if row:
            return User(**dict(row))
        return None

    # ========== 标注管理 ==========

    def add_annotation(self, entity_type: str, entity_name: str, user_id: str,
                       annotation_type: str, content: str,
                       file_path: str = "", line_number: int = 0) -> Annotation:
        """添加标注"""
        annotation = Annotation(
            id=self._generate_id(),
            entity_type=entity_type,
            entity_name=entity_name,
            user_id=user_id,
            annotation_type=annotation_type,
            content=content,
            file_path=file_path,
            line_number=line_number,
            created_at=self._now(),
            updated_at=self._now()
        )

        conn = sqlite3.connect(self.annotations_db)
        conn.execute(
            """INSERT INTO annotations 
               (id, entity_type, entity_name, user_id, annotation_type, 
                content, file_path, line_number, created_at, updated_at, resolved)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (annotation.id, annotation.entity_type, annotation.entity_name,
             annotation.user_id, annotation.annotation_type, annotation.content,
             annotation.file_path, annotation.line_number,
             annotation.created_at, annotation.updated_at, annotation.resolved)
        )
        conn.commit()
        conn.close()

        return annotation

    def get_annotations(self, entity_type: str = None, entity_name: str = None,
                        user_id: str = None, resolved: bool = None) -> List[Annotation]:
        """获取标注列表"""
        conn = sqlite3.connect(self.annotations_db)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM annotations WHERE 1=1"
        params = []

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_name:
            query += " AND entity_name = ?"
            params.append(entity_name)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(resolved)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()

        annotations = []
        for row in rows:
            ann = Annotation(**dict(row))
            # 加载回复
            replies = conn.execute(
                "SELECT * FROM replies WHERE annotation_id = ? ORDER BY created_at",
                (ann.id,)
            ).fetchall()
            ann.replies = [dict(r) for r in replies]
            annotations.append(ann)

        conn.close()
        return annotations

    def update_annotation(self, annotation_id: str, content: str = None,
                          resolved: bool = None) -> bool:
        """更新标注"""
        conn = sqlite3.connect(self.annotations_db)

        if content is not None:
            conn.execute(
                "UPDATE annotations SET content = ?, updated_at = ? WHERE id = ?",
                (content, self._now(), annotation_id)
            )

        if resolved is not None:
            conn.execute(
                "UPDATE annotations SET resolved = ?, updated_at = ? WHERE id = ?",
                (resolved, self._now(), annotation_id)
            )

        conn.commit()
        conn.close()
        return True

    def delete_annotation(self, annotation_id: str) -> bool:
        """删除标注"""
        conn = sqlite3.connect(self.annotations_db)
        conn.execute("DELETE FROM replies WHERE annotation_id = ?", (annotation_id,))
        conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
        conn.commit()
        conn.close()
        return True

    def add_reply(self, annotation_id: str, user_id: str, content: str) -> Dict:
        """添加回复"""
        reply = {
            "id": self._generate_id(),
            "annotation_id": annotation_id,
            "user_id": user_id,
            "content": content,
            "created_at": self._now()
        }

        conn = sqlite3.connect(self.annotations_db)
        conn.execute(
            "INSERT INTO replies VALUES (?, ?, ?, ?, ?)",
            (reply["id"], reply["annotation_id"], reply["user_id"],
             reply["content"], reply["created_at"])
        )
        conn.commit()
        conn.close()

        return reply

    # ========== 快照管理 ==========

    def create_snapshot(self, name: str, description: str, db_path: str,
                        created_by: str, permission: str = "private") -> Snapshot:
        """创建快照"""
        snapshot_id = self._generate_id()
        share_token = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]

        snapshot = Snapshot(
            id=snapshot_id,
            name=name,
            description=description,
            db_path=db_path,
            created_by=created_by,
            created_at=self._now(),
            permission=permission,
            share_token=share_token
        )

        # 复制数据库到快照目录
        snapshot_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.db")
        import shutil
        shutil.copy2(db_path, snapshot_path)

        # 保存元数据
        meta_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        with open(meta_path, 'w') as f:
            json.dump(asdict(snapshot), f, indent=2)

        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """获取快照"""
        meta_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(meta_path):
            return None

        with open(meta_path, 'r') as f:
            data = json.load(f)
            return Snapshot(**data)

    def get_snapshot_by_token(self, token: str) -> Optional[Snapshot]:
        """通过分享令牌获取快照"""
        for filename in os.listdir(self.snapshots_dir):
            if filename.endswith('.json'):
                meta_path = os.path.join(self.snapshots_dir, filename)
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                    if data.get('share_token') == token:
                        return Snapshot(**data)
        return None

    def list_snapshots(self, user_id: str = None) -> List[Snapshot]:
        """列出快照"""
        snapshots = []

        for filename in os.listdir(self.snapshots_dir):
            if filename.endswith('.json'):
                meta_path = os.path.join(self.snapshots_dir, filename)
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                    # 过滤权限
                    if data.get('permission') == 'public':
                        snapshots.append(Snapshot(**data))
                    elif data.get('permission') == 'team':
                        snapshots.append(Snapshot(**data))
                    elif data.get('created_by') == user_id:
                        snapshots.append(Snapshot(**data))

        return sorted(snapshots, key=lambda x: x.created_at, reverse=True)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        snapshot_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.db")
        meta_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")

        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

        return True

    def increment_view_count(self, snapshot_id: str):
        """增加查看次数"""
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot:
            snapshot.view_count += 1
            meta_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
            with open(meta_path, 'w') as f:
                json.dump(asdict(snapshot), f, indent=2)

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict:
        """获取协作统计"""
        conn = sqlite3.connect(self.annotations_db)

        total_annotations = conn.execute(
            "SELECT COUNT(*) FROM annotations"
        ).fetchone()[0]

        resolved_annotations = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE resolved = 1"
        ).fetchone()[0]

        total_replies = conn.execute(
            "SELECT COUNT(*) FROM replies"
        ).fetchone()[0]

        conn.close()

        snapshot_count = len([f for f in os.listdir(self.snapshots_dir)
                              if f.endswith('.json')])

        return {
            "total_annotations": total_annotations,
            "resolved_annotations": resolved_annotations,
            "pending_annotations": total_annotations - resolved_annotations,
            "total_replies": total_replies,
            "snapshot_count": snapshot_count
        }


# 便捷函数
def get_collaboration_manager(db_path: str) -> CollaborationManager:
    """获取协作管理器实例"""
    return CollaborationManager(db_path)


if __name__ == "__main__":
    import sys

    # 简单测试
    manager = CollaborationManager("test.db")

    # 创建用户
    user = manager.create_user("test_user", "test@example.com")
    print(f"Created user: {user.username}")

    # 添加标注
    ann = manager.add_annotation(
        entity_type="class",
        entity_name="TestClass",
        user_id=user.id,
        annotation_type="todo",
        content="需要重构这个方法",
        file_path="test.ets",
        line_number=10
    )
    print(f"Created annotation: {ann.id}")

    # 获取统计
    stats = manager.get_stats()
    print(f"Stats: {stats}")
