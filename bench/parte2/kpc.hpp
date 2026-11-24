// Contadores de hardware do processador no macOS, pelos frameworks privados kperf e kperfdata
// (os mesmos que o Instruments usa). Ler os contadores exige root.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <dlfcn.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace cos_kpc {

using u32 = std::uint32_t;
using u64 = std::uint64_t;

class Counters {
  public:
    // Eventos com os nomes de /usr/share/kpep; a base certa para o processador é escolhida
    // pelo próprio kperfdata.
    explicit Counters(const std::vector<std::string> & events)
    {
        load();
        void * db = nullptr;
        check(db_create(nullptr, &db), "kpep_db_create");
        void * config = nullptr;
        check(config_create(db, &config), "kpep_config_create");
        check(config_force_counters(config), "kpep_config_force_counters");
        for (const auto & name : events) {
            void * event = nullptr;
            check(db_event(db, name.c_str(), &event), "evento inexistente: " + name);
            check(config_add_event(config, &event, 0, nullptr), "evento não cabe: " + name);
        }
        check(config_kpc_classes(config, &classes_), "kpep_config_kpc_classes");
        auto count = std::size_t{0};
        check(config_kpc_count(config, &count), "kpep_config_kpc_count");
        check(config_kpc_map(config, map_.data(), sizeof(map_)), "kpep_config_kpc_map");
        auto registers = std::array<u64, max_counters>{};
        check(config_kpc(config, registers.data(), sizeof(registers)), "kpep_config_kpc");
        config_free(config);
        db_free(db);

        check(force_all_ctrs_set(1), "kpc_force_all_ctrs_set (rode com sudo)");
        if ((classes_ & configurable_class) != 0 && count > 0) {
            check(set_config(classes_, registers.data()), "kpc_set_config");
        }
        check(set_counting(classes_), "kpc_set_counting");
        check(set_thread_counting(classes_), "kpc_set_thread_counting");
        events_ = events.size();
    }

    ~Counters()
    {
        set_counting(0);
        set_thread_counting(0);
        force_all_ctrs_set(0);
    }

    Counters(const Counters &) = delete;
    Counters & operator=(const Counters &) = delete;

    // Valores acumulados da thread atual, na ordem dos eventos do construtor.
    std::vector<u64> read() const
    {
        auto raw = std::array<u64, max_counters>{};
        check(get_thread_counters(0, max_counters, raw.data()), "kpc_get_thread_counters");
        auto values = std::vector<u64>(events_);
        for (auto index = std::size_t{0}; index < events_; ++index) {
            values[index] = raw[map_[index]];
        }
        return values;
    }

  private:
    static constexpr u32 max_counters = 32;
    static constexpr u32 configurable_class = 1u << 1;

    template <class Function> static void bind(void * library, Function & function, const char * name)
    {
        function = reinterpret_cast<Function>(dlsym(library, name));
        if (function == nullptr) {
            throw std::runtime_error{std::string{"símbolo ausente: "} + name};
        }
    }

    static void check(int status, const std::string & what)
    {
        if (status != 0) {
            throw std::runtime_error{what + " falhou (" + std::to_string(status) + ")"};
        }
    }

    void load()
    {
        auto * kperf = dlopen("/System/Library/PrivateFrameworks/kperf.framework/kperf", RTLD_LAZY);
        auto * data = dlopen("/System/Library/PrivateFrameworks/kperfdata.framework/kperfdata", RTLD_LAZY);
        if (kperf == nullptr || data == nullptr) {
            throw std::runtime_error{"kperf ou kperfdata indisponível"};
        }
        bind(kperf, force_all_ctrs_set, "kpc_force_all_ctrs_set");
        bind(kperf, set_config, "kpc_set_config");
        bind(kperf, set_counting, "kpc_set_counting");
        bind(kperf, set_thread_counting, "kpc_set_thread_counting");
        bind(kperf, get_thread_counters, "kpc_get_thread_counters");
        bind(data, db_create, "kpep_db_create");
        bind(data, db_free, "kpep_db_free");
        bind(data, db_event, "kpep_db_event");
        bind(data, config_create, "kpep_config_create");
        bind(data, config_free, "kpep_config_free");
        bind(data, config_force_counters, "kpep_config_force_counters");
        bind(data, config_add_event, "kpep_config_add_event");
        bind(data, config_kpc_classes, "kpep_config_kpc_classes");
        bind(data, config_kpc_count, "kpep_config_kpc_count");
        bind(data, config_kpc_map, "kpep_config_kpc_map");
        bind(data, config_kpc, "kpep_config_kpc");
    }

    int (*force_all_ctrs_set)(int) = nullptr;
    int (*set_config)(u32, u64 *) = nullptr;
    int (*set_counting)(u32) = nullptr;
    int (*set_thread_counting)(u32) = nullptr;
    int (*get_thread_counters)(u32, u32, u64 *) = nullptr;
    int (*db_create)(const char *, void **) = nullptr;
    void (*db_free)(void *) = nullptr;
    int (*db_event)(void *, const char *, void **) = nullptr;
    int (*config_create)(void *, void **) = nullptr;
    void (*config_free)(void *) = nullptr;
    int (*config_force_counters)(void *) = nullptr;
    int (*config_add_event)(void *, void **, u32, u32 *) = nullptr;
    int (*config_kpc_classes)(void *, u32 *) = nullptr;
    int (*config_kpc_count)(void *, std::size_t *) = nullptr;
    int (*config_kpc_map)(void *, std::size_t *, std::size_t) = nullptr;
    int (*config_kpc)(void *, u64 *, std::size_t) = nullptr;

    u32 classes_ = 0;
    std::array<std::size_t, max_counters> map_{};
    std::size_t events_ = 0;
};

} // namespace cos_kpc
