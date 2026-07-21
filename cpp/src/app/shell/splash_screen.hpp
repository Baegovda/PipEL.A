#pragma once

#include <chrono>

#include <QPixmap>
#include <QTimer>
#include <QWidget>

class QApplication;

// AGENT: C++ splash parity with pipela_qt/splash_screen.py (synthesized panel + eased gauge).
class PipelaSplashProgress : public QWidget {
    Q_OBJECT
public:
    explicit PipelaSplashProgress(QWidget* parent = nullptr);

    void setLoadingTarget(double target);
    void setLoadingMessage(const QString& message);
    bool loadAnimQuiescent() const;

protected:
    void paintEvent(QPaintEvent* event) override;

private:
    void tickAnim();

    double target_{0.0};
    double display_{0.0};
    QString message_;
    QPixmap background_pixmap_;
    QTimer* anim_timer_{nullptr};
};

PipelaSplashProgress* createStartupSplash(QApplication& app);
void finishStartupSplash(QApplication& app, PipelaSplashProgress* splash, QWidget* main_window);
