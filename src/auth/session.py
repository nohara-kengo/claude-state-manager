"""セッション管理モジュール

ユーザー認証のセッション切れを検知し、自動的にリフレッシュする機能を提供する。
"""

import time
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
        return max(0, remaining)

    def should_refresh(self, threshold: int = 300) -> bool:
        """セッションのリフレッシュが必要かどうかを判定する

        Args:
            threshold: リフレッシュの閾値（秒）。デフォルトは5分前。
        """
        return self.remaining_seconds < threshold and not self.is_expired


class SessionManager:
    """セッションの生成・検証・リフレッシュを管理するクラス"""

    def __init__(self, default_expires_in: int = 3600):
        self._sessions: dict[str, Session] = {}
        self._default_expires_in = default_expires_in

    def create_session(self, user_id: str, token: str, refresh_token: str = "") -> Session:
        """新しいセッションを作成する"""
        session = Session(
            user_id=user_id,
            token=token,
            expires_in=self._default_expires_in,
            refresh_token=refresh_token,
        )
        self._sessions[user_id] = session
        return session

    def get_session(self, user_id: str) -> Session | None:
        """ユーザーIDからセッションを取得する。期限切れの場合はNoneを返す。"""
        session = self._sessions.get(user_id)
        if session is None:
            return None
        if session.is_expired:
            self.revoke_session(user_id)
            return None
        return session

    def refresh_session(self, user_id: str, new_token: str) -> Session | None:
        """セッションをリフレッシュする"""
        session = self._sessions.get(user_id)
        if session is None:
            return None
        refreshed = Session(
            user_id=user_id,
            token=new_token,
            expires_in=self._default_expires_in,
            refresh_token=session.refresh_token,
        )
        self._sessions[user_id] = refreshed
        return refreshed

    def revoke_session(self, user_id: str) -> None:
        """セッションを無効化する"""
        self._sessions.pop(user_id, None)

    def cleanup_expired(self) -> int:
        """期限切れのセッションを一括削除する。削除した件数を返す。"""
        expired_users = [
            uid for uid, session in self._sessions.items() if session.is_expired
        ]
        for uid in expired_users:
            del self._sessions[uid]
        return len(expired_users)
