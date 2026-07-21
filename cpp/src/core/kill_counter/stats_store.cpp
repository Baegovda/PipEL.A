#include "pipela/core/kill_counter/stats_store.hpp"

#include <algorithm>
#include <chrono>
#include <ctime>
#include <cstdio>
#include <fstream>
#include <map>
#include <mutex>
#include <vector>

#include <nlohmann/json.hpp>

#include "pipela/core/kill_counter/tier_data.hpp"
#include "pipela/core/paths.hpp"

namespace pipela::core::kill_counter {

namespace {

struct StatsEvent {
    double t{0.0};
    int d{0};
};

std::mutex g_mutex;
bool g_loaded{false};
std::vector<StatsEvent> g_events;
std::vector<double> g_reload_marks;
std::string g_reconcile_local_date;
int g_n1_at_local_day_start{-1};

constexpr int kStatsMaxSingleEventDelta = 12000;

double nowUnix() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

void loadFromDisk() {
    g_events.clear();
    const std::string path = killCounterStatsFilePath();
    std::ifstream in(path);
    if (!in) {
        return;
    }
    try {
        nlohmann::json root;
        in >> root;
        if (!root.contains("events") || !root["events"].is_array()) {
            return;
        }
        for (const auto& item : root["events"]) {
            if (!item.is_object()) {
                continue;
            }
            StatsEvent ev;
            ev.t = item.value("t", 0.0);
            ev.d = item.value("d", 0);
            if (ev.d > 0) {
                g_events.push_back(ev);
            }
        }
        if (root.contains("reload_marks") && root["reload_marks"].is_array()) {
            for (const auto& rm : root["reload_marks"]) {
                if (rm.is_number()) {
                    g_reload_marks.push_back(rm.get<double>());
                }
            }
        }
        std::sort(g_events.begin(), g_events.end(),
                  [](const StatsEvent& a, const StatsEvent& b) { return a.t < b.t; });
    } catch (...) {
        g_events.clear();
    }
}

void saveToDisk() {
    nlohmann::json root;
    nlohmann::json events = nlohmann::json::array();
    for (const auto& ev : g_events) {
        events.push_back({{"t", ev.t}, {"d", ev.d}});
    }
    root["events"] = std::move(events);
    nlohmann::json rmarks = nlohmann::json::array();
    for (double t : g_reload_marks) {
        rmarks.push_back(t);
    }
    root["reload_marks"] = std::move(rmarks);
    const std::string path = killCounterStatsFilePath();
    std::ofstream out(path, std::ios::trunc);
    if (out) {
        out << root.dump(2);
    }
}

void pruneOldEvents(double now_ts) {
    const double cutoff = now_ts - 60.0 * 86400.0;
    g_events.erase(std::remove_if(g_events.begin(), g_events.end(),
                                  [cutoff](const StatsEvent& ev) { return ev.t < cutoff; }),
                   g_events.end());
    g_reload_marks.erase(
        std::remove_if(g_reload_marks.begin(), g_reload_marks.end(),
                       [cutoff](double t) { return t < cutoff; }),
        g_reload_marks.end());
}

std::string localDateKey(double unix_ts) {
    const std::time_t tt = static_cast<std::time_t>(unix_ts);
    std::tm lt{};
#ifdef _WIN32
    localtime_s(&lt, &tt);
#else
    localtime_r(&tt, &lt);
#endif
    char buf[16]{};
    std::strftime(buf, sizeof(buf), "%Y-%m-%d", &lt);
    return buf;
}

int sumEventsForDay(const std::string& day_key) {
    int sum = 0;
    for (const auto& ev : g_events) {
        if (localDateKey(ev.t) == day_key) {
            sum += ev.d;
        }
    }
    return sum;
}

}  // namespace

std::string killCounterStatsFilePath() { return pipela::core::killCounterStatsFilePath(); }

void statsEnsureLoaded() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_loaded) {
        return;
    }
    loadFromDisk();
    pruneOldEvents(nowUnix());
    g_loaded = true;
}

int statsSumLastSeconds(double sec) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_loaded) {
        loadFromDisk();
        g_loaded = true;
    }
    const double now = nowUnix();
    const double cutoff = now - sec;
    int sum = 0;
    for (const auto& ev : g_events) {
        if (ev.t >= cutoff) {
            sum += ev.d;
        }
    }
    return sum;
}

int statsSumWindow(double t_lo, double t_hi) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_loaded) {
        loadFromDisk();
        g_loaded = true;
    }
    int sum = 0;
    for (const auto& ev : g_events) {
        if (ev.t >= t_lo && ev.t <= t_hi) {
            sum += ev.d;
        }
    }
    return sum;
}

int statsSumLapTotal(double lap_start_ts) {
    if (lap_start_ts <= 0.0) {
        return 0;
    }
    return statsSumWindow(lap_start_ts, nowUnix());
}

int statsSumLapInLastSeconds(double lap_start_ts, double sec) {
    if (lap_start_ts <= 0.0) {
        return 0;
    }
    const double now = nowUnix();
    const double cutoff = now - sec;
    return statsSumWindow(std::max(lap_start_ts, cutoff), now);
}

void statsRecordDelta(int delta, bool allow_large_jump) {
    if (delta <= 0) {
        return;
    }
    if (!allow_large_jump && delta > kStatsMaxSingleEventDelta) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_loaded) {
        loadFromDisk();
        g_loaded = true;
    }
    const double now = nowUnix();
    g_events.push_back(StatsEvent{now, delta});
    pruneOldEvents(now);
    saveToDisk();
}

