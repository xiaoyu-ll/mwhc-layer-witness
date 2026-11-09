#include "mwhc.hpp"

#include <algorithm>
#include <cmath>
#include <queue>
#include <stdexcept>
#include <tuple>

namespace mwhc {
namespace {

struct Budget {
    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    double limit;
    explicit Budget(double seconds) : limit(seconds) {}
    bool expired() const { return limit > 0 && elapsed(start) >= limit; }
};

std::vector<int> normalize_queries(const Hypergraph& h, std::vector<int> q) {
    for (int v : q)
        if (v < 0 || v >= h.n) throw std::invalid_argument("query vertex out of range");
    std::sort(q.begin(), q.end());
    q.erase(std::unique(q.begin(), q.end()), q.end());
    if (q.empty()) throw std::invalid_argument("at least one query vertex is required");
    return q;
}

struct Seed {
    Selection selected;
    Selection component;
    std::vector<int> distance;
    int raw_size = 0;
    Cost radial_upper_sum = 0;
    bool feasible = false;
};

// Incidence BFS realizes the member-to-member hop metric without constructing
// the clique expansion. Complete witness hyperedges preserve every traced hop.
Seed layer_witness_seed(const Hypergraph& h, const std::vector<int>& rooted_q,
                        Stats& stats) {
    Seed out;
    out.selected = none(h);
    out.component = none(h);
    out.distance = bfs(h, all(h), rooted_q.front(), &stats);
    for (int v = 0; v < h.n; ++v) out.component[v] = out.distance[v] < INF_DIST;
    for (int v : rooted_q) if (!out.component[v]) return out;

    std::vector<int> parent_vertex(h.n, -1), parent_edge(h.n, -1);
    for (int edge_id = 0; edge_id < static_cast<int>(h.edges.size()); ++edge_id) {
        const auto& edge = h.edges[edge_id];
        int min_distance = INF_DIST, parent = -1;
        for (int u : edge) if (out.distance[u] < min_distance) {
            min_distance = out.distance[u];
            parent = u;
        }
        if (min_distance >= INF_DIST) continue;
        for (int v : edge) if (out.distance[v] == min_distance + 1) {
            const int old = parent_edge[v];
            if (old < 0 || edge.size() < h.edges[old].size() ||
                (edge.size() == h.edges[old].size() && edge_id < old)) {
                parent_edge[v] = edge_id;
                parent_vertex[v] = parent;
            }
        }
    }

    Selection raw = none(h);
    raw[rooted_q.front()] = out.selected[rooted_q.front()] = 1;
    std::vector<int> activation_depth(h.n, INF_DIST);
    activation_depth[rooted_q.front()] = 0;
    std::vector<unsigned char> chosen_edge(h.edges.size(), 0);
    for (int terminal : rooted_q) {
        int v = terminal, steps = 0;
        while (v != rooted_q.front()) {
            raw[v] = 1;
            const int edge_id = parent_edge[v], parent = parent_vertex[v];
            if (edge_id < 0 || parent < 0 || ++steps > h.n)
                throw std::logic_error("invalid incidence predecessor chain");
            if (!chosen_edge[edge_id]) {
                chosen_edge[edge_id] = 1;
                for (int u : h.edges[edge_id]) {
                    out.selected[u] = 1;
                    activation_depth[u] = std::min(activation_depth[u], out.distance[v]);
                }
            }
            v = parent;
        }
    }
    out.raw_size = count(raw);
    for (int v = 0; v < h.n; ++v) if (out.selected[v]) {
        if (activation_depth[v] >= INF_DIST)
            throw std::logic_error("selected member has no rooted activation path");
        out.radial_upper_sum += activation_depth[v];
    }
    out.feasible = true;
    return out;
}

void install_seed(const Hypergraph& h, const std::vector<int>& q,
                  const Seed& seed, Result& result) {
    if (!seed.feasible) {
        result.selected = none(h);
        result.status = "infeasible";
        return;
    }
    bool connected = false;
    const Cost cost = evaluate_wiener(h, seed.selected, &connected, &result.stats);
    if (!connected || !contains_queries(seed.selected, q))
        throw std::logic_error("layer-witness completion is not a connector");
    result.selected = seed.selected;
    result.cost = cost;
    result.feasible = true;
    result.stats.counters["seed_raw_size"] = seed.raw_size;
    result.stats.counters["seed_completed_size"] = count(seed.selected);
    const Cost k = static_cast<Cost>(q.size());
    result.lower_bound = (k - 1) * (k - 2) / 2;
    for (int v : q) result.lower_bound += seed.distance[v];
}

std::vector<int> rooted(const std::vector<int>& q, int root) {
    std::vector<int> order;
    order.reserve(q.size());
    order.push_back(root);
    for (int v : q) if (v != root) order.push_back(v);
    return order;
}

void finish(Result& result, const Budget& budget) {
    result.timed_out = budget.expired();
    result.status = result.timed_out ? "timed_out_feasible" : "heuristic";
    if (result.feasible && !result.timed_out && result.cost == result.lower_bound) {
        result.optimal = true;
        result.status = "optimal";
    }
    if (result.feasible && result.lower_bound > 0)
        result.approx_factor = static_cast<double>(result.cost) / result.lower_bound;
    result.seconds = elapsed(budget.start);
}

} // namespace

Result solve_allrootpath(const Hypergraph& h, const std::vector<int>& queries,
                         const Options& options) {
    Budget budget(options.time_limit);
    Result result;
    result.algorithm = "allrootpath";
    const auto q = normalize_queries(h, queries);
    for (int root : q) {
        if (result.feasible && budget.expired()) break;
        Result candidate;
        const Seed seed = layer_witness_seed(h, rooted(q, root), candidate.stats);
        install_seed(h, q, seed, candidate);
        result.stats.evaluations += candidate.stats.evaluations;
        result.stats.bfs_runs += candidate.stats.bfs_runs;
        for (const auto& [name, value] : candidate.stats.counters)
            result.stats.counters[name] += value;
        if (!candidate.feasible) {
            result.status = "infeasible";
            result.seconds = elapsed(budget.start);
            return result;
        }
        result.lower_bound = std::max(result.lower_bound, candidate.lower_bound);
        if (!result.feasible || candidate.cost < result.cost ||
            (candidate.cost == result.cost && count(candidate.selected) < count(result.selected))) {
            result.feasible = true;
            result.cost = candidate.cost;
            result.selected = std::move(candidate.selected);
            result.stats.counters["best_root"] = root;
        }
        ++result.stats.counters["completed_roots"];
    }
    finish(result, budget);
    return result;
}

Result solve_medoidpath(const Hypergraph& h, const std::vector<int>& queries,
                        const Options& options) {
    Budget budget(options.time_limit);
    Result result;
    result.algorithm = "medoidpath";
    const auto q = normalize_queries(h, queries);
    Seed best;
    Cost best_radial = INF_COST, global_lower_bound = 0;
    int best_root = -1;
    for (int root : q) {
        if (best.feasible && budget.expired()) break;
        const Seed seed = layer_witness_seed(h, rooted(q, root), result.stats);
        if (!seed.feasible) {
            result.status = "infeasible";
            result.seconds = elapsed(budget.start);
            return result;
        }
        Cost radial = 0;
        for (int v : q) radial += seed.distance[v];
        const Cost k = static_cast<Cost>(q.size());
        global_lower_bound = std::max(global_lower_bound,
                                      radial + (k - 1) * (k - 2) / 2);
        if (!best.feasible || radial < best_radial ||
            (radial == best_radial && count(seed.selected) < count(best.selected)) ||
            (radial == best_radial && count(seed.selected) == count(best.selected) && root < best_root)) {
            best = seed;
            best_radial = radial;
            best_root = root;
        }
        ++result.stats.counters["roots_scanned"];
    }
    if (!best.feasible) {
        result.status = "timed_out_no_incumbent";
        result.timed_out = true;
        result.seconds = elapsed(budget.start);
        return result;
    }
    install_seed(h, q, best, result);
    result.lower_bound = global_lower_bound;
    result.stats.counters["medoid_root"] = best_root;
    finish(result, budget);
    return result;
}

Result solve_fastpath(const Hypergraph& h, const std::vector<int>& queries,
                      const Options& options) {
    const auto q = normalize_queries(h, queries);
    if (q.size() <= 2) {
        Result direct = solve_medoidpath(h, q, options);
        direct.algorithm = "fastpath";
        return direct;
    }
    Budget budget(options.time_limit);
    Result result;
    result.algorithm = "fastpath";

    const Seed anchor_seed = layer_witness_seed(h, rooted(q, q.front()), result.stats);
    const auto& anchor_distance = anchor_seed.distance;
    int far = q.front();
    for (int v : q) {
        if (anchor_distance[v] >= INF_DIST) {
            result.status = "infeasible";
            result.seconds = elapsed(budget.start);
            return result;
        }
        if (anchor_distance[v] > anchor_distance[far] ||
            (anchor_distance[v] == anchor_distance[far] && v < far)) far = v;
    }
    const Seed far_seed = layer_witness_seed(h, rooted(q, far), result.stats);
    const auto& far_distance = far_seed.distance;
    int center = -1;
    std::tuple<int, int, int> center_score{INF_DIST, INF_DIST, INF_DIST};
    for (int v : q) {
        const auto score = std::make_tuple(std::max(anchor_distance[v], far_distance[v]),
                                           anchor_distance[v] + far_distance[v], v);
        if (score < center_score) { center_score = score; center = v; }
    }

    const Cost k = static_cast<Cost>(q.size());
    Cost radial_anchor = 0, radial_far = 0;
    for (int v : q) {
        radial_anchor += anchor_distance[v];
        radial_far += far_distance[v];
    }
    Cost global_lower_bound = std::max(radial_anchor, radial_far)
                            + (k - 1) * (k - 2) / 2;
    Cost landmark_lower_bound = 0;
    for (std::size_t i = 0; i < q.size(); ++i)
        for (std::size_t j = i + 1; j < q.size(); ++j)
            landmark_lower_bound += std::max({1,
                std::abs(anchor_distance[q[i]] - anchor_distance[q[j]]),
                std::abs(far_distance[q[i]] - far_distance[q[j]])});
    global_lower_bound = std::max(global_lower_bound, landmark_lower_bound);

    std::vector<std::pair<int, Seed>> candidates;
    candidates.push_back({q.front(), anchor_seed});
    if (far != q.front()) candidates.push_back({far, far_seed});
    if (center != q.front() && center != far)
        candidates.push_back({center, layer_witness_seed(h, rooted(q, center), result.stats)});

    int best_root = -1;
    Cost best_bound = INF_COST;
    Seed best_seed;
    for (const auto& [root, seed] : candidates) {
        const Cost bound = static_cast<Cost>(count(seed.selected) - 1)
                         * seed.radial_upper_sum;
        if (bound < best_bound ||
            (bound == best_bound && count(seed.selected) < count(best_seed.selected)) ||
            (bound == best_bound && count(seed.selected) == count(best_seed.selected) && root < best_root)) {
            best_bound = bound;
            best_seed = seed;
            best_root = root;
        }
    }
    install_seed(h, q, best_seed, result);
    result.lower_bound = std::max(result.lower_bound, global_lower_bound);
    result.stats.counters["far_pivot"] = far;
    result.stats.counters["center_pivot"] = center;
    result.stats.counters["selected_root"] = best_root;
    result.stats.counters["candidate_count"] = candidates.size();
    finish(result, budget);
    return result;
}

} // namespace mwhc
