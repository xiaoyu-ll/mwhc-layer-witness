#!/usr/bin/env python3
"""Render the Gephi-positioned Davis hypergraph community case study."""

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse

from build_davis_community_case_gexf import (
    COMMUNITY_A, COMMUNITY_B, QUERY, SELECTED, event_labels, read_edges,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "case_studies/output/davis_community_case"
COLORS = {"A": "#0072B2", "B": "#E69F00"}


def short_name(full):
    first, *middle, last = full.split()
    return f"{first[0]}. {last}"


def main():
    mapping = json.loads((ROOT / "case_studies/data/davis_southern_women_mapping.json").read_text())
    names = {row["id"]: short_name(row["name"]) for row in mapping["nodes"]}
    positions = json.loads((ROOT / "case_studies/output/davis_community_positions.json").read_text())
    edges = read_edges()
    labels = event_labels()
    active = {edge_id for edge_id, members in enumerate(edges) if set(members) <= SELECTED}

    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 6.1,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "figure.facecolor": "white", "axes.facecolor": "white",
    })
    fig, ax = plt.subplots(figsize=(3.5, 1.68))

    # Soft community regions summarize the weighted 2-section modularity split;
    # every actual relationship is still drawn as a member--event incidence.
    for community, title in ((COMMUNITY_A, "Community A"), (COMMUNITY_B, "Community B")):
        key = "A" if community is COMMUNITY_A else "B"
        xs = [positions[f"p{v}"][0] for v in community]
        ys = [positions[f"p{v}"][1] for v in community]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        width, height = (max(xs) - min(xs)) * 1.38, (max(ys) - min(ys)) * 1.42
        ax.add_patch(Ellipse((cx, cy), width, height, facecolor=COLORS[key],
                             edgecolor=COLORS[key], alpha=0.075, linewidth=0.8,
                             linestyle=(0, (3, 2)), zorder=0))
        ax.text(cx, cy + height / 2 - 8, title, ha="center", va="top",
                color=COLORS[key], fontsize=6.0, fontweight="bold", zorder=1)

    # Inactive incidences are context; active complete-hyperedge incidences are
    # the dark backbone returned by FastPath.
    for edge_id, members in enumerate(edges):
        ex, ey = positions[f"e{edge_id}"]
        for vertex in members:
            x, y = positions[f"p{vertex}"]
            is_active = edge_id in active and vertex in SELECTED
            ax.plot([x, ex], [y, ey], color="#4F4F4F" if is_active else "#C8C8C8",
                    linewidth=1.0 if is_active else 0.35,
                    alpha=0.85 if is_active else 0.24, zorder=2 if is_active else 1)

    for edge_id in range(len(edges)):
        x, y = positions[f"e{edge_id}"]
        is_active = edge_id in active
        ax.scatter(x, y, s=31 if is_active else 12, marker="s",
                   c="#4D4D4D" if is_active else "#BDBDBD",
                   edgecolors="white", linewidths=0.45,
                   alpha=1.0 if is_active else 0.38, zorder=5 if is_active else 3)
        # Event identifiers are described in the artifact; suppressing them in
        # the compact paper rendering prevents label collisions at final size.

    for vertex in range(18):
        x, y = positions[f"p{vertex}"]
        community = "A" if vertex in COMMUNITY_A else "B"
        selected = vertex in SELECTED
        query = vertex in QUERY
        size = 84 if query else 45 if selected else 25
        ax.scatter(x, y, s=size, marker="o", c=COLORS[community],
                   edgecolors="black" if query else "white",
                   linewidths=1.0 if query else 0.55,
                   alpha=1.0 if selected else 0.22, zorder=7 if query else 6)
        if query:
            ax.scatter(x, y, s=size + 35, marker="o", facecolors="none",
                       edgecolors=COLORS[community], linewidths=0.8, zorder=6)

    handles = [
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=COLORS["A"],
               markeredgecolor="white", markersize=5.8, label="Comm. A"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=COLORS["B"],
               markeredgecolor="white", markersize=5.8, label="Comm. B"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
               markeredgecolor="black", markersize=6.0, label="Query"),
        Line2D([], [], marker="s", linestyle="none", markerfacecolor="#4D4D4D",
               markeredgecolor="white", markersize=5.5, label="Active event"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.985),
               ncol=4, frameon=False, fontsize=7.4, handletextpad=0.28,
               columnspacing=1.0, handlelength=0.8, borderaxespad=0.0)
    xs = [value[0] for value in positions.values()]
    ys = [value[1] for value in positions.values()]
    ax.set_xlim(min(xs) - 75, max(xs) + 75)
    ax.set_ylim(min(ys) - 80, max(ys) + 85)
    ax.axis("off")
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.04, top=0.91)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    for suffix, dpi in ((".pdf", None), (".svg", None), (".png", 400)):
        fig.savefig(OUT.with_suffix(suffix), dpi=dpi, facecolor="white")
    fig.savefig(OUT.with_name(OUT.name + "_preview").with_suffix(".png"),
                dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
