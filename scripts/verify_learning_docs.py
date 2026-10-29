"""Offline acceptance for the curated handbook, never starts services or follows web links."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HANDBOOK = ROOT / "docs" / "learning"
CHAPTERS = (
    "01-request-and-design.md",
    "02-python-and-resources.md",
    "03-sql-and-indexes.md",
    "04-transactions-and-idempotency.md",
    "05-cache-strategies.md",
    "06-tasks-and-retries.md",
    "07-performance-and-debugging.md",
    "08-production-and-foundations.md",
)
SECTIONS = ("问题与解释", "源码入口", "动手操作", "预期现象", "反例", "自测与答案", "精选参考")


def verify() -> list[str]:
    errors: list[str] = []
    for name in ("README.md", "references.md", "maintaining.md", *CHAPTERS):
        path = HANDBOOK / name
        if not path.is_file():
            errors.append(f"Missing handbook file: {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if name in CHAPTERS:
            for section in SECTIONS:
                if f"## {section}" not in content:
                    errors.append(f"{name}: missing section {section}")
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", content):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.is_file():
                errors.append(f"{name}: broken or out-of-repository link {target}")
    return errors


if __name__ == "__main__":
    failures = verify()
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Learning handbook: {len(CHAPTERS)} chapters, required sections and local links passed")
