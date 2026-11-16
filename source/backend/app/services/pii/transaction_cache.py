"""Keep PII caches inside the database session and current transaction scope."""

import threading
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import AsyncSession


class TransactionCache:
    def __init__(self):
        self._states = WeakKeyDictionary()
        self._lock = threading.Lock()

    def for_session(self, db: AsyncSession) -> dict:
        outer = db.sync_session.get_transaction()
        nested = db.sync_session.get_nested_transaction()
        with self._lock:
            state = self._states.get(db)
            if state is None or state[0] is not outer or state[1] is not nested:
                state = (outer, nested, {})
                self._states[db] = state
            return state[2]

    def invalidate(self, session_id=None) -> None:
        with self._lock:
            for _, _, entries in list(self._states.values()):
                if session_id is None:
                    entries.clear()
                else:
                    entries.pop(session_id, None)
