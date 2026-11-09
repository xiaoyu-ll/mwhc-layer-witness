#include "mwhc.hpp"

#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {

std::vector<int> parse_query(const std::string& value) {
    std::vector<int> query;
    std::stringstream input(value);
    std::string token;
    while (std::getline(input, token, ',')) query.push_back(std::stoi(token));
    return query;
}

void usage(const char* program) {
    std::cerr << "Usage: " << program
              << " --input graph.hgr --query v1,v2,..."
                 " --algo allrootpath|medoidpath|fastpath [--time-limit seconds]\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::string input, algorithm;
        std::vector<int> query;
        mwhc::Options options;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--input" && i + 1 < argc) input = argv[++i];
            else if (arg == "--query" && i + 1 < argc) query = parse_query(argv[++i]);
            else if (arg == "--algo" && i + 1 < argc) algorithm = argv[++i];
            else if (arg == "--time-limit" && i + 1 < argc) options.time_limit = std::stod(argv[++i]);
            else { usage(argv[0]); return 2; }
        }
        if (input.empty() || query.empty() || algorithm.empty()) {
            usage(argv[0]);
            return 2;
        }
        const auto graph = mwhc::Hypergraph::read(input);
        mwhc::Result result;
        if (algorithm == "allrootpath") result = mwhc::solve_allrootpath(graph, query, options);
        else if (algorithm == "medoidpath") result = mwhc::solve_medoidpath(graph, query, options);
        else if (algorithm == "fastpath") result = mwhc::solve_fastpath(graph, query, options);
        else throw std::invalid_argument("unknown algorithm: " + algorithm);
        std::cout << mwhc::result_json(graph, query, result) << '\n';
        return result.feasible ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
