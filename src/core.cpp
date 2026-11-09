#include "mwhc.hpp"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <queue>
#include <sstream>
#include <stdexcept>

namespace mwhc {

Hypergraph::Hypergraph(int vertices, std::vector<std::vector<int>> hyperedges)
    : n(vertices) {
    if (n < 1) throw std::invalid_argument("vertex count must be positive");
    for (auto& edge : hyperedges) {
        std::sort(edge.begin(), edge.end());
        edge.erase(std::unique(edge.begin(), edge.end()), edge.end());
        if (edge.size() < 2) throw std::invalid_argument("hyperedge rank must be at least two");
        for (int v : edge)
            if (v < 0 || v >= n) throw std::invalid_argument("vertex id outside [0,n)");
    }
    std::sort(hyperedges.begin(), hyperedges.end());
    hyperedges.erase(std::unique(hyperedges.begin(), hyperedges.end()), hyperedges.end());
    edges = std::move(hyperedges);
    inc.resize(n);
    for (int i = 0; i < static_cast<int>(edges.size()); ++i) {
        rank = std::max(rank, static_cast<int>(edges[i].size()));
        incidence_count += static_cast<long long>(edges[i].size());
        for (int v : edges[i]) inc[v].push_back(i);
    }
}

Hypergraph Hypergraph::read(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read input: " + path);
    std::string line;
    int n = 0, m = 0;
    bool header = false;
    std::vector<std::vector<int>> edges;
    while (std::getline(input, line)) {
        const auto comment = line.find('#');
        if (comment != std::string::npos) line.resize(comment);
        std::istringstream row(line);
        int first;
        if (!(row >> first)) continue;
        if (!header) {
            n = first;
            if (!(row >> m) || n < 1 || m < 0) throw std::runtime_error("expected header: n m");
            header = true;
            continue;
        }
        if (first < 2) throw std::runtime_error("hyperedge cardinality must be at least two");
        std::vector<int> edge(first);
        for (int& v : edge)
            if (!(row >> v)) throw std::runtime_error("truncated hyperedge");
        edges.push_back(std::move(edge));
    }
    if (!header || static_cast<int>(edges.size()) != m)
        throw std::runtime_error("hyperedge count does not match header");
    return Hypergraph(n, std::move(edges));
}

Selection none(const Hypergraph& h) { return Selection(h.n, 0); }
Selection all(const Hypergraph& h) { return Selection(h.n, 1); }
int count(const Selection& s) { return std::accumulate(s.begin(), s.end(), 0); }

bool contains_queries(const Selection& s, const std::vector<int>& q) {
    for (int v : q)
        if (v < 0 || v >= static_cast<int>(s.size()) || !s[v]) return false;
    return true;
}

static bool edge_inside(const std::vector<int>& edge, const Selection& selected) {
    for (int v : edge) if (!selected[v]) return false;
    return true;
}

std::vector<int> bfs(const Hypergraph& h, const Selection& allowed, int source,
                     Stats* stats) {
    if (stats) ++stats->bfs_runs;
    std::vector<int> distance(h.n, INF_DIST);
    if (source < 0 || source >= h.n || !allowed[source]) return distance;
    std::vector<unsigned char> seen_edge(h.edges.size(), 0);
    std::queue<int> queue;
    distance[source] = 0;
    queue.push(source);
    while (!queue.empty()) {
        const int u = queue.front();
        queue.pop();
        for (int edge_id : h.inc[u]) {
            if (seen_edge[edge_id]) continue;
            seen_edge[edge_id] = 1;
            if (!edge_inside(h.edges[edge_id], allowed)) continue;
            for (int v : h.edges[edge_id]) if (distance[v] == INF_DIST) {
                distance[v] = distance[u] + 1;
                queue.push(v);
            }
        }
    }
    return distance;
}

Cost evaluate_wiener(const Hypergraph& h, const Selection& selected,
                     bool* connected, Stats* stats) {
    if (stats) ++stats->evaluations;
    std::vector<int> vertices;
    for (int v = 0; v < h.n; ++v) if (selected[v]) vertices.push_back(v);
    if (vertices.empty()) {
        if (connected) *connected = false;
        return INF_COST;
    }
    Cost cost = 0;
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        const auto distance = bfs(h, selected, vertices[i], nullptr);
        for (std::size_t j = i + 1; j < vertices.size(); ++j) {
            if (distance[vertices[j]] >= INF_DIST) {
                if (connected) *connected = false;
                return INF_COST;
            }
            cost += distance[vertices[j]];
        }
    }
    if (connected) *connected = true;
    return cost;
}

double elapsed(const std::chrono::steady_clock::time_point& start) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

static std::string escape_json(const std::string& value) {
    std::ostringstream out;
    for (char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c == '\n') out << "\\n";
        else out << c;
    }
    return out.str();
}

std::string result_json(const Hypergraph& h, const std::vector<int>& q,
                        const Result& r) {
    std::ostringstream out;
    out << std::setprecision(12)
        << "{\"algorithm\":\"" << escape_json(r.algorithm)
        << "\",\"status\":\"" << escape_json(r.status)
        << "\",\"n\":" << h.n << ",\"m\":" << h.edges.size()
        << ",\"rank\":" << h.rank << ",\"query\":[";
    for (std::size_t i = 0; i < q.size(); ++i) { if (i) out << ','; out << q[i]; }
    out << "],\"feasible\":" << (r.feasible ? "true" : "false")
        << ",\"optimal\":" << (r.optimal ? "true" : "false")
        << ",\"timed_out\":" << (r.timed_out ? "true" : "false")
        << ",\"cost\":";
    if (r.feasible) out << r.cost; else out << "null";
    out << ",\"lower_bound\":" << r.lower_bound
        << ",\"seconds\":" << r.seconds
        << ",\"size\":" << (r.feasible ? count(r.selected) : 0)
        << ",\"selected\":[";
    bool first = true;
    for (int v = 0; v < h.n; ++v) if (r.selected[v]) {
        if (!first) out << ',';
        first = false;
        out << v;
    }
    out << "],\"stats\":{\"evaluations\":" << r.stats.evaluations
        << ",\"bfs_runs\":" << r.stats.bfs_runs;
    for (const auto& [key, value] : r.stats.counters)
        out << ",\"" << escape_json(key) << "\":" << value;
    out << "}}";
    return out.str();
}

} // namespace mwhc