void statsReconcileWithN1(int n1) {
    if (n1 < 0) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_loaded) {
        loadFromDisk();
        g_loaded = true;
    }
    const double now = nowUnix();
    const std::string today = localDateKey(now);
    if (g_reconcile_local_date != today) {
        g_reconcile_local_date = today;
        const int prior = sumEventsForDay(today);
        g_n1_at_local_day_start = std::max(0, n1 - prior);
    }
    if (g_n1_at_local_day_start < 0) {
        g_n1_at_local_day_start = n1;
    } else if (n1 < g_n1_at_local_day_start - 2) {
        g_n1_at_local_day_start = n1;
    }
    const int allow = std::max(0, n1 - g_n1_at_local_day_start);
    const int today_sum = sumEventsForDay(today);
    if (today_sum > allow) {
        int excess = today_sum - allow;
        for (auto it = g_events.rbegin(); it != g_events.rend() && excess > 0; ++it) {
            if (localDateKey(it->t) != today) {
                continue;
            }
            const int sub = std::min(it->d, excess);
            it->d -= sub;
            excess -= sub;
        }
        g_events.erase(std::remove_if(g_events.begin(), g_events.end(),
                                      [](const StatsEvent& ev) { return ev.d <= 0; }),
                       g_events.end());
        saveToDisk();
    }
}

std::vector<DailyKillSum> statsDailySumsLastDays(int days) {
    statsEnsureLoaded();
    std::lock_guard<std::mutex> lock(g_mutex);
    std::map<std::string, int> sums;
    for (const auto& ev : g_events) {
        sums[localDateKey(ev.t)] += ev.d;
    }
    std::vector<DailyKillSum> out;
    const double now = nowUnix();
    for (int i = days - 1; i >= 0; --i) {
        const std::string key = localDateKey(now - static_cast<double>(i) * 86400.0);
        DailyKillSum row;
        row.date_key = key;
        const auto it = sums.find(key);
        row.kills = it == sums.end() ? 0 : it->second;
        out.push_back(row);
    }
    return out;
}

std::vector<int> statsTodayBucketSeries(int bucket_minutes) {
    const auto entries = statsTodayBucketEntries(bucket_minutes);
    std::vector<int> out;
    out.reserve(entries.size());
    for (const auto& e : entries) {
        out.push_back(e.kills);
    }
    return out;
}

std::vector<TodayBucketEntry> statsTodayBucketEntries(int bucket_minutes) {
    if (bucket_minutes < 1) {
        bucket_minutes = 30;
    }
    statsEnsureLoaded();
    std::lock_guard<std::mutex> lock(g_mutex);
    const double now = nowUnix();
    const std::time_t tt = static_cast<std::time_t>(now);
    std::tm lt{};
#ifdef _WIN32
    localtime_s(&lt, &tt);
#else
    localtime_r(&tt, &lt);
#endif
    std::tm midnight = lt;
    midnight.tm_hour = 0;
    midnight.tm_min = 0;
    midnight.tm_sec = 0;
    const double day_start = static_cast<double>(std::mktime(&midnight));
    const int total_min = lt.tm_hour * 60 + lt.tm_min;
    const int bucket_count = total_min / bucket_minutes + 1;
    std::vector<TodayBucketEntry> buckets(static_cast<size_t>(bucket_count));
    for (const auto& ev : g_events) {
        if (ev.t < day_start) {
            continue;
        }
        const int min_of_day = static_cast<int>((ev.t - day_start) / 60.0);
        const int idx = min_of_day / bucket_minutes;
        if (idx >= 0 && idx < bucket_count) {
            buckets[static_cast<size_t>(idx)].kills += ev.d;
        }
    }
    for (double rm : g_reload_marks) {
        if (rm < day_start || rm > now) {
            continue;
        }
        const int min_of_day = static_cast<int>((rm - day_start) / 60.0);
        const int idx = min_of_day / bucket_minutes;
        if (idx >= 0 && idx < bucket_count) {
            buckets[static_cast<size_t>(idx)].reload_mark = true;
        }
    }
    return buckets;
}

void statsRecordReloadMark(double unix_ts) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_loaded) {
        loadFromDisk();
        g_loaded = true;
    }
    const double t = unix_ts >= 0.0 ? unix_ts : nowUnix();
    g_reload_marks.push_back(t);
    pruneOldEvents(t);
    saveToDisk();
}

namespace {

std::string formatHm(int minutes_of_day) {
    minutes_of_day = std::max(0, std::min(24 * 60 - 1, minutes_of_day));
    const int h = minutes_of_day / 60;
    const int m = minutes_of_day % 60;
    char buf[8];
    std::snprintf(buf, sizeof(buf), "%02d:%02d", h, m);
    return buf;
}

}  // namespace

std::string formatTodayBucketTimeRange(int bucket_index, int bucket_minutes) {
    if (bucket_index < 0 || bucket_minutes < 1) {
        return {};
    }
    const int start_min = bucket_index * bucket_minutes;
    const int end_min = start_min + bucket_minutes - 1;
    return formatHm(start_min) + "\xe2\x80\x93" + formatHm(end_min);  // en-dash UTF-8
}

void statsResetAll() {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_events.clear();
    g_reload_marks.clear();
    g_reconcile_local_date.clear();
    g_n1_at_local_day_start = -1;
    g_loaded = true;
    saveToDisk();
}

}  // namespace pipela::core::kill_counter
