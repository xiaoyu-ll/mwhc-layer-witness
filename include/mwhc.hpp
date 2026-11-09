#pragma once

#include <chrono>
#include <cstdint>
#include <limits>
#include <map>
#include <string>
#include <vector>

namespace mwhc {

using Cost = long long;
using Selection = std::vector<unsigned char>;
constexpr Cost INF_COST = std::numeric_limits<Cost>::max() / 16;
constexpr int INF_DIST = 100000000;

struct Hypergraph {
    int n = 0;
    int rank = 0;
    long long incidence_count = 0;
    std::vector<std::vector<int>> edges;
    std::vector<std::vector<int>> inc;

    Hypergraph() = default;
    Hypergraph(int vertices, std::vector<std::vector<int>> hyperedges);
    static Hypergraph read(const std::string& path);
};

struct Stats {
    long long evaluations = 0;
    long long bfs_runs = 0;
    std::map<std::string, long long> counters;
};

struct Options {
    double time_limit = 0.0; // <= 0 means unlimited
};

struct Result {
    std::string algorithm;
    std::string status;
    Selection selected;
    Cost cost = INF_COST;
    Cost lower_bound = 0;
    bool feasible = false;
    bool optimal = false;
    bool timed_out = false;
    double approx_factor = 0.0;
    double seconds = 0.0;
    Stats stats;
    std::vector<std::string> notes;
};

Selection none(const Hypergraph& h);
Selection all(const Hypergraph& h);
int count(const Selection& s);
bool contains_queries(const Selection& s, const std::vector<int>& q);
std::vector<int> bfs(const Hypergraph& h, const Selection& allowed, int source,
                     Stats* stats = nullptr);
Cost evaluate_wiener(const Hypergraph& h, const Selection& selected,
                     bool* connected = nullptr, Stats* stats = nullptr);
double elapsed(const std::chrono::steady_clock::time_point& start);
std::string result_json(const Hypergraph& h, const std::vector<int>& q,
                        const Result& result);

Result solve_allrootpath(const Hypergraph& h, const std::vector<int>& queries,
                         const Options& options = {});
Result solve_medoidpath(const Hypergraph& h, const std::vector<int>& queries,
                        const Options& options = {});
Result solve_fastpath(const Hypergraph& h, const std::vector<int>& queries,
                      const Options& options = {});

} // namespace mwhc
