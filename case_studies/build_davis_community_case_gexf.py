#!/usr/bin/env python3
"""Build a Gephi-ready community case study from Davis Southern Women."""

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
GEXF_NS = "http://gexf.net/1.3"
VIZ_NS = "http://gexf.net/1.3/viz"
register_namespace("", GEXF_NS)
register_namespace("viz", VIZ_NS)

QUERY = {2, 9, 11, 12, 13}
SELECTED = {1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14}
COMMUNITY_A = {0, 1, 2, 3, 4, 5, 6, 8}
COMMUNITY_B = set(range(18)) - COMMUNITY_A


def read_edges():
    lines = (ROOT / "case_studies/data/davis_southern_women.hgr").read_text().splitlines()[1:]
    edges = []
    for line in lines:
        values = [int(value) for value in line.split()]
        assert values[0] == len(values) - 1
        edges.append(values[1:])
    return edges


def event_labels():
    mapping = json.loads((ROOT / "case_studies/data/davis_southern_women_mapping.json").read_text())
    reverse = {}
    for source, edge in mapping["source_edge_to_hgr_edge"].items():
        reverse.setdefault(edge, []).append(source)
    return {edge: "/".join(labels) for edge, labels in reverse.items()}


def layout(edges):
    graph = nx.Graph()
    for vertex in range(18):
        graph.add_node(f"p{vertex}")
    for edge_id, members in enumerate(edges):
        graph.add_node(f"e{edge_id}")
        graph.add_edges_from((f"p{vertex}", f"e{edge_id}") for vertex in members)
    initial = {}
    for vertex in range(18):
        side = -1.0 if vertex in COMMUNITY_A else 1.0
        initial[f"p{vertex}"] = (side, (vertex % 10 - 4.5) / 5.0)
    for edge_id, members in enumerate(edges):
        x = sum(-1.0 if vertex in COMMUNITY_A else 1.0 for vertex in members) / len(members)
        initial[f"e{edge_id}"] = (x * 0.65, ((edge_id * 7) % 13 - 6) / 8.0)
    positions = nx.spring_layout(graph, pos=initial, seed=20261106,
                                 iterations=700, k=0.48, weight=None)
    # Stretch horizontally to emphasize the two communities.
    return {node: (float(x) * 430, float(y) * 330)
            for node, (x, y) in positions.items()}


def main():
    mapping = json.loads((ROOT / "case_studies/data/davis_southern_women_mapping.json").read_text())
    names = {row["id"]: row["name"] for row in mapping["nodes"]}
    edges = read_edges()
    labels = event_labels()
    positions = layout(edges)
    active = {edge_id for edge_id, members in enumerate(edges) if set(members) <= SELECTED}
    assert active == {8, 9, 10, 11}

    root = Element(f"{{{GEXF_NS}}}gexf", version="1.3")
    meta = SubElement(root, f"{{{GEXF_NS}}}meta", lastmodifieddate="2026-11-06")
    SubElement(meta, f"{{{GEXF_NS}}}creator").text = "MWHC reproducibility artifact"
    SubElement(meta, f"{{{GEXF_NS}}}description").text = (
        "Davis two-community incidence network for davis_southern_women_k5_03; "
        "FastPath size=12, Wiener cost=78."
    )
    graph = SubElement(root, f"{{{GEXF_NS}}}graph", mode="static", defaultedgetype="undirected")
    attrs = SubElement(graph, f"{{{GEXF_NS}}}attributes", **{"class": "node"})
    for attr_id, title, kind in (("0", "kind", "string"), ("1", "role", "string"),
                                 ("2", "community", "string"), ("3", "active", "boolean")):
        SubElement(attrs, f"{{{GEXF_NS}}}attribute", id=attr_id, title=title, type=kind)
    nodes = SubElement(graph, f"{{{GEXF_NS}}}nodes")

    palette = {"A": (0, 114, 178), "B": (230, 159, 0)}
    for vertex in range(18):
        community = "A" if vertex in COMMUNITY_A else "B"
        role = "query" if vertex in QUERY else "selected" if vertex in SELECTED else "excluded"
        node = SubElement(nodes, f"{{{GEXF_NS}}}node", id=f"p{vertex}", label=names[vertex])
        values = SubElement(node, f"{{{GEXF_NS}}}attvalues")
        for key, value in (("0", "person"), ("1", role), ("2", community),
                           ("3", str(vertex in SELECTED).lower())):
            SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": key, "value": value})
        r, g, b = palette[community]
        alpha = "1.0" if vertex in SELECTED else "0.22"
        SubElement(node, f"{{{VIZ_NS}}}color", r=str(r), g=str(g), b=str(b), a=alpha)
        SubElement(node, f"{{{VIZ_NS}}}size", value="28" if role == "query" else "17" if role == "selected" else "10")
        x, y = positions[f"p{vertex}"]
        SubElement(node, f"{{{VIZ_NS}}}position", x=str(x), y=str(y), z="0")

    for edge_id, members in enumerate(edges):
        is_active = edge_id in active
        node = SubElement(nodes, f"{{{GEXF_NS}}}node", id=f"e{edge_id}", label=labels[edge_id])
        values = SubElement(node, f"{{{GEXF_NS}}}attvalues")
        for key, value in (("0", "event"), ("1", "active" if is_active else "inactive"),
                           ("2", "mixed"), ("3", str(is_active).lower())):
            SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": key, "value": value})
        shade = 65 if is_active else 185
        SubElement(node, f"{{{VIZ_NS}}}color", r=str(shade), g=str(shade), b=str(shade),
                   a="1.0" if is_active else "0.28")
        SubElement(node, f"{{{VIZ_NS}}}size", value="11" if is_active else "6")
        x, y = positions[f"e{edge_id}"]
        SubElement(node, f"{{{VIZ_NS}}}position", x=str(x), y=str(y), z="0")

    graph_edges = SubElement(graph, f"{{{GEXF_NS}}}edges")
    serial = 0
    for edge_id, members in enumerate(edges):
        for vertex in members:
            is_active_incidence = edge_id in active and vertex in SELECTED
            edge = SubElement(graph_edges, f"{{{GEXF_NS}}}edge", id=str(serial),
                              source=f"p{vertex}", target=f"e{edge_id}", weight="2" if is_active_incidence else "1")
            SubElement(edge, f"{{{VIZ_NS}}}color", r="70" if is_active_incidence else "190",
                       g="70" if is_active_incidence else "190",
                       b="70" if is_active_incidence else "190",
                       a="0.85" if is_active_incidence else "0.18")
            serial += 1

    out = ROOT / "case_studies/output/davis_community_fastpath.gexf"
    out.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    (out.parent / "davis_community_positions.json").write_text(
        json.dumps({node: [x, y] for node, (x, y) in positions.items()}, indent=2) + "\n"
    )
    print(out)


if __name__ == "__main__":
    main()
