#!/usr/bin/env python3
"""Build the Gephi input for the Enron FastPath case study.

The drawing is an incidence (factor) graph, not a clique expansion: person
nodes connect to message nodes, and each message node represents one original
email hyperedge.  The five messages form a witness backbone for the 13-member
FastPath answer to the frozen query email_enron_k3_01.
"""

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace


ROOT = Path(__file__).resolve().parents[1]
GEXF_NS = "http://gexf.net/1.3"
VIZ_NS = "http://gexf.net/1.3/viz"
register_namespace("", GEXF_NS)
register_namespace("viz", VIZ_NS)

QUERY = {21, 58, 142}
SELECTED = {7, 21, 41, 58, 66, 81, 118, 120, 130, 136, 140, 142, 143}
# Zero-based edge IDs in the normalized .hgr file.  Together they preserve
# all three query-pair distances of the complete 13-member FastPath answer.
WITNESS_EDGES = [315, 333, 531, 1447, 1454]

POSITIONS = {
    21: (-320, 0),      # Craig Dean (query)
    58: (320, 190),     # Kam Keiser (query)
    142: (320, -190),   # Jason Williams (query)
    130: (-20, 0),      # Kate Symes
    140: (105, 120),    # Stacey White
    7: (220, 115),      # Sally Beck
    136: (105, -120),   # Kim Ward
    41: (-260, 125), 66: (-215, 205), 118: (-335, 205),
    120: (-405, 115), 81: (-405, -115), 143: (-260, -125),
}
MESSAGE_POSITIONS = {
    531: (-175, 0),
    315: (165, 155),
    333: (275, 0),
    1447: (45, -65),
    1454: (205, -155),
}


def read_edges():
    edges = {}
    lines = (ROOT / "case_studies/data/email_enron.hgr").read_text().splitlines()[1:]
    for edge_id, line in enumerate(lines):
        values = [int(value) for value in line.split()]
        assert values[0] == len(values) - 1
        edges[edge_id] = values[1:]
    return edges


def main():
    mapping = json.loads((ROOT / "case_studies/data/email_enron_mapping.json").read_text())
    names = {row["id"]: row["name"].split("@")[0].replace(".", " ").title()
             for row in mapping["nodes"]}
    edges = read_edges()
    witness_members = set().union(*(set(edges[e]) for e in WITNESS_EDGES))
    assert witness_members == SELECTED

    root = Element(f"{{{GEXF_NS}}}gexf", version="1.3")
    meta = SubElement(root, f"{{{GEXF_NS}}}meta", lastmodifieddate="2026-11-05")
    SubElement(meta, f"{{{GEXF_NS}}}creator").text = "MWHC reproducibility artifact"
    SubElement(meta, f"{{{GEXF_NS}}}description").text = (
        "Enron email incidence backbone for email_enron_k3_01; "
        "FastPath size=13, Wiener cost=141."
    )
    graph = SubElement(root, f"{{{GEXF_NS}}}graph", mode="static", defaultedgetype="undirected")
    attrs = SubElement(graph, f"{{{GEXF_NS}}}attributes", **{"class": "node"})
    SubElement(attrs, f"{{{GEXF_NS}}}attribute", id="0", title="kind", type="string")
    SubElement(attrs, f"{{{GEXF_NS}}}attribute", id="1", title="role", type="string")
    nodes = SubElement(graph, f"{{{GEXF_NS}}}nodes")

    colors = {
        "query": (213, 94, 0),
        "bridge": (0, 158, 115),
        "member": (86, 180, 233),
        "message": (110, 110, 110),
    }
    bridges = {7, 81, 130, 136}
    for vertex in sorted(SELECTED):
        role = "query" if vertex in QUERY else "bridge" if vertex in bridges else "member"
        node = SubElement(nodes, f"{{{GEXF_NS}}}node", id=f"p{vertex}", label=names[vertex])
        values = SubElement(node, f"{{{GEXF_NS}}}attvalues")
        SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": "0", "value": "person"})
        SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": "1", "value": role})
        r, g, b = colors[role]
        SubElement(node, f"{{{VIZ_NS}}}color", r=str(r), g=str(g), b=str(b))
        SubElement(node, f"{{{VIZ_NS}}}size", value="30" if role == "query" else "20" if role == "bridge" else "13")
        x, y = POSITIONS[vertex]
        SubElement(node, f"{{{VIZ_NS}}}position", x=str(x), y=str(y), z="0")

    message_labels = {
        315: "Email A (Sally, Kam, Stacey)",
        333: "Email B (Sally, Jason)",
        531: "Email C (Craig's 8-person group)",
        1447: "Email D (Kate, Kim)",
        1454: "Email E (Kim, Jason)",
    }
    for edge_id in WITNESS_EDGES:
        node = SubElement(nodes, f"{{{GEXF_NS}}}node", id=f"e{edge_id}", label=message_labels[edge_id])
        values = SubElement(node, f"{{{GEXF_NS}}}attvalues")
        SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": "0", "value": "message"})
        SubElement(values, f"{{{GEXF_NS}}}attvalue", **{"for": "1", "value": "witness"})
        r, g, b = colors["message"]
        SubElement(node, f"{{{VIZ_NS}}}color", r=str(r), g=str(g), b=str(b))
        SubElement(node, f"{{{VIZ_NS}}}size", value="8")
        x, y = MESSAGE_POSITIONS[edge_id]
        SubElement(node, f"{{{VIZ_NS}}}position", x=str(x), y=str(y), z="0")

    graph_edges = SubElement(graph, f"{{{GEXF_NS}}}edges")
    serial = 0
    for edge_id in WITNESS_EDGES:
        for vertex in edges[edge_id]:
            SubElement(graph_edges, f"{{{GEXF_NS}}}edge", id=str(serial),
                       source=f"p{vertex}", target=f"e{edge_id}", weight="1")
            serial += 1

    output_dir = ROOT / "case_studies/output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "enron_fastpath_backbone.gexf"
    ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    print(output)


if __name__ == "__main__":
    main()
