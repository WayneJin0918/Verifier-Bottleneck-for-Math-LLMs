#!/usr/bin/env python3
"""Build the English research note from src/stu.md."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "stu.md"
OUT = ROOT / "index.html"

TITLE = "Two More Answers Cost Eight Times the Read"
DATE = "22 September 2026"


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
            escaped = apply_cites(escaped)
            out.append(escaped)
    return "".join(out)


REF_ORDER: list[str] = []
REF_TEXT: dict[str, str] = {}


def prepare_refs(md: str) -> None:
    REF_ORDER.clear()
    REF_TEXT.clear()
    match = re.search(r"```refs\n(.*?)```", md, flags=re.S)
    if not match:
        return
    for line in match.group(1).splitlines():
        if not line.strip() or "|" not in line:
            continue
        key, text = line.split("|", 1)
        key = key.strip()
        REF_ORDER.append(key)
        REF_TEXT[key] = text.strip()


def apply_cites(escaped: str) -> str:
    def link(key: str) -> str:
        if key not in REF_TEXT:
            raise SystemExit(f"unknown reference @{key}")
        number = REF_ORDER.index(key) + 1
        return f'<a class="cite" href="#ref-{key}">{number}</a>'

    def repl(match: re.Match[str]) -> str:
        keys = re.findall(r"@([A-Za-z0-9]+)", match.group(0))
        return "[" + ",".join(link(key) for key in keys) + "]"

    return re.sub(
        r"\[@[A-Za-z0-9]+\](?:\s+\[@[A-Za-z0-9]+\])*",
        repl,
        escaped,
    )


def link_urls(escaped: str) -> str:
    def repl(match: re.Match[str]) -> str:
        url = match.group(1).rstrip(".,;")
        tail = match.group(1)[len(url):]
        return f'<a href="{url}">{url}</a>{tail}'

    return re.sub(r"(https://[^\s<]+)", repl, escaped)


def refs_html() -> str:
    items = []
    for key in REF_ORDER:
        body = link_urls(html.escape(REF_TEXT[key]))
        items.append(f'<li id="ref-{key}">{body}</li>')
    return '<ol class="refs">' + "".join(items) + "</ol>"


INK = "#1a1a1a"
ACCENT = "#1f4d3a"
UMBER = "#8d5a3c"
MUTED = "#5c5c5c"
GRID = "#eeeeee"
AXIS = "#d0d0d0"


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-8:
        return str(int(round(value)))
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text


def _panel(spec: dict) -> str:
    width, height = 440, 312
    left, right, top, bottom = 62, 16, 56, 44
    x0, x1 = left, width - right
    y0, y1 = top, height - bottom
    xs = spec["x"]
    xmin, xmax = min(xs), max(xs)
    if xmin == xmax:
        xmax = xmin + 1
    ymin = spec.get("ymin", 0)
    ymax = spec["ymax"]
    yticks = spec["yticks"]
    xticks = spec.get("xticks", xs)

    def px(x: float) -> float:
        return x0 + (x - xmin) / (xmax - xmin) * (x1 - x0)

    def py(y: float) -> float:
        return y1 - (y - ymin) / (ymax - ymin) * (y1 - y0)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img">',
        f'<title>{html.escape(spec["title"])}</title>',
        f'<text x="{x0}" y="16" fill="{INK}" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">{html.escape(spec["title"])}</text>',
    ]
    colors = [ACCENT, UMBER, MUTED]
    legend_x = float(x0)
    for index, series in enumerate(spec["series"]):
        color = colors[index % len(colors)]
        name = html.escape(series["name"])
        dash_attr = ' stroke-dasharray="4 3"' if series.get("dash") else ""
        parts.append(
            f'<line x1="{legend_x:.1f}" y1="32" x2="{legend_x + 14:.1f}" y2="32" stroke="{color}" stroke-width="1.7"{dash_attr}/>'
        )
        parts.append(
            f'<text x="{legend_x + 18:.1f}" y="35.5" fill="{INK}" font-size="11" font-family="Source Sans 3, sans-serif">{name}</text>'
        )
        legend_x += 28 + 6.2 * len(series["name"])
    for tick in yticks:
        yy = py(tick)
        parts.append(f'<line x1="{x0}" y1="{yy:.2f}" x2="{x1}" y2="{yy:.2f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(
            f'<text x="{x0 - 8}" y="{yy + 3.5:.2f}" text-anchor="end" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{_fmt(tick)}</text>'
        )
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{AXIS}" stroke-width="1"/>')
    parts.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{AXIS}" stroke-width="1"/>')
    for tick in xticks:
        xx = px(tick)
        parts.append(
            f'<text x="{xx:.2f}" y="{y1 + 16}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{_fmt(tick)}</text>'
        )
    parts.append(
        f'<text x="{(x0 + x1) / 2:.2f}" y="{height - 8}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{html.escape(spec["xlabel"])}</text>'
    )
    ylabel = html.escape(spec["ylabel"])
    parts.append(
        f'<text x="16" y="{(y0 + y1) / 2:.2f}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif" transform="rotate(-90 16 {(y0 + y1) / 2:.2f})">{ylabel}</text>'
    )
    for index, series in enumerate(spec["series"]):
        color = colors[index % len(colors)]
        dash = ' stroke-dasharray="4 3"' if series.get("dash") else ""
        points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(xs, series["y"]))
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"{dash} points="{points}"/>'
        )
        for x, y in zip(xs, series["y"]):
            parts.append(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="2.5" fill="{color}"/>')
    parts.append("</svg>")
    return "".join(parts)


def _bars(spec: dict) -> str:
    width, height = 440, 312
    left, right, top, bottom = 62, 16, 56, 44
    x0, x1 = left, width - right
    y0, y1 = top, height - bottom
    xs = spec["x"]
    ymin = spec.get("ymin", 0)
    ymax = spec["ymax"]
    yticks = spec["yticks"]
    colors = [ACCENT, UMBER, MUTED]
    count = len(xs)
    nseries = max(1, len(spec["series"]))
    slot = (x1 - x0) / count
    inset = slot * 0.22
    group = slot - inset
    bar_w = group / nseries

    def py(y: float) -> float:
        return y1 - (y - ymin) / (ymax - ymin) * (y1 - y0)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img">',
        f'<title>{html.escape(spec["title"])}</title>',
        f'<text x="{x0}" y="16" fill="{INK}" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">{html.escape(spec["title"])}</text>',
    ]
    legend_x = float(x0)
    for index, series in enumerate(spec["series"]):
        color = colors[index % len(colors)]
        parts.append(f'<rect x="{legend_x:.1f}" y="26" width="10" height="10" fill="{color}"/>')
        parts.append(
            f'<text x="{legend_x + 14:.1f}" y="35.5" fill="{INK}" font-size="11" font-family="Source Sans 3, sans-serif">{html.escape(series["name"])}</text>'
        )
        legend_x += 22 + 6.2 * len(series["name"])
    for tick in yticks:
        yy = py(tick)
        parts.append(f'<line x1="{x0}" y1="{yy:.2f}" x2="{x1}" y2="{yy:.2f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(
            f'<text x="{x0 - 8}" y="{yy + 3.5:.2f}" text-anchor="end" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{_fmt(tick)}</text>'
        )
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{AXIS}" stroke-width="1"/>')
    parts.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{AXIS}" stroke-width="1"/>')
    base = py(ymin)
    for i, label in enumerate(xs):
        origin = x0 + slot * i + inset / 2
        parts.append(
            f'<text x="{origin + group / 2:.2f}" y="{y1 + 16}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{_fmt(label)}</text>'
        )
        for s, series in enumerate(spec["series"]):
            value = min(max(series["y"][i], ymin), ymax)
            top_y = py(value)
            bx = origin + s * bar_w + bar_w * 0.12
            bw = bar_w * 0.76
            parts.append(
                f'<rect x="{bx:.2f}" y="{top_y:.2f}" width="{bw:.2f}" height="{max(0.0, base - top_y):.2f}" fill="{colors[s % len(colors)]}"/>'
            )
    parts.append(
        f'<text x="{(x0 + x1) / 2:.2f}" y="{height - 8}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif">{html.escape(spec["xlabel"])}</text>'
    )
    parts.append(
        f'<text x="16" y="{(y0 + y1) / 2:.2f}" text-anchor="middle" fill="{MUTED}" font-size="11" font-family="Source Sans 3, sans-serif" transform="rotate(-90 16 {(y0 + y1) / 2:.2f})">{html.escape(spec["ylabel"])}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def chart_html(kind: str) -> str:
    ns = list(range(1, 17))
    q = 0.5
    passed = [1 - q**n for n in ns]
    util = [((1 - q**n) / n) / (1 - q) for n in ns]
    ratio = [value / passed[0] for value in passed]
    charts = {
        "proposition": {
            "caption": "Homogeneous proofs with success probability 1/2. Left: coverage and utilization at five widths. Right: the accuracy ratio A(n)/A(1), which levels off near 2. The token bar at those same widths is 1, 2, 4, 8, and 16, so the later bars sit under it.",
            "panels": [
                {
                    "title": "Pass@n and STU",
                    "xlabel": "Width n",
                    "ylabel": "Pass@n or relative STU",
                    "x": [1, 2, 4, 8, 16],
                    "ymax": 1,
                    "yticks": [0, 0.25, 0.5, 0.75, 1],
                    "bars": True,
                    "series": [
                        {"name": "Pass@n", "y": [passed[n - 1] for n in (1, 2, 4, 8, 16)]},
                        {"name": "STU / STU(1)", "y": [util[n - 1] for n in (1, 2, 4, 8, 16)]},
                    ],
                },
                {
                    "title": "Accuracy ratio",
                    "xlabel": "Width n",
                    "ylabel": "A(n) / A(1)",
                    "x": [1, 2, 4, 8, 16],
                    "ymax": 2.2,
                    "yticks": [0, 0.5, 1, 1.5, 2],
                    "bars": True,
                    "series": [
                        {"name": "A(n) / A(1)", "y": [ratio[n - 1] for n in (1, 2, 4, 8, 16)]},
                    ],
                },
            ],
        },
        "budget": {
            "caption": "Twelve easy problems, one fresh sample at each generation cap. From 512 to 1024 tokens, accuracy goes from 5 to 12 and A/τ rises, because the finished traces stop spending the extra allowance.",
            "panels": [
                {
                    "title": "Correct problems",
                    "xlabel": "Generation cap",
                    "ylabel": "Correct out of 12",
                    "x": [128, 256, 512, 1024],
                    "ymax": 12,
                    "yticks": [0, 4, 8, 12],
                    "series": [{"name": "Correct", "y": [0, 0, 5, 12]}],
                },
                {
                    "title": "Utilization",
                    "xlabel": "Generation cap",
                    "ylabel": "A/τ",
                    "x": [128, 256, 512, 1024],
                    "ymax": 2,
                    "yticks": [0, 0.5, 1, 1.5, 2],
                    "series": [{"name": "A/τ", "y": [0, 0, 0.770, 1.671]}],
                },
            ],
        },
        "width": {
            "caption": "A/τ on the easy and medium bands, at widths 1, 2, 4, 8, and 16. The medium band was selected so that some sample in the pool of 16 is correct, and that happens by width 8. A/τ falls on both bands. Each panel starts at zero and has its own vertical scale.",
            "panels": [
                {
                    "title": "Easy band",
                    "xlabel": "Width n",
                    "ylabel": "A/τ",
                    "x": [1, 2, 4, 8, 16],
                    "ymax": 1.8,
                    "yticks": [0, 0.6, 1.2, 1.8],
                    "series": [{"name": "A/τ", "y": [1.658, 0.822, 0.418, 0.210, 0.104]}],
                },
                {
                    "title": "Medium band",
                    "xlabel": "Width n",
                    "ylabel": "A/τ",
                    "x": [1, 2, 4, 8, 16],
                    "ymax": 0.16,
                    "yticks": [0, 0.04, 0.08, 0.12, 0.16],
                    "series": [{"name": "A/τ", "y": [0.136, 0.092, 0.059, 0.035, 0.017]}],
                },
            ],
        },
        "aime": {
            "caption": "AIME 2025, thirty problems, one pool of eight finished traces. Left: accuracy as a share of the 30 problems. The axis runs from 0.75 to 0.95, so the vote's dip at width 2 separates from Pass@n. Right: A/τ starts at zero and falls at every width.",
            "panels": [
                {
                    "title": "Accuracy",
                    "xlabel": "Width n",
                    "ylabel": "Share of 30 problems",
                    "x": [1, 2, 3, 4, 5, 6, 7, 8],
                    "ymin": 0.75,
                    "ymax": 0.95,
                    "yticks": [0.75, 0.8, 0.85, 0.9, 0.95],
                    "series": [
                        {"name": "Pass", "y": [25 / 30, 26 / 30, 26 / 30, 26 / 30, 26 / 30, 27 / 30, 27 / 30, 27 / 30]},
                        {"name": "Vote", "y": [25 / 30, 24 / 30, 25 / 30, 26 / 30, 26 / 30, 26 / 30, 26 / 30, 27 / 30]},
                    ],
                },
                {
                    "title": "Utilization",
                    "xlabel": "Width n",
                    "ylabel": "A/τ",
                    "x": [1, 2, 3, 4, 5, 6, 7, 8],
                    "ymax": 0.04,
                    "yticks": [0, 0.01, 0.02, 0.03, 0.04],
                    "series": [{"name": "A/τ", "y": [0.0384, 0.0188, 0.0130, 0.0100, 0.0079, 0.0066, 0.0056, 0.0051]}],
                },
            ],
        },
    }
    spec = charts[kind.strip()]
    panels = "".join((_bars if panel.get("bars", True) else _panel)(panel) for panel in spec["panels"])
    return figure_html('<div class="chart-row">' + panels + "</div>", spec["caption"])


FIG = 0


def figure_html(inner: str, caption: str) -> str:
    global FIG
    FIG += 1
    return (
        '<figure class="fig chart">'
        + inner
        + "<figcaption>"
        + html.escape(f"Figure {FIG}. {caption}")
        + "</figcaption></figure>"
    )


def _marker(name: str) -> str:
    return (
        f'<defs><marker id="arrow-{name}" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
        f'<path d="M0,0 L7,3 L0,6 Z" fill="#1a1a1a"/></marker></defs>'
    )


def _node(x, y, w, h, title, sub="", accent=False) -> str:
    stroke = "#1f4d3a" if accent else "#1a1a1a"
    fill = "#f3f7f5" if accent else "#ffffff"
    title_y = y + (h / 2 if not sub else h / 2 - 7)
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1.25"/>',
        f'<text x="{x + w / 2}" y="{title_y + 4}" text-anchor="middle" fill="#1a1a1a" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">{html.escape(title)}</text>',
    ]
    if sub:
        parts.append(
            f'<text x="{x + w / 2}" y="{title_y + 20}" text-anchor="middle" fill="#5c5c5c" font-size="11" font-family="Source Sans 3, sans-serif">{html.escape(sub)}</text>'
        )
    return "".join(parts)


def _arrow(name, x1, y1, x2, y2) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1a1a1a" stroke-width="1.2" '
        f'marker-end="url(#arrow-{name})"/>'
    )


def _frame(w: int, h: int, inner: str) -> str:
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img">'
        f'<rect width="{w}" height="{h}" rx="8" fill="#f7f7f7"/>'
        f"{inner}</svg>"
    )


def _card(x, y, w, h, symbol: str, role: str, line1: str, line2: str, tone: str) -> str:
    ink = "#1f4d3a" if tone == "num" else "#8d5a3c"
    wash = "#e7f0eb" if tone == "num" else "#f6eee6"
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#ffffff" stroke="#e4e4e4"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="8" rx="4" fill="{ink}"/>'
        f'<rect x="{x + 14}" y="{y + 24}" width="36" height="22" rx="3" fill="{wash}"/>'
        f'<text x="{x + 32}" y="{y + 40}" text-anchor="middle" fill="{ink}" font-size="14" font-weight="600" font-family="Source Serif 4, serif">{symbol}</text>'
        f'<text x="{x + 58}" y="{y + 39}" fill="{ink}" font-size="11" font-weight="600" font-family="Source Sans 3, sans-serif" letter-spacing="0.06em">{html.escape(role.upper())}</text>'
        f'<text x="{x + w / 2}" y="{y + 92}" text-anchor="middle" fill="#1a1a1a" font-size="34" font-weight="600" font-family="Source Serif 4, serif">{symbol}</text>'
        f'<text x="{x + 16}" y="{y + 132}" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">{html.escape(line1)}</text>'
        f'<text x="{x + 16}" y="{y + 150}" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">{html.escape(line2)}</text>'
    )


def _metric(x, y, label: str, frac: float, value: str, color: str) -> str:
    track = 168
    filled = max(6, track * frac)
    return (
        f'<text x="{x}" y="{y + 11}" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">{html.escape(label)}</text>'
        f'<rect x="{x + 78}" y="{y}" width="{track}" height="12" rx="2" fill="#eeeeee"/>'
        f'<rect x="{x + 78}" y="{y}" width="{filled:.1f}" height="12" rx="2" fill="{color}"/>'
        f'<text x="{x + 78 + track + 10}" y="{y + 11}" fill="#1a1a1a" font-size="12" font-weight="600" font-family="Source Sans 3, sans-serif">{html.escape(value)}</text>'
    )


def _diagram_svg(name: str) -> str:
    if name == "factors":
        cards = [
            ("A", "Return", "Exact-answer", "accuracy on the set", "num"),
            ("β", "Return", "Attention that lands", "on answer tokens", "num"),
            ("ρ", "Return", "Share of the read", "about the answer", "num"),
            ("α", "Price", "Parameters on,", "over all parameters", "den"),
            ("τ", "Price", "Tokens read,", "divided by 1024", "den"),
        ]
        inner = []
        for i, spec in enumerate(cards):
            inner.append(_card(16 + i * 148, 16, 136, 176, *spec))
        inner.append(
            '<text x="380" y="228" text-anchor="middle" fill="#1a1a1a" font-size="16" font-family="Source Serif 4, serif">'
            "STU  =  ( A · β · ρ )  /  ( α · τ )</text>"
        )
        body = _frame(760, 252, "".join(inner))
        caption = "The five factors, filled in. Green cards are the return. Brown cards are the price. The score moves only when one of these five moves, and the product does not say which."
    elif name == "split":
        left = (
            '<rect x="16" y="16" width="360" height="210" rx="6" fill="#ffffff" stroke="#1f4d3a" stroke-width="1.4"/>'
            '<text x="36" y="46" fill="#1f4d3a" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">ONE SAMPLE</text>'
            '<text x="250" y="46" fill="#1a1a1a" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">n = 1 · 25/30</text>'
            + _metric(36, 72, "Accuracy", 0.833, "83.3%", "#1f4d3a")
            + _metric(36, 112, "Tokens", 1 / 8.15, "× 1", "#8d5a3c")
            + _metric(36, 152, "A/τ", 1.0, "0.038", "#1f4d3a")
            + '<text x="36" y="200" fill="#1f4d3a" font-size="12" font-family="Source Sans 3, sans-serif">Utilization is highest here.</text>'
        )
        right = (
            '<rect x="384" y="16" width="360" height="210" rx="6" fill="#ffffff" stroke="#e4e4e4"/>'
            '<text x="404" y="46" fill="#5c5c5c" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">WIDER POOL</text>'
            '<text x="620" y="46" fill="#1a1a1a" font-size="13" font-weight="600" font-family="Source Sans 3, sans-serif">n = 8 · 27/30</text>'
            + _metric(404, 72, "Accuracy", 0.90, "90.0%", "#1f4d3a")
            + _metric(404, 112, "Tokens", 1.0, "× 8.15", "#8d5a3c")
            + _metric(404, 152, "A/τ", 0.0051 / 0.0384, "0.005", "#8d5a3c")
            + '<text x="404" y="200" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">Accuracy × 1.08. Read × 8.15.</text>'
        )
        body = _frame(760, 246, left + right)
        caption = "The split on AIME, drawn to scale. Accuracy barely moves. The read grows with the width, so A/τ shrinks. One sample is the higher-utilization side."
    elif name == "width":
        ns = [1, 2, 4, 8, 16]
        q = 0.5
        passed = [1 - q**n for n in ns]
        util = [((1 - q**n) / n) / (1 - q) for n in ns]
        cols = []
        for i, n in enumerate(ns):
            x = 24 + i * 148
            pips = []
            show = min(n, 8)
            for k in range(show):
                pips.append(
                    f'<rect x="{x + 8 + (k % 8) * 14}" y="58" width="10" height="10" rx="1" fill="#1f4d3a"/>'
                )
            extra = ""
            if n > 8:
                extra = f'<text x="{x + 124}" y="68" fill="#5c5c5c" font-size="11" font-family="Source Sans 3, sans-serif">+8</text>'
            ph = 132 * passed[i]
            uh = 132 * util[i]
            base = 214
            cols.append(
                f'<text x="{x + 62}" y="40" text-anchor="middle" fill="#1a1a1a" font-size="16" font-weight="600" font-family="Source Serif 4, serif">n = {n}</text>'
                + "".join(pips)
                + extra
                + f'<rect x="{x + 28}" y="{base - ph:.1f}" width="26" height="{ph:.1f}" rx="2" fill="#1f4d3a"/>'
                + f'<rect x="{x + 62}" y="{base - uh:.1f}" width="26" height="{uh:.1f}" rx="2" fill="#8d5a3c"/>'
                + f'<text x="{x + 41}" y="232" text-anchor="middle" fill="#1f4d3a" font-size="11" font-family="Source Sans 3, sans-serif">{passed[i]:.2f}</text>'
                + f'<text x="{x + 75}" y="232" text-anchor="middle" fill="#8d5a3c" font-size="11" font-family="Source Sans 3, sans-serif">{util[i]:.2f}</text>'
            )
        legend = (
            '<rect x="24" y="252" width="10" height="10" fill="#1f4d3a"/>'
            '<text x="40" y="262" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">Pass@n</text>'
            '<rect x="120" y="252" width="10" height="10" fill="#8d5a3c"/>'
            '<text x="136" y="262" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">STU / STU(1)</text>'
            '<text x="736" y="262" text-anchor="end" fill="#5c5c5c" font-size="12" font-family="Source Sans 3, sans-serif">p = 1/2, tokens ∝ n</text>'
        )
        body = _frame(760, 284, "".join(cols) + legend)
        caption = "One homogeneous pool, five widths. Each green square is a sample. The green bar is coverage. The brown bar is utilization scaled so one sample equals 1. Coverage climbs toward 1. Utilization falls toward 1/n."
    elif name == "reflect":
        body = f'''<svg viewBox="0 0 760 220" role="img">{_marker("reflect")}
{_node(16, 78, 168, 64, "Finished proof", "T tokens, relevance ρ")}
{_arrow("reflect", 184, 96, 206, 48)}
{_arrow("reflect", 184, 124, 206, 168)}
{_node(206, 16, 196, 64, "Critique and rewrite", "replace a fraction λ")}
{_node(206, 140, 196, 64, "New i.i.d. sample", "λ = 0")}
{_arrow("reflect", 402, 48, 430, 48)}
{_arrow("reflect", 402, 172, 430, 172)}
{_node(430, 16, 150, 64, "Relevance ρ′", "can rise or fall", accent=True)}
{_node(430, 140, 150, 64, "Relevance stays ρ", "only the length grows")}
{_arrow("reflect", 580, 48, 604, 100)}
{_arrow("reflect", 580, 172, 604, 130)}
{_node(604, 78, 140, 64, "Matched tokens", "then score accuracy", accent=True)}</svg>'''
        caption = "Reflection against resampling. A rewrite raises relevance only when the new relevant tokens outnumber the slice of the extra read that the old relevance already accounted for. An independent draw does not change relevance. The experiment holds the token count fixed and scores accuracy."
    elif name == "pipeline":
        body = f'''<svg viewBox="0 0 760 268" role="img">{_marker("pipeline")}
{_node(48, 16, 140, 44, "GSM8K")}
{_node(310, 16, 140, 44, "MATH")}
{_node(572, 16, 140, 44, "AIME")}
{_arrow("pipeline", 118, 60, 300, 88)}
{_arrow("pipeline", 380, 60, 380, 88)}
{_arrow("pipeline", 642, 60, 460, 88)}
{_node(220, 96, 320, 52, "Qwen3-4B-Thinking", "dense, α = 1")}
{_arrow("pipeline", 300, 148, 140, 176)}
{_arrow("pipeline", 380, 148, 380, 176)}
{_arrow("pipeline", 460, 148, 620, 176)}
{_node(24, 184, 210, 64, "Generation cap", "fresh sample, early stop")}
{_node(274, 184, 212, 64, "Width 1…16", "tokens not matched")}
{_node(526, 184, 210, 64, "Critique vs resample", "tokens matched", accent=True)}</svg>'''
        caption = "What the experiments vary. All three bands use the same dense checkpoint. The cap changes the allowance on one sample. Width adds independent samples and lets the read grow. Reflection is the only comparison that matches the number of tokens before scoring accuracy."
    else:
        raise SystemExit(f"unknown diagram {name}")
    return figure_html(f'<div class="diagram">{body}</div>', caption)


def numeric_cell(text: str) -> bool:
    plain = re.sub(r"\\\(.+?\\\)", "", text)
    plain = plain.replace("$", "").replace(",", "").strip()
    return bool(re.fullmatch(r"-?\d+(\.\d+)?(/\d+)?%?", plain))


def md_to_html(md: str) -> str:
    global FIG
    FIG = 0
    lines = md.splitlines()
    chunks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            body = "\n".join(code).strip()
            if lang == "chart":
                chunks.append(chart_html(body))
            elif lang == "diagram":
                chunks.append(_diagram_svg(body))
            elif lang == "refs":
                chunks.append(refs_html())
            else:
                chunks.append("<pre><code>" + html.escape(body) + "</code></pre>")
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
        if line.startswith("|"):
            rows: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                raw = lines[i].strip()
                if not re.match(r"^\|\s*-+", raw):
                    cells = [c.strip() for c in raw.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            if not rows:
                continue
            head, body_rows = rows[0], rows[1:]
            numeric_cols = []
            for col in range(len(head)):
                numeric_cols.append(all(col < len(row) and numeric_cell(row[col]) for row in body_rows))
            def cell(text: str, col: int, tag: str) -> str:
                kind = " num" if col < len(numeric_cols) and numeric_cols[col] else ""
                return f'<{tag} class="{tag}{kind}">{protect_math(text)}</{tag}>'
            thead = "".join(cell(c, col, "th") for col, c in enumerate(head))
            tbody = "".join(
                "<tr>" + "".join(cell(c, col, "td") for col, c in enumerate(row)) + "</tr>"
                for row in body_rows
            )
            chunks.append(f"<table class=\"results\"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>")
            continue
        if line.startswith("### "):
            title = line[4:].strip()
            chunks.append(f'<h3 id="{slugify(title)}">{protect_math(title)}</h3>')
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
            and not lines[i].startswith("|")
        ):
            para.append(lines[i])
            i += 1
        chunks.append("<p>" + protect_math(" ".join(p.strip() for p in para)) + "</p>")
    return "\n".join(chunks)


def toc_html(body: str) -> str:
    heads = re.findall(r'<h(2|3) id="([^"]+)">(.*?)</h\1>', body, flags=re.S)
    sections: list[list] = []
    sec = 0
    sub = 0
    for level, sid, raw in heads:
        label = re.sub(r"<[^>]+>", "", raw)
        label = label.replace("&lt;", "<").replace("&amp;", "&")
        if level == "2":
            sec += 1
            sub = 0
            sections.append([sid, f"{sec}. {label}", []])
        else:
            sub += 1
            if not sections:
                raise SystemExit(f"subsection before a section: {label}")
            sections[-1][2].append((sid, f"{sec}.{sub}  {label}"))
    parts = []
    for sid, label, children in sections:
        child_html = ""
        if children:
            inner = "".join(
                f'<li><a href="#{html.escape(csid)}">{html.escape(clabel)}</a></li>'
                for csid, clabel in children
            )
            child_html = f"<ol>{inner}</ol>"
        parts.append(
            f'<li><a href="#{html.escape(sid)}">{html.escape(label)}</a>{child_html}</li>'
        )
    parts.append('<li><a href="#cite">Cite</a></li>')
    return f'<nav class="toc" aria-label="Contents"><p class="toc-k">Contents</p><ol>{"".join(parts)}</ol></nav>'


def page_html(body: str) -> str:
    bibtex = """@misc{huang2026stu,
  author       = {Huang, Jing and Bi, Jiaxi and Luo, Tongxu and Wang, Benyou},
  title        = {Two More Answers Cost Eight Times the Read},
  year         = {2026},
  howpublished = {Research note},
  note         = {Affiliations: The Chinese University of Hong Kong, Shenzhen (CUHK-Shenzhen); Shenzhen Loop Area Institute (SLAI). Correspondence to Benyou Wang}
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
      <header class="authors">
        <p class="author-line">
          <span>Jing Huang<sup>1,2</sup></span>
          <span>Jiaxi Bi<sup>1,2</sup></span>
          <span>Tongxu Luo<sup>1,2</sup></span>
          <span>Benyou Wang<sup>1,2,*</sup></span>
        </p>
        <p class="affil-line"><sup>1</sup>The Chinese University of Hong Kong, Shenzhen (CUHK-Shenzhen)</p>
        <p class="affil-line"><sup>2</sup>Shenzhen Loop Area Institute (SLAI)</p>
        <p class="corr"><sup>*</sup>Correspondence to Benyou Wang</p>
      </header>
      {body}
      <h2 id="cite" class="unnumbered">Cite</h2>
      <div class="bib">
        <button type="button" class="bib-copy" data-copy>Copy</button>
        <pre><code>{html.escape(bibtex)}</code></pre>
      </div>
    </article>
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
    source = SRC.read_text(encoding="utf-8")
    prepare_refs(source)
    body = md_to_html(source)
    OUT.write_text(page_html(body), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
