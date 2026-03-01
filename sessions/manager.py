import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SESSION_TTL = 600  # 10 minutes
TOKEN_SUMMARISE_THRESHOLD = 1500
TOKEN_MEMORY_THRESHOLD = 100


@dataclass
class Session:
    user_id: str
    app: str
    messages: list[dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    summary: str | None = None

    @property
    def key(self) -> str:
        return f"{self.app}:{self.user_id}"

    def touch(self) -> None:
        self.last_active = time.time()

    @property
    def expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TTL

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self.touch()

    def estimated_tokens(self) -> int:
        return sum(len(m["content"]) // 4 for m in self.messages)

    def needs_mid_summary(self) -> bool:
        return self.estimated_tokens() > TOKEN_SUMMARISE_THRESHOLD

    def ai_output_tokens(self) -> int:
        return sum(
            len(m["content"]) // 4
            for m in self.messages
            if m["role"] == "assistant"
        )


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._callbacks: list = []

    def on_expire(self, callback) -> None:
        self._callbacks.append(callback)

    def get_or_create(self, user_id: str, app: str) -> Session:
        key = f"{app}:{user_id}"
        session = self._sessions.get(key)
        if session and not session.expired:
            session.touch()
            return session
        if session and session.expired:
            self._handle_expire(session)
        session = Session(user_id=user_id, app=app)
        self._sessions[key] = session
        logger.info("Session created: %s", key)
        return session

    def _handle_expire(self, session: Session) -> None:
        logger.info("Session expired: %s", session.key)
        for cb in self._callbacks:
            try:
                cb(session)
            except Exception:
                logger.exception("Error in session expire callback")
        self._sessions.pop(session.key, None)

    async def cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            expired = [s for s in self._sessions.values() if s.expired]
            for s in expired:
                self._handle_expire(s)

    def remove(self, key: str) -> Session | None:
        return self._sessions.pop(key, None)


sessions = SessionManager()
