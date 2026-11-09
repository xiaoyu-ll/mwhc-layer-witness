# Layer-Witness Algorithms for Hypergraph Connectors

This repository contains the three algorithms introduced in our work:

- **AllRootPath** enumerates every query vertex as a layer-witness root and evaluates every completed candidate under the native hypergraph Wiener objective.
- **MedoidPath** selects a query 1-median from all rooted distance sums and performs one native objective evaluation.
- **FastPath** constructs at most three candidates from an anchor, a far pivot, and a two-pivot center; it selects one using a rooted Wiener upper bound and evaluates it once.

The implementation traverses the hypergraph incidence structure directly. It does not materialize a clique expansion. A selected hyperedge is activated only when all of its members are selected.

## Build and run

```bash
make
./bin/mwhc --input tests/tiny.hgr --query 0,3,5 --algo fastpath
make test
```

Input files use the following format:

```text
number_of_vertices number_of_hyperedges
edge_cardinality vertex_1 vertex_2 ...
```

Vertex identifiers are zero based. Use `--time-limit 0` for an unlimited run.

## Case studies

The `case_studies/` directory contains the code and source data for the Enron email incidence-backbone example and the Davis Southern Women community example. Generate Gephi files with:

```bash
python3 -m pip install -r requirements.txt
make case-studies
```

The generated GEXF files are written to `case_studies/output/`. The rendering scripts additionally produce PDF, SVG, and PNG versions.

## Repository scope

Only the three proposed algorithms, their common hypergraph primitives, smoke tests, and the two case-study programs are included. Experimental runners, competing methods, paper sources, and result logs are intentionally excluded.
