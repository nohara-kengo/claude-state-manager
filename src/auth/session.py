"""セッション管理モジュール

ユーザー認証のセッション切れを検知し、自動的にリフレッシュする機能を提供する。
"""

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Session:
    """ユーザーセッションを管理するクラス"""

    user_id: str
    token: str
    created_at: float = field(default_factory=time.time)
    expires_in: int = 3600  # デフォルト1時間
    refresh_token: str = ""

    @property
    def is_expired(self) -> bool:
        """セッションが期限切れかどうかを判定する"""
        return time.time() > self.created_at + self.expires_in

    @property
    def remaining_seconds(self) -> float:
        """セッションの残り時間（秒）を返す"""
        remaining = (self.created_at + self.expires_in) - time.time()
        return max(0.0, remaining)

    def should_refresh(self, threshold: int = 300) -> bool:
        """セッションのリフレッシュが必要かどうかを判定する

        is_expired が True の場合、remaining_seconds は 0 となるため
        threshold > 0 であれば常にリフレッシュ対象となる。
        期限切れセッションもリフレッシュ対象として扱う。

        Args:
            threshold: リフレッシュの閾値（秒）。デフォルトは5分前。
        """
        return self.remaining_seconds < threshold


class AbstractSessionStore(ABC):
    """セッションストアの抽象インターフェース"""

    @abstractmethod
    def get(self, user_id: str) -> Session | None:
        """ユーザーIDからセッションを取得する"""

    @abstractmethod
    def set(self, user_id: str, session: Session) -> None:
        """セッションを保存する"""

    @abstractmethod
    def delete(self, user_id: str) -> None:
        """セッションを削除する"""

    @abstractmethod
    def all_sessions(self) -> dict[str, Session]:
        """全セッションを返す"""


class InMemorySessionStore(AbstractSessionStore):
    """インメモリセッションストア"""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, user_id: str) -> Session | None:
        return self._sessions.get(user_id)

    def set(self, user_id: str, session: Session) -> None:
        self._sessions[user_id] = session

    def delete(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)

    def all_sessions(self) -> dict[str, Session]:
        return dict(self._sessions)


class SessionManager:
    """セッションの生成・検証・リフレッシュを管理するクラス

    threading.Lock により並行アクセスを制御する。
    """

    def __init__(
        self,
        default_expires_in: int = 3600,
        store: AbstractSessionStore | None = None,
    ):
        self._store = store or InMemorySessionStore()
        self._default_expires_in = default_expires_in
        self._lock = threading.Lock()

    def create_session(self, user_id: str, token: str, refresh_token: str = "") -> Session:
        """新しいセッションを作成する"""
        session = Session(
            user_id=user_id,
            token=token,
            expires_in=self._default_expires_in,
            refresh_token=refresh_token,
        )
        with self._lock:
            self._store.set(user_id, session)
        return session

    def get_session(self, user_id: str) -> Session | None:
        """ユーザーIDからセッションを取得する。期限切れの場合はNoneを返す。"""
        with self._lock:
            session = self._store.get(user_id)
            if session is None:
                return None
            if session.is_expired:
                self._store.delete(user_id)
                return None
            return session

    def refresh_session(self, user_id: str, new_token: str) -> Session | None:
        """セッションをリフレッシュする

        期限切れセッションの場合は None を返し、リフレッシュしない。
        """
        with self._lock:
            session = self._store.get(user_id)
            if session is None:
                return None
            if session.is_expired:
                self._store.delete(user_id)
                return None
            refreshed = Session(
                user_id=user_id,
                token=new_token,
                expires_in=self._default_expires_in,
                refresh_token=session.refresh_token,
            )
            self._store.set(user_id, refreshed)
            return refreshed

    def revoke_session(self, user_id: str) -> None:
        """セッションを無効化する"""
        with self._lock:
            self._store.delete(user_id)

    def cleanup_expired(self) -> int:
        """期限切れのセッションを一括削除する。削除した件数を返す。

        revoke_session の内部ロジック（store.delete）を再利用する。
        """
        with self._lock:
            expired_users = [
                uid
                for uid, session in self._store.all_sessions().items()
                if session.is_expired
            ]
            for uid in expired_users:
                self._store.delete(uid)
            return len(expired_users)
