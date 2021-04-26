"""A pool for sqlite connections."""
import threading

from sqlalchemy.pool import NullPool, StaticPool


class RecorderPool(StaticPool, NullPool):
    """A hybird of NullPool and StaticPool.

    When called from the creating thread acts like StaticPool
    When called from any other thread, acts like NullPool
    """

    def __init__(self, *args, **kw):  # pylint: disable=super-init-not-called
        """Create the pool."""
        self._tid = threading.current_thread().ident
        StaticPool.__init__(self, *args, **kw)

    def status(self):
        """Status of the pool."""
        return "RecorderPool"

    @property
    def _is_recorder(self):
        return threading.current_thread().ident == self._tid

    def _do_return_conn(self, conn):
        if self._is_recorder:
            return super()._do_return_conn(conn)
        conn.close()

    def dispose(self):
        """Dispose of the connection."""
        if self._is_recorder:
            return super().dispose()

    def _do_get(self):
        if self._is_recorder:
            return super()._do_get()
        return super(  # pylint: disable=bad-super-call
            NullPool, self
        )._create_connection()
