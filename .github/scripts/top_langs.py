"""Build a "Most Used Languages" card that also counts code written in org repos.

Own repos count in full. Org repos count only the user's share of the commits,
so a big team codebase doesn't drown out everything else.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = "YakshB07"
ORG_REPOS = [
    "FRC1229/Reefscape",
    "FRC1229/Physics-SIM-frc",
]
SKIP_REPOS = {"YakshB07", "Robot"}
SKIP_LANGS = {"xBase", "Makefile", "Shell", "Batchfile", "Dockerfile", "CMake"}
LANG_COUNT = 8

COLORS = {
    "Java": "#b07219", "TypeScript": "#3178c6", "Python": "#3572A5",
    "Processing": "#0096D8", "JavaScript": "#f1e05a", "CSS": "#663399",
    "C++": "#f34b7d", "HTML": "#e34c26", "C": "#555555", "Vue": "#41b883",
    "SCSS": "#c6538c", "Kotlin": "#A97BFF", "C#": "#178600", "Go": "#00ADD8",
}


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def paged(path):
    out, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = api(f"{path}{sep}per_page=100&page={page}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def commit_share(repo):
    contributors = paged(f"/repos/{repo}/contributors")
    total = sum(c["contributions"] for c in contributors)
    mine = sum(c["contributions"] for c in contributors if c["login"].lower() == USER.lower())
    return mine / total if total else 0.0


def collect():
    totals = {}

    def add(langs, weight):
        for lang, size in langs.items():
            if lang not in SKIP_LANGS:
                totals[lang] = totals.get(lang, 0) + size * weight

    for repo in paged(f"/users/{USER}/repos?type=owner"):
        if repo["fork"] or repo["name"] in SKIP_REPOS:
            continue
        add(api(f"/repos/{repo['full_name']}/languages"), 1.0)

    for repo in ORG_REPOS:
        add(api(f"/repos/{repo}/languages"), commit_share(repo))

    return totals


def render(totals):
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LANG_COUNT]
    total = sum(v for _, v in top) or 1
    width, pad, bar_w = 350, 25, 300
    rows = (len(top) + 1) // 2
    height = 90 + rows * 25

    bar, x = [], pad
    for lang, size in top:
        w = bar_w * size / total
        bar.append(f'<rect x="{x:.2f}" y="45" width="{w:.2f}" height="8" fill="{COLORS.get(lang, "#8b949e")}"/>')
        x += w

    items = []
    for i, (lang, size) in enumerate(top):
        col, row = i // rows, i % rows
        ix, iy = pad + col * 150, 82 + row * 25
        color = COLORS.get(lang, "#8b949e")
        items.append(
            f'<circle cx="{ix + 5}" cy="{iy - 4}" r="5" fill="{color}"/>'
            f'<text x="{ix + 15}" y="{iy}" class="lang">{escape(lang)} {100 * size / total:.2f}%</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
.title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #70a5fd; }}
.lang {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #38bdae; }}
</style>
<rect width="{width}" height="{height}" rx="4.5" fill="#1a1b27"/>
<text x="{pad}" y="32" class="title">Most Used Languages</text>
<clipPath id="bar"><rect x="{pad}" y="45" width="{bar_w}" height="8" rx="4"/></clipPath>
<g clip-path="url(#bar)">{''.join(bar)}</g>
{''.join(items)}
</svg>
"""


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/top-langs.svg"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(collect()))
