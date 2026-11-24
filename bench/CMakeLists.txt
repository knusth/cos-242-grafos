# Executáveis de benchmark e experimentos isolados da biblioteca e dos programas da disciplina.
# Habilitado via -DCOS_BUILD_BENCHMARKS=ON na raiz do projeto.

add_executable(cos_bench2 parte2/dijkstra_bench.cpp)
target_link_libraries(cos_bench2 PRIVATE cos)

add_executable(cos_bench3 parte3/caminhos_bench.cpp)
target_link_libraries(cos_bench3 PRIVATE cos)

# Experimentos de baixo nível; std::print exige C++23.
add_executable(cos_lowlevel parte2/lowlevel_bench.cpp)
target_link_libraries(cos_lowlevel PRIVATE cos)
target_compile_features(cos_lowlevel PRIVATE cxx_std_23)

# O mesmo código com os contadores de hardware (bench/parte2/run_counters.sh, exige sudo); alvo à
# parte para não mudar o cos_lowlevel.
if(APPLE)
    add_executable(cos_counters parte2/lowlevel_bench.cpp)
    target_link_libraries(cos_counters PRIVATE cos)
    target_compile_features(cos_counters PRIVATE cxx_std_23)
    target_compile_definitions(cos_counters PRIVATE COS_COUNTERS=1)
endif()

# Vizinhos de bench/parte2/run_contention.sh; fora de cos_lowlevel para não mudar o código medido.
add_executable(cos_busy parte2/busy.cpp)
target_compile_features(cos_busy PRIVATE cxx_std_23)
