#!/usr/bin/env python3
"""Draw a cozy pastel contribution calendar for the profile README.

Reads the public contribution calendar from the GitHub GraphQL API and writes
an SVG that matches the bear banner. Standard library only.

Usage:
    GITHUB_TOKEN=... GH_USER=ngocminh710 python3 cozy_contributions.py [output.svg]

For local testing, set CALENDAR_JSON to a file holding a saved
`contributionCalendar` object and no network call is made.
"""
import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

WIDTH, HEIGHT = 880, 292
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 28, 84, 824, 180
GRID_X, GRID_Y = 86, 120
GRID_RIGHT = 838
CELL = 11


def fetch_calendar(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "cozy-contributions",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    user = payload["data"]["user"]
    if user is None:
        raise SystemExit(f"No GitHub user named {login!r}")
    return user["contributionsCollection"]["contributionCalendar"]


def load_calendar():
    saved = os.environ.get("CALENDAR_JSON")
    if saved:
        with open(saved, encoding="utf-8") as handle:
            return json.load(handle)
    token = os.environ.get("GITHUB_TOKEN")
    login = os.environ.get("GH_USER")
    if not token or not login:
        raise SystemExit("Set GITHUB_TOKEN and GH_USER (or CALENDAR_JSON for a saved calendar).")
    return fetch_calendar(login, token)


def fmt(number):
    return f"{number:.1f}".rstrip("0").rstrip(".")


def month_labels(weeks, pitch):
    """One label per month, placed over the first week that starts in it."""
    starts = []
    previous = None
    for index, week in enumerate(weeks):
        month = date.fromisoformat(week["contributionDays"][0]["date"]).month
        if month != previous:
            starts.append((index, month))
            previous = month
    labels = []
    for position, (index, month) in enumerate(starts):
        following = starts[position + 1][0] if position + 1 < len(starts) else len(weeks) + 2
        if following - index < 2:
            continue  # too cramped to fit a label
        labels.append((GRID_X + index * pitch, MONTHS[month - 1]))
    return labels


def render(calendar):
    weeks = [week for week in calendar["weeks"] if week["contributionDays"]]
    total = calendar["totalContributions"]
    pitch = min(14.1, (GRID_RIGHT - GRID_X) / max(len(weeks), 1))
    noun = "contribution" if total == 1 else "contributions"

    quiet, busy = [], []
    for column, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = (date.fromisoformat(day["date"]).weekday() + 1) % 7  # Sunday on top
            level = LEVELS.get(day["contributionLevel"], 0)
            x, y = fmt(GRID_X + column * pitch), fmt(GRID_Y + row * pitch)
            if level:
                # Real rects (not <use>) so the glow scales around each square's own centre.
                delay = fmt(-0.37 * len(busy))
                busy.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3.2" '
                    f'class="l{level} on" style="animation-delay: {delay}s"/>'
                )
            else:
                quiet.append(f'<use href="#c" x="{x}" y="{y}"/>')
    cells = quiet + busy  # busy days are drawn last so they sit on top while glowing

    months = "\n      ".join(
        f'<text x="{fmt(x)}" y="108">{name}</text>' for x, name in month_labels(weeks, pitch)
    )
    days = "\n      ".join(
        f'<text x="46" y="{fmt(GRID_Y + row * pitch + 9.5)}">{name}</text>'
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )
    legend_x = GRID_RIGHT - 34 - 5 * 15
    legend = "\n      ".join(
        f'<use href="#c" x="{legend_x + level * 15}" y="238"{"" if level == 0 else f" class=\"l{level}\""}/>'
        for level in range(5)
    )
    grid = "\n      ".join(cells)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">{total} {noun} in the last year</title>
  <desc id="desc">A pastel pink contribution calendar with a cartoon bear in mint headphones peeking over the top.</desc>

  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFF6E9"/>
      <stop offset="1" stop-color="#FFE1EC"/>
    </linearGradient>
    <clipPath id="card"><rect width="{WIDTH}" height="{HEIGHT}" rx="28"/></clipPath>
    <rect id="c" width="{CELL}" height="{CELL}" rx="3.2"/>
    <path id="heart" d="M0 -3 C0 -9 -9 -9 -9 -3 C-9 2 -3 5 0 8 C3 5 9 2 9 -3 C9 -9 0 -9 0 -3 Z"/>
    <path id="spark" d="M0 -9 C1 -2.5 2.5 -1 9 0 C2.5 1 1 2.5 0 9 C-1 2.5 -2.5 1 -9 0 C-2.5 -1 -1 -2.5 0 -9 Z"/>
    <g id="paw">
      <ellipse cx="0" cy="4" rx="7" ry="5.6"/>
      <circle cx="-8" cy="-3.5" r="3"/>
      <circle cx="-3" cy="-8.5" r="3.2"/>
      <circle cx="3" cy="-8.5" r="3.2"/>
      <circle cx="8" cy="-3.5" r="3"/>
    </g>
  </defs>

  <style>
    text {{ font-family: ui-rounded, "SF Pro Rounded", "Nunito", "Quicksand", "Varela Round", "Arial Rounded MT Bold", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
    .grid use, .grid rect {{ fill: #F8E8EE; }}
    .grid .l1 {{ fill: #FFC6DA; }}
    .grid .l2 {{ fill: #F99DC0; }}
    .grid .l3 {{ fill: #EC72A3; }}
    .grid .l4 {{ fill: #CF4F86; }}
    .labels text {{ font-size: 11.5px; font-weight: 700; fill: #B58373; }}

    .on {{ transform-box: fill-box; transform-origin: center; animation: glow 2.6s ease-in-out infinite alternate; }}
    @keyframes glow {{ from {{ transform: scale(0.86); }} to {{ transform: scale(1.2); }} }}

    .peek {{ animation: peek 3.6s ease-in-out infinite alternate; }}
    @keyframes peek {{ from {{ transform: translateY(5px); }} to {{ transform: translateY(0); }} }}

    .eye {{ transform-box: fill-box; transform-origin: center; animation: blink 4.8s infinite; }}
    @keyframes blink {{ 0%, 91%, 100% {{ transform: scaleY(1); }} 94.5% {{ transform: scaleY(0.08); }} }}

    .twinkle {{ transform-box: fill-box; transform-origin: center; animation: twinkle 2.8s ease-in-out infinite alternate; }}
    .t2 {{ animation-delay: -1.4s; }}
    @keyframes twinkle {{ from {{ transform: scale(0.55); opacity: 0.45; }} to {{ transform: scale(1.1); opacity: 1; }} }}

    .pulse {{ transform-box: fill-box; transform-origin: center; animation: pulse 1.6s ease-in-out infinite alternate; }}
    @keyframes pulse {{ from {{ transform: scale(0.88); }} to {{ transform: scale(1.12); }} }}

    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
    }}
  </style>

  <g clip-path="url(#card)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#bg)"/>
    <circle cx="24" cy="20" r="74" fill="#FFE8C4" opacity="0.6"/>
    <circle cx="866" cy="284" r="96" fill="#FFD3E2" opacity="0.6"/>
    <g transform="translate(618 40)" fill="#FFC96B"><use href="#spark" class="twinkle"/></g>
    <g transform="translate(852 62) scale(0.7)" fill="#F7A8C4"><use href="#spark" class="twinkle t2"/></g>
    <g transform="translate(676 58) rotate(-12) scale(0.8)" fill="#F7A8C4"><use href="#heart"/></g>

    <g transform="translate(52 48) scale(0.9)" fill="#F58FB5"><use href="#heart" class="pulse"/></g>
    <text x="70" y="57" font-size="25" font-weight="800" fill="#5B3A29">{total} {noun} in the last year</text>

    <!-- bear peeking over the calendar -->
    <g class="peek">
      <g transform="translate(768 64) scale(0.52) translate(-170 -128)">
        <ellipse cx="170" cy="128" rx="74" ry="66" fill="#C98D62"/>
        <path d="M98 134 C98 40 242 40 242 134" fill="none" stroke="#8ED1C0" stroke-width="9" stroke-linecap="round"/>
        <rect x="82" y="110" width="26" height="50" rx="13" fill="#8ED1C0"/>
        <rect x="232" y="110" width="26" height="50" rx="13" fill="#8ED1C0"/>
        <rect x="88" y="120" width="8" height="30" rx="4" fill="#B9E6DA"/>
        <rect x="244" y="120" width="8" height="30" rx="4" fill="#B9E6DA"/>
        <circle cx="118" cy="76" r="25" fill="#C98D62"/>
        <circle cx="222" cy="76" r="25" fill="#C98D62"/>
        <circle cx="118" cy="76" r="13" fill="#F6B3AE"/>
        <circle cx="222" cy="76" r="13" fill="#F6B3AE"/>
        <ellipse cx="123" cy="150" rx="12" ry="8" fill="#F59C9C" opacity="0.6"/>
        <ellipse cx="217" cy="150" rx="12" ry="8" fill="#F59C9C" opacity="0.6"/>
        <ellipse cx="170" cy="153" rx="31" ry="24" fill="#FCEBD7"/>
        <g class="eye">
          <circle cx="141" cy="127" r="7" fill="#4A3024"/>
          <circle cx="143.4" cy="124.4" r="2.4" fill="#FFFFFF"/>
        </g>
        <g class="eye">
          <circle cx="199" cy="127" r="7" fill="#4A3024"/>
          <circle cx="201.4" cy="124.4" r="2.4" fill="#FFFFFF"/>
        </g>
        <ellipse cx="170" cy="142" rx="9.5" ry="7" fill="#4A3024"/>
        <ellipse cx="167.5" cy="140" rx="3" ry="1.8" fill="#FFFFFF" opacity="0.55"/>
        <path d="M170 149 v7 M170 156 q-8 8 -15 0 M170 156 q8 8 15 0" fill="none" stroke="#4A3024" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>

    <rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="20" fill="#FFFFFF" stroke="#F6CFDD" stroke-width="2"/>
    <ellipse cx="735" cy="{PANEL_Y + 1}" rx="10" ry="7" fill="#C98D62"/>
    <ellipse cx="801" cy="{PANEL_Y + 1}" rx="10" ry="7" fill="#C98D62"/>

    <g class="labels">
      {months}
      {days}
      <text x="{legend_x - 8}" y="247.5" text-anchor="end">less</text>
      <text x="{GRID_RIGHT}" y="247.5" text-anchor="end">more</text>
    </g>
    <g class="grid">
      {grid}
      {legend}
    </g>
    <g transform="translate(51 244) scale(0.62)" fill="#F7A8C4"><use href="#paw"/></g>
    <text x="64" y="247.5" font-size="11.5" font-weight="700" fill="#C9A093">one little square per day</text>
  </g>

  <rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="27" fill="none" stroke="#F6CFDD" stroke-width="2"/>
</svg>
"""


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "assets/cozy-contributions.svg"
    svg = render(load_calendar())
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
