#!/usr/bin/env python3
"""Render the Gephi-positioned Enron incidence backbone for the paper."""

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from build_enron_case_study_gexf import (
    MESSAGE_POSITIONS, POSITIONS, QUERY, SELECTED, WITNESS_EDGES, read_edges,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "case_studies/output/enron_fastpath_case"
BRIDGES = {7, 130, 136, 140}
COLORS = {
    "query": "#D55E00",
    "bridge": "#009E73",
    "member": "#56B4E9",
    "message": "#666666",
}


def short_name(full):
    parts = full.split("@")[0].split(".")
    return f"{parts[0][0].upper()}. {parts[-1].title()}"


def main():
    mapping = json.loads((ROOT / "case_studies/data/email_enron_mapping.json").read_text())
    names = {row["id"]: short_name(row["name"]) for row in mapping["nodes"]}
    edges = read_edges()

    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 6.2,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "figure.facecolor": "white", "axes.facecolor": "white",
    })
    fig, ax = plt.subplots(figsize=(3.5, 1.68))

    # Original email incidences.  No clique-expanded person-person edges appear.
    for edge_id in WITNESS_EDGES:
        ex, ey = MESSAGE_POSITIONS[edge_id]
        for vertex in edges[edge_id]:
            x, y = POSITIONS[vertex]
            ax.plot([x, ex], [y, ey], color="#B8B8B8", linewidth=0.75,
                    solid_capstyle="round", zorder=1)

    for vertex in sorted(SELECTED):
        x, y = POSITIONS[vertex]
        role = "query" if vertex in QUERY else "bridge" if vertex in BRIDGES else "member"
        size = 92 if role == "query" else 58 if role == "bridge" else 34
        ax.scatter(x, y, s=size, marker="o", c=COLORS[role],
                   edgecolors="black" if role == "query" else "white",
                   linewidths=1.0 if role == "query" else 0.6, zorder=4)
        if role == "query":
            ax.scatter(x, y, s=size + 38, marker="o", facecolors="none",
                       edgecolors=COLORS[role], linewidths=0.8, zorder=3)
        # Peripheral members of Email C remain visible as nodes, but suppressing
        # their labels keeps the single-column rendering legible.
        if role in {"query", "bridge"}:
            dx = -6 if vertex in QUERY else 6
            ha = "right" if dx < 0 else "left"
            dy = 9
            va = "bottom" if dy > 0 else "top"
            weight = "bold" if role == "query" else "normal"
            ax.annotate(names[vertex], (x, y), xytext=(dx, dy),
                        textcoords="offset points", ha=ha, va=va,
                        fontsize=5.6, fontweight=weight, color="#202020", zorder=6)

    message_letters = {531: "C", 315: "A", 333: "B", 1447: "D", 1454: "E"}
    for edge_id in WITNESS_EDGES:
        x, y = MESSAGE_POSITIONS[edge_id]
        ax.scatter(x, y, s=30, marker="s", c=COLORS["message"],
                   edgecolors="white", linewidths=0.5, zorder=5)
        ax.text(x, y, message_letters[edge_id], ha="center", va="center",
                color="white", fontsize=4.8, fontweight="bold", zorder=6)

    ax.annotate("Email C: Craig's 8-person group", MESSAGE_POSITIONS[531],
                xytext=(-8, -18), textcoords="offset points", ha="center",
                va="top", fontsize=5.0, color="#444444")

    handles = [
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=COLORS["query"],
               markeredgecolor="black", markersize=5.8, label="Query"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=COLORS["bridge"],
               markeredgecolor="white", markersize=5.8, label="Bridge"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=COLORS["member"],
               markeredgecolor="white", markersize=5.8, label="Member"),
        Line2D([], [], marker="s", linestyle="none", markerfacecolor=COLORS["message"],
               markeredgecolor="white", markersize=5.5, label="Hyperedge"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.985),
               ncol=4, frameon=False, fontsize=7.4, handletextpad=0.28,
               columnspacing=1.0, handlelength=0.8, borderaxespad=0.0)
    ax.set_xlim(-470, 395)
    ax.set_ylim(-225, 255)
    ax.set_aspect("auto")
    ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.90)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    for suffix, dpi in ((".pdf", None), (".svg", None), (".png", 400)):
        fig.savefig(OUT.with_suffix(suffix), dpi=dpi, facecolor="white")
    fig.savefig(OUT.with_name(OUT.name + "_preview").with_suffix(".png"),
                dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
