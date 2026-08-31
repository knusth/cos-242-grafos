#pragma once

#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace cos_file {

inline std::vector<std::pair<std::uint32_t, std::uint32_t>> read_pairs(const std::string & path,
                                                                       std::uint32_t & header)
{
    auto input = std::ifstream{path};
    if (!(input >> header)) {
        throw std::runtime_error{"não foi possível ler o cabeçalho do arquivo"};
    }

    auto pairs = std::vector<std::pair<std::uint32_t, std::uint32_t>>{};
    auto first = std::uint32_t{0};
    auto second = std::uint32_t{0};

    while (input >> first >> second) {
        pairs.emplace_back(first, second);
    }
    return pairs;
}

} // namespace cos_file
