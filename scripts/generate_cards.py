"""Generate README SVGs from public GitHub REST data, without a personal token."""

import argparse
from html import escape
import json
from pathlib import Path
import textwrap
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECTS = {
    "DeepCTR": "deepctr_pin.svg",
    "DeepCTR-Torch": "deepctr-torch_pin.svg",
    "DeepMatch": "deepmatch_pin.svg",
    "GraphEmbedding": "graphembedding_pin.svg",
}
COLORS = {"Python": "#3572a5", "Jupyter Notebook": "#da5b0b"}


def fetch(path):
    # All displayed data is public. Do not send a repository-scoped PAT.
    request = Request(
        f"https://api.github.com/{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "readme-cards"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def text(x, y, value, title=False):
    color = "#2f80ed" if title else "#434d58"
    size = 18 if title else 13
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}"'
        f' font-weight="{600 if title else 400}">{escape(str(value))}</text>'
    )


def svg(width, height, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
        f' viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">\n'
        f'<title id="title">{escape(title)}</title>\n'
        '<g font-family="Segoe UI, Ubuntu, sans-serif">\n'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}"'
        ' rx="4.5" fill="#fffefe" stroke="#e4e2e2"/>\n'
        + "\n".join(body)
        + "\n</g>\n</svg>\n"
    )


def pin_card(repo):
    lines = textwrap.wrap(repo.get("description") or "", width=47)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:44] + "..."
    body = [text(25, 35, repo["name"], title=True)]
    body.extend(text(25, 62 + 18 * i, line) for i, line in enumerate(lines))
    language = repo.get("language") or "Unknown"
    color = COLORS.get(language, "#858585")
    body.extend([
        f'<circle cx="30" cy="133" r="6" fill="{color}"/>',
        text(42, 137, language),
        text(180, 137, f'Stars: {repo["stargazers_count"]:,}'),
        text(290, 137, f'Forks: {repo["forks_count"]:,}'),
    ])
    return svg(400, 160, f'{repo["full_name"]} repository statistics', body)


def pr_count(owner, merged=False, api=fetch):
    query = f"type:pr author:{owner}" + (" is:merged" if merged else "")
    result = api("search/issues?" + urlencode({"q": query, "per_page": 1}))
    if result.get("incomplete_results", False):
        raise ValueError("GitHub returned incomplete pull request statistics")
    return result["total_count"]


def generate(owner, api=fetch):
    repos = {name: api(f"repos/{owner}/{name}") for name in PROJECTS}
    for name, repo in repos.items():
        if repo["private"] or repo["full_name"].lower() != f"{owner}/{name}".lower():
            raise ValueError(f"Unexpected repository data for {name}")
    total = pr_count(owner, api=api)
    merged = pr_count(owner, merged=True, api=api)
    if not 0 <= merged <= total:
        raise ValueError("Inconsistent pull request statistics")
    percentage = f"{merged / total:.1%}" if total else "N/A"
    stars = sum(repo["stargazers_count"] for repo in repos.values())
    body = [text(25, 35, f"{owner}'s GitHub Stats", title=True)]
    for i, (label, value) in enumerate([
        ("Stars (featured projects)", f"{stars:,}"),
        ("Public pull requests", f"{total:,}"),
        ("Merged pull requests", f"{merged:,}"),
        ("Pull requests merged", percentage),
    ]):
        body.extend([text(25, 65 + 25 * i, label), text(320, 65 + 25 * i, value)])
    # Build all cards before writing: API errors must not overwrite valid SVGs.
    cards = {"stats.svg": svg(450, 165, f"{owner} public GitHub statistics", body)}
    cards.update({PROJECTS[name]: pin_card(repo) for name, repo in repos.items()})
    return cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", type=Path, default=Path("profile"))
    args = parser.parse_args()
    cards = generate(args.owner)
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, content in cards.items():
        temporary = args.output / (filename + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(args.output / filename)


if __name__ == "__main__":
    main()
