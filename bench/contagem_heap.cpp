// Contagem de operações do heap e traço de uma execução (tamanho do heap e dist por extração).
#include <cos/file_reader.hpp>
#include <cos/graph.hpp>

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <print>
#include <random>
#include <string>
#include <vector>

using cos_graph::Vertex;
using cos_graph::Weight;

struct CountingHeap {
    inline static std::uint64_t pushes = 0, pops = 0, peak = 0, size = 0;
    static void reset() { pushes = pops = peak = size = 0; }
    explicit CountingHeap(Vertex n) : heap_{n}, queued_(n, false) {}
    void push(Vertex v, Weight d)
    {
        ++pushes;
        if (!queued_[v]) { queued_[v] = true; peak = std::max(peak, ++size); }
        heap_.push(v, d);
    }
    Vertex pop()
    {
        auto v = heap_.pop();
        if (v != cos_graph::no_vertex) { ++pops; --size; }
        return v;
    }
    cos_graph::HeapFrontier heap_;
    std::vector<bool> queued_;
};

int main(int argc, char ** argv)
{
    std::string name = argv[1], path = argv[2];
    auto runs = std::atoi(argv[3]);
    Vertex n = 0;
    auto edges = cos_file::read_triples(path, n);
    for (auto & [a, b, w] : edges) { --a; --b; }
    auto m = edges.size();
    auto g = cos_graph::Graph{n, edges};
    edges.clear(); edges.shrink_to_fit();
    auto rng = std::mt19937_64{2026};
    auto pick = std::uniform_int_distribution<Vertex>{0, n - 1};
    std::print("{{\"name\":\"{}\",\"n\":{},\"m\":{},\"runs\":[", name, n, m);
    for (int r = 0; r < runs; ++r) {
        auto s = pick(rng);
        CountingHeap::reset();
        std::vector<std::pair<std::uint64_t, double>> trace;
        if (r == 0) trace.reserve(n);
        g.dijkstra<CountingHeap>(s, [&](Vertex, Vertex, Weight d) {
            if (r == 0) trace.emplace_back(CountingHeap::size, d);
        });
        std::print("{}{{\"source\":{},\"pushes\":{},\"pops\":{},\"peak\":{}", r ? "," : "", s + 1,
                   CountingHeap::pushes, CountingHeap::pops, CountingHeap::peak);
        if (r == 0) {
            // ~500 pontos igualmente espaçados nas extrações.
            std::print(",\"trace\":[");
            auto step = std::max<std::size_t>(1, trace.size() / 500);
            for (std::size_t i = 0; i < trace.size(); i += step)
                std::print("{}[{},{},{:.6g}]", i ? "," : "", i + 1, trace[i].first, trace[i].second);
            std::print("]");
        }
        std::print("}}");
    }
    std::println("]}}");
}
