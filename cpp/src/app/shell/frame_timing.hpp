#pragma once

#include <QObject>

namespace pipela::ui::shell {

// AGENT: Optional Qt notify frame timing — PIPELA_UI_FRAME_TIMING=1 writes TSV on exit.
class FrameTimingProbe : public QObject {
    Q_OBJECT
public:
    explicit FrameTimingProbe(QObject* parent = nullptr);
    static bool enabledByEnv();
};

void installFrameTimingProbeIfRequested();

// Returns PipelaApplication (notify timing) when PIPELA_UI_FRAME_TIMING=1, else plain QApplication.
QApplication* createPipelaApplication(int& argc, char** argv);

}  // namespace pipela::ui::shell
