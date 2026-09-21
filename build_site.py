#!/usr/bin/env python3
"""Build the English research note from src/stu.md."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "stu.md"
OUT = ROOT / "index.html"

TITLE = "Parallel Samples Raise Accuracy and Lower Utilization"
DATE = "21 September 2026"


def slugify(title: str) -> str:
    title = re.sub(r"\\\((.+?)\\\)", r"\1", title)
    title = re.sub(r"[^\w]+", "-", title.lower()).strip("-")
    return title or "section"


def protect_math(text: str) -> str:
    """Escape text but keep KaTeX delimiters intact."""
    parts = re.split(r"(\\\(.+?\\\)|\\\[[\s\S]+?\\\])", text)
    out: list[str] = []
    for part in parts:
        if part.startswith("\\(") or part.startswith("\\["):
            out.append(part.replace("&", "&amp;").replace("<", "&lt;"))
        else:
            escaped = html.escape(part)
            escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
            escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
            out.append(escaped)
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    chunks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            chunks.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            i += 1
            continue
        if not line.strip() or line.strip() == "---":
            i += 1
            continue
        if line.startswith("# ") and not line.startswith("## "):
            i += 1
            continue
        if line.startswith("\\[") or line.strip() == "\\[":
            block = [line]
            if "\\]" not in line[2:]:
                i += 1
                while i < len(lines) and "\\]" not in lines[i]:
                    block.append(lines[i])
                    i += 1
                if i < len(lines):
                    block.append(lines[i])
            raw = "\n".join(block)
            chunks.append(
                '<div class="math-block">'
                + raw.replace("&", "&amp;").replace("<", "&lt;")
                + "</div>"
            )
            i += 1
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            chunks.append(f'<h2 id="{slugify(title)}">{protect_math(title)}</h2>')
            i += 1
            continue
        para = [line]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith("#")
            and not lines[i].startswith("```")
            and lines[i].strip() != "---"
            and not lines[i].startswith("\\[")
        ):
            para.append(lines[i])
            i += 1
        chunks.append("<p>" + protect_math(" ".join(p.strip() for p in para)) + "</p>")
    return "\n".join(chunks)


def toc_html(body: str) -> str:
    items = [("top", "Introduction")]
    for sid, raw in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, flags=re.S):
        label = re.sub(r"<[^>]+>", "", raw)
        label = label.replace("&lt;", "<").replace("&amp;", "&")
        items.append((sid, label))
    items.append(("cite", "Cite"))
    lis = "\n".join(
        f'<li><a href="#{html.escape(sid)}">{html.escape(label)}</a></li>'
        for sid, label in items
    )
    return f'<nav class="toc" aria-label="Contents"><p class="toc-k">Contents</p><ol>{lis}</ol></nav>'


def page_html(body: str) -> str:
    bibtex = """@misc{huang2026stu,
  author       = {Huang, Jing and Bi, Jiaxi and Luo, Tongxu and Wang, Benyou},
  title        = {Parallel Samples Raise Accuracy and Lower Utilization},
  year         = {2026},
  howpublished = {Research note},
  note         = {Correspondence to Benyou Wang}
}"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(TITLE)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://cdn.jsdelivr.net">
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
  <link rel="stylesheet" href="css/blog.css">
</head>
<body>
  <div class="shell">
    {toc_html(body)}
    <main class="page">
    <header class="mast">
      <p class="date">{html.escape(DATE)}</p>
    </header>
    <article>
      <h1 id="top">{html.escape(TITLE)}</h1>
      <p class="byline">Jing Huang, Jiaxi Bi, Tongxu Luo, and Benyou Wang. Correspondence to Benyou Wang.</p>
      {body}
      <h2 id="cite">Cite</h2>
      <div class="bib">
        <button type="button" class="bib-copy" data-copy>Copy</button>
        <pre><code>{html.escape(bibtex)}</code></pre>
      </div>
    </article>
    <footer class="credit">Page format follows <a href="https://github.com/Jing524">How Far Are We from a Native Autoregressive Video Model?</a></footer>
    </main>
  </div>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
  <script defer src="js/math.js"></script>
  <script defer src="js/ui.js"></script>
</body>
</html>
"""


def main() -> None:
    (ROOT / ".nojekyll").write_text("")
    body = md_to_html(SRC.read_text(encoding="utf-8"))
    OUT.write_text(page_html(body), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
