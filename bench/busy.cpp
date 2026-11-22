// Vizinho para bench/run_contention.sh; não termina.
//   cos_busy registradores   ocupa um núcleo sem tocar na memória
//   cos_busy memoria         relê 64 MB sem parar: disputa o L2 e a banda de memória
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string_view>
#include <vector>

int main(int argc, char * argv[])
{
    const auto mode = std::string_view{argc == 2 ? argv[1] : ""};
    if (mode != "registradores" && mode != "memoria") {
        std::cerr << "uso: cos_busy registradores|memoria\n";
        return EXIT_FAILURE;
    }
    auto buffer = std::vector<std::uint64_t>(mode == "memoria" ? 8u << 20 : 0, 1);
    auto sum = std::uint64_t{1};
    for (;;) {
        if (buffer.empty()) {
            for (auto i = 0; i < 1'000'000; ++i) sum = sum * 6364136223846793005u + 1442695040888963407u;
        } else {
            for (std::size_t i = 0; i < buffer.size(); i += 8) sum += buffer[i]; // uma leitura por linha
        }
        if (sum == 42) std::cout << sum << '\n'; // impede o compilador de remover o laço
    }
}
