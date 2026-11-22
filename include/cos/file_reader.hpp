#pragma once

#include <algorithm>
#include <charconv>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <system_error>
#include <tuple>
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

namespace detail {

inline bool blank(char character) { return character == ' ' || character == '\t'; }

inline const char * skip_blank(const char * first, const char * last)
{
    // O(espaços pulados).
    while (first != last && blank(*first)) {
        ++first;
    }
    return first;
}

template <class Number>
const char * parse_field(const char * first, const char * last, Number & value)
{
    // Espaços antes do número, conversão sem alocação e separador obrigatório depois: O(campo).
    first = skip_blank(first, last);
    const auto [end, error] = std::from_chars(first, last, value);
    if (error != std::errc{} || end == first || (end != last && !blank(*end))) {
        throw std::runtime_error{"o arquivo contém um número inválido"};
    }
    return end;
}

inline void finish_line(const char * first, const char * last)
{
    // Depois dos campos esperados, só podem restar espaços.
    if (skip_blank(first, last) != last) {
        throw std::runtime_error{"o arquivo contém conteúdo inesperado no fim de uma linha"};
    }
}

} // namespace detail

// Tempo O(tamanho do arquivo), lido duas vezes; memória de um bloco além do vetor de saída,
// reservado com o tamanho exato. Cada linha, sem a quebra, precisa ter menos que `block` bytes.
inline std::vector<std::tuple<std::uint32_t, std::uint32_t, double>>
read_triples(const std::string & path, std::uint32_t & header, std::size_t block = 1 << 20)
{
    auto input = std::ifstream{path, std::ios::binary};
    if (!input) {
        throw std::runtime_error{"não foi possível abrir o arquivo"};
    }

    auto triples = std::vector<std::tuple<std::uint32_t, std::uint32_t, double>>{};
    auto buffer = std::make_unique_for_overwrite<char[]>(block);
    auto pending = std::size_t{0};
    auto has_header = false;

    // Primeira passagem O(tamanho do arquivo): contar linhas evita que o vetor dobre e
    // mantenha até o dobro da capacidade, o que dominaria o pico de memória.
    auto lines = std::size_t{0};
    do {
        input.read(buffer.get(), std::streamsize(block));
        lines += std::size_t(std::count(buffer.get(), buffer.get() + input.gcount(), '\n'));
    } while (input);
    if (input.bad()) {
        throw std::runtime_error{"não foi possível ler o arquivo"};
    }
    input.clear();
    input.seekg(0);
    // O cabeçalho usa uma quebra, que cobre a última linha caso ela não tenha a sua.
    triples.reserve(lines);

    const auto parse_line = [&](const char * first, const char * last) {
        // O(tamanho da linha); CRLF e linhas vazias são aceitos.
        if (first != last && last[-1] == '\r') {
            --last;
        }

        auto cursor = detail::skip_blank(first, last);
        if (cursor == last) {
            return;
        }

        if (!has_header) {
            detail::finish_line(detail::parse_field(cursor, last, header), last);
            has_header = true;
            return;
        }

        auto & [source, target, weight] = triples.emplace_back();
        cursor = detail::parse_field(cursor, last, source);
        cursor = detail::parse_field(cursor, last, target);
        detail::finish_line(detail::parse_field(cursor, last, weight), last);
    };

    // Segunda passagem O(tamanho do arquivo); a linha incompleta passa ao próximo bloco.
    while (true) {
        input.read(buffer.get() + pending, std::streamsize(block - pending));
        if (input.bad()) {
            throw std::runtime_error{"não foi possível ler o arquivo"};
        }

        const auto at_end = input.eof();
        const auto * first = buffer.get();
        const auto * const last = first + pending + std::size_t(input.gcount());

        while (const auto * newline =
                   static_cast<const char *>(std::memchr(first, '\n', std::size_t(last - first)))) {
            parse_line(first, newline);
            first = newline + 1;
        }

        if (at_end) {
            // A última linha pode terminar sem quebra de linha.
            parse_line(first, last);
            break;
        }

        pending = std::size_t(last - first);
        if (pending == block) {
            throw std::runtime_error{"o arquivo contém uma linha maior que o bloco de leitura"};
        }
        std::memmove(buffer.get(), first, pending);
    }

    if (!has_header) {
        throw std::runtime_error{"não foi possível ler o cabeçalho do arquivo"};
    }
    return triples;
}

} // namespace cos_file
