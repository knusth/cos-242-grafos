cmake_minimum_required(VERSION 3.20)

project(cos_grafos VERSION 1.0.0 LANGUAGES CXX)

option(COS_MATRIX "Usa a matriz de adjacências no lugar da CSR" OFF)

set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

add_library(cos INTERFACE)
target_include_directories(cos INTERFACE include)
target_compile_features(cos INTERFACE cxx_std_20)
target_compile_definitions(cos INTERFACE COS_MATRIX=$<BOOL:${COS_MATRIX}>)

add_executable(cos_part1 part1/main.cpp)
target_link_libraries(cos_part1 PRIVATE cos)

add_executable(cos_part2 part2/main.cpp)
target_link_libraries(cos_part2 PRIVATE cos)

add_executable(cos_bench2 bench/dijkstra_bench.cpp)
target_link_libraries(cos_bench2 PRIVATE cos)

add_executable(cos_part3 part3/main.cpp)
target_link_libraries(cos_part3 PRIVATE cos)

add_executable(cos_bench3 bench/caminhos_bench.cpp)
target_link_libraries(cos_bench3 PRIVATE cos)

# Experimentos de baixo nível; std::print exige C++23.
add_executable(cos_lowlevel bench/lowlevel_bench.cpp)
target_link_libraries(cos_lowlevel PRIVATE cos)
target_compile_features(cos_lowlevel PRIVATE cxx_std_23)
# O mesmo código com os contadores de hardware (bench/run_counters.sh, exige sudo); alvo à
# parte para não mudar o cos_lowlevel.
if(APPLE)
  add_executable(cos_counters bench/lowlevel_bench.cpp)
  target_link_libraries(cos_counters PRIVATE cos)
  target_compile_features(cos_counters PRIVATE cxx_std_23)
  target_compile_definitions(cos_counters PRIVATE COS_COUNTERS=1)
endif()
# Vizinhos de bench/run_contention.sh; fora de cos_lowlevel para não mudar o código medido.
add_executable(cos_busy bench/busy.cpp)
target_compile_features(cos_busy PRIVATE cxx_std_23)

include(CTest)
if(BUILD_TESTING)
    add_executable(cos_tests tests/graph_tests.cpp)
    target_link_libraries(cos_tests PRIVATE cos)
    target_compile_definitions(cos_tests PRIVATE
        COS_FIXTURE="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/graph.txt"
        COS_WEIGHTED_FIXTURE="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/weighted.txt"
    )
    add_test(NAME cos_tests COMMAND cos_tests)
endif()
