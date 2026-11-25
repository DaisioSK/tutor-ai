"""parts/ → story-table.md → story.html（卡片标签带章名与节名）+ story.pdf（手机版）。
用法：python3 assemble.py <story_dir> <book_dir> [--no-pdf]
parts 命名：0-head.md（引子 + 图例）· 1-preview.md（前瞻章节，可选）· act01.md … actNN.md（每幕一份，大幕可拆 act03a / act03b）· 9-tail.md（结尾串讲），按文件名排序拼接。"""
import subprocess
import sys
from pathlib import Path

d = Path(sys.argv[1])
allp = sorted((d / "parts").glob("*.md"))
parts = ([p for p in allp if p.stem.endswith("head")] + [p for p in allp if p.stem.endswith("preview")]
         + [p for p in allp if p.stem.startswith("act")]
         + [p for p in allp if p.stem.endswith("tail")])
if not parts:
    sys.exit(f"{d}/parts/ 里没有 md")
table = d / "story-table.md"
table.write_text("\n".join(p.read_text(encoding="utf-8").rstrip("\n") + "\n" for p in parts), encoding="utf-8")
print("拼接:", " + ".join(p.name for p in parts), "→", table.name)
here = Path(__file__).resolve().parent
cmd = [sys.executable, str(here / "to_html.py"), str(table), str(d / "story.html"), "--book", sys.argv[2]]
subprocess.run(cmd + ([] if "--no-pdf" in sys.argv else ["--pdf"]), check=True)
