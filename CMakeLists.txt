cmake_minimum_required(VERSION 3.20)

project(cos_grafos VERSION 1.0.0 LANGUAGES CXX)

option(COS_MATRIX "Usa a matriz de adjacências no lugar da CSR" OFF)
option(COS_BUILD_BENCHMARKS "Compila os executáveis de benchmark em bench/" OFF)

set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Biblioteca header-only
add_library(cos INTERFACE)
target_include_directories(cos INTERFACE include)
target_compile_features(cos INTERFACE cxx_std_20)
target_compile_definitions(cos INTERFACE COS_MATRIX=$<BOOL:${COS_MATRIX}>)

# Programas da disciplina (Partes 1, 2 e 3)
add_executable(cos_part1 part1/main.cpp)
target_link_libraries(cos_part1 PRIVATE cos)

add_executable(cos_part2 part2/main.cpp)
target_link_libraries(cos_part2 PRIVATE cos)

add_executable(cos_part3 part3/main.cpp)
target_link_libraries(cos_part3 PRIVATE cos)

# Benchmarks opcionais (isolados em bench/)
if(COS_BUILD_BENCHMARKS)
    add_subdirectory(bench)
endif()

# Testes unitários e de integração (isolados em tests/)
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
