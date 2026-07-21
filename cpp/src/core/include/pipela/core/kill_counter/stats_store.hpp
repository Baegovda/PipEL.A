#pragma once

#include <string>
#include <vector>

namespace pipela::core::kill_counter {

std::string killCounterStatsFilePath();

void statsEnsureLoaded();
int statsSumLastSeconds(double sec);
int statsSumWindow(double t_lo, double t_hi);
int statsSumLapTotal(double lap_start_ts);
int statsSumLapInLastSeconds(double lap_start_ts, double sec);
void statsRecordDelta(int delta, bool allow_large_jump = false);
void statsReconcileWithN1(int n1);
void statsResetAll();

struct DailyKillSum {
    std::string date_key;
    int kills{0};
};

struct TodayBucketEntry {
    int kills{0};
    bool reload_mark{false};
};

std::vector<DailyKillSum> statsDailySumsLastDays(int days);
std::vector<int> statsTodayBucketSeries(int bucket_minutes);
std::vector<TodayBucketEntry> statsTodayBucketEntries(int bucket_minutes);

void statsRecordReloadMark(double unix_ts = -1.0);

// "HH:MM–HH:MM" local time range for today's bucket index (empty if invalid).
std::string formatTodayBucketTimeRange(int bucket_index, int bucket_minutes);

}  // namespace pipela::core::kill_counter
