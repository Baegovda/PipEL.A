#include "shell/frame_timing.hpp"

#include <QApplication>
#include <QCoreApplication>
#include <QEvent>
#include <QFile>
#include <QTextStream>

#include <chrono>
#include <cstdlib>
#include <map>
#include <string>

namespace pipela::ui::shell {

namespace {

bool envTruthy(const char* key) {
    const char* raw = std::getenv(key);
    return raw != nullptr && (raw[0] == '1' || raw[0] == 't' || raw[0] == 'T');
}

struct Acc {
    double total_ns{0.0};
    int count{0};
};

std::map<std::string, Acc> g_acc;
bool g_enabled = false;

class PipelaApplication : public QApplication {
public:
    PipelaApplication(int& argc, char** argv) : QApplication(argc, argv) {}

    bool notify(QObject* receiver, QEvent* event) override {
        if (!g_enabled) {
            return QApplication::notify(receiver, event);
        }
        const auto t0 = std::chrono::steady_clock::now();
        const bool ok = QApplication::notify(receiver, event);
        const auto t1 = std::chrono::steady_clock::now();
        const double ns =
            std::chrono::duration<double, std::nano>(t1 - t0).count();
        auto& a = g_acc["PipelaApplication.notify_total"];
        a.total_ns += ns;
        a.count += 1;
        Q_UNUSED(receiver);
        Q_UNUSED(event);
        return ok;
    }
};

void flushFrameTimingTsv() {
    if (!g_enabled || g_acc.empty()) {
        return;
    }
    QFile f(QString::fromUtf8("profiling/agent_profile/frame_timing.tsv"));
    if (!f.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return;
    }
    QTextStream out(&f);
    out << "label\tcalls\ttotal_ms\tavg_us\n";
    for (const auto& [label, a] : g_acc) {
        const double total_ms = a.total_ns / 1e6;
        const double avg_us = a.count > 0 ? (a.total_ns / a.count) / 1e3 : 0.0;
        out << QString::fromStdString(label) << '\t' << a.count << '\t' << total_ms << '\t'
            << avg_us << '\n';
    }
}

PipelaApplication* g_pipela_app = nullptr;

}  // namespace

bool FrameTimingProbe::enabledByEnv() { return envTruthy("PIPELA_UI_FRAME_TIMING"); }

FrameTimingProbe::FrameTimingProbe(QObject* parent) : QObject(parent) {
    connect(qApp, &QCoreApplication::aboutToQuit, this, []() { flushFrameTimingTsv(); });
}

void installFrameTimingProbeIfRequested() {
    g_enabled = FrameTimingProbe::enabledByEnv();
    if (!g_enabled) {
        return;
    }
    static FrameTimingProbe* probe = new FrameTimingProbe(qApp);
    Q_UNUSED(probe);
}

QApplication* createPipelaApplication(int& argc, char** argv) {
    g_enabled = FrameTimingProbe::enabledByEnv();
    if (g_enabled) {
        g_pipela_app = new PipelaApplication(argc, argv);
        return g_pipela_app;
    }
    return new QApplication(argc, argv);
}

}  // namespace pipela::ui::shell
