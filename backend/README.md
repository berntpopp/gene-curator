# Gene Curator backend

FastAPI + SQLAlchemy 2.0 API (Python 3.12, uv). Setup, commands, architecture and rules live in the
repository's [AGENTS.md](../AGENTS.md); the quick version:

```bash
make install    # from the repo root
make backend    # API on http://localhost:8051/docs
make test       # SQLite tests; `make test-postgres` for the RLS/PostgreSQL lane
```
