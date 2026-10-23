# Agent maintenance guide
Read .specify/memory/constitution.md, then specs/001-project-foundation/{spec,plan,tasks,validation}.md.
Use installed official .agents/skills/speckit-* for new features. Update spec/plan before scope changes.
Run uv sync --frozen and uv run python scripts/verify.py. Integration requires Compose and Alembic head; run uv run pytest tests/integration explicitly.
No create_all, no per-request pools, no shared sessions across tasks, no committed .env. Current schema only lab_marker; future commerce diagrams are not implemented.
Do not claim remote CI passed unless executed on GitHub. Keep actual validation evidence and open tasks honest.

## Git workflow
The stable default branch is main. Start each new feature or fix from updated main on a new
feature/<short-name> or fix/<short-name> branch. Do not implement future features directly on main.
Push the working branch and open a pull request targeting main, with linked SDD artifacts and
actual test results. Merge only after quality and integration checks pass and review is complete.
Never commit local credentials, .env, generated data, caches, virtual environments or logs.
