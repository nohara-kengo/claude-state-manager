"""セッション管理モジュールの単体テスト"""

import time

import pytest

from src.auth.session import (
    InMemorySessionStore,
    Session,
    SessionManager,
)


# ---------- Session.is_expired ----------


class TestSessionIsExpired:
    def test_not_expired(self):
        session = Session(user_id="u1", token="tok", expires_in=3600)
        assert session.is_expired is False

    def test_expired(self):
        session = Session(
            user_id="u1",
            token="tok",
            created_at=time.time() - 7200,
            expires_in=3600,
        )
        assert session.is_expired is True

    def test_just_expired(self):
        """expires_in=0 のセッションは即座に期限切れとなる"""
        session = Session(
            user_id="u1",
            token="tok",
            created_at=time.time() - 1,
            expires_in=0,
        )
        assert session.is_expired is True

    def test_remaining_seconds_zero_when_expired(self):
        session = Session(
            user_id="u1",
            token="tok",
            created_at=time.time() - 7200,
            expires_in=3600,
        )
        assert session.remaining_seconds == 0.0


# ---------- Session.should_refresh ----------


class TestSessionShouldRefresh:
    def test_should_refresh_within_threshold(self):
        session = Session(
            user_id="u1",
            token="tok",
            created_at=time.time() - 3400,
            expires_in=3600,
        )
        # remaining ~200s < threshold 300s
        assert session.should_refresh(threshold=300) is True

    def test_should_not_refresh_outside_threshold(self):
        session = Session(user_id="u1", token="tok", expires_in=3600)
        assert session.should_refresh(threshold=300) is False

    def test_expired_session_should_refresh(self):
        """期限切れセッションもリフレッシュ対象（remaining=0 < threshold）"""
        session = Session(
            user_id="u1",
            token="tok",
            created_at=time.time() - 7200,
            expires_in=3600,
        )
        assert session.should_refresh(threshold=300) is True


# ---------- SessionManager.get_session ----------


class TestGetSession:
    def test_get_existing_session(self):
        mgr = SessionManager()
        mgr.create_session("u1", "tok")
        assert mgr.get_session("u1") is not None
        assert mgr.get_session("u1").token == "tok"

    def test_get_nonexistent_session(self):
        mgr = SessionManager()
        assert mgr.get_session("u1") is None

    def test_get_expired_session_returns_none(self):
        mgr = SessionManager(default_expires_in=0)
        mgr.create_session("u1", "tok")
        # expires_in=0 -> 即座に期限切れ
        time.sleep(0.01)
        assert mgr.get_session("u1") is None


# ---------- SessionManager.refresh_session ----------


class TestRefreshSession:
    def test_refresh_valid_session(self):
        mgr = SessionManager()
        mgr.create_session("u1", "old_tok", refresh_token="rt")
        refreshed = mgr.refresh_session("u1", "new_tok")
        assert refreshed is not None
        assert refreshed.token == "new_tok"
        assert refreshed.refresh_token == "rt"

    def test_refresh_nonexistent_session_returns_none(self):
        mgr = SessionManager()
        assert mgr.refresh_session("u1", "tok") is None

    def test_refresh_expired_session_returns_none(self):
        """期限切れセッションをリフレッシュしようとすると None を返す"""
        mgr = SessionManager(default_expires_in=0)
        mgr.create_session("u1", "tok")
        time.sleep(0.01)
        assert mgr.refresh_session("u1", "new_tok") is None


# ---------- SessionManager.cleanup_expired ----------


class TestCleanupExpired:
    def test_cleanup_removes_expired(self):
        mgr = SessionManager(default_expires_in=0)
        mgr.create_session("u1", "tok1")
        mgr.create_session("u2", "tok2")
        time.sleep(0.01)
        count = mgr.cleanup_expired()
        assert count == 2

    def test_cleanup_keeps_valid(self):
        mgr = SessionManager(default_expires_in=3600)
        mgr.create_session("u1", "tok1")
        count = mgr.cleanup_expired()
        assert count == 0


# ---------- InMemorySessionStore ----------


class TestInMemorySessionStore:
    def test_crud_operations(self):
        store = InMemorySessionStore()
        session = Session(user_id="u1", token="tok")
        store.set("u1", session)
        assert store.get("u1") is session
        store.delete("u1")
        assert store.get("u1") is None

    def test_all_sessions(self):
        store = InMemorySessionStore()
        s1 = Session(user_id="u1", token="t1")
        s2 = Session(user_id="u2", token="t2")
        store.set("u1", s1)
        store.set("u2", s2)
        all_s = store.all_sessions()
        assert len(all_s) == 2
