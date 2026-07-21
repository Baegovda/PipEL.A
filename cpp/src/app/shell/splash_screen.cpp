#include "splash_screen.hpp"

#include <cmath>

#include <QApplication>
#include <QCoreApplication>
#include <QFile>
#include <QGuiApplication>
#include <QPainter>
#include <QScreen>
#include <QThread>
#include <QTimer>

#include "pipela/core/paths.hpp"
#include "pipela/core/version.hpp"

namespace {

bool splashDisabledByEnv() {
    const QByteArray raw = qgetenv("PIPELA_NO_SPLASH");
    const QByteArray v = raw.trimmed().toLower();
    return v == "1" || v == "true" || v == "yes" || v == "on";
}

QPixmap loadSplashPixmap() {
    const QString path = QString::fromStdString(pipela::core::splashImagePath());
    if (QFile::exists(path)) {
        QPixmap pm(path);
        if (!pm.isNull()) {
            constexpr int kMaxW = 720;
            if (pm.width() > kMaxW) {
                return pm.scaledToWidth(kMaxW, Qt::SmoothTransformation);
            }
            return pm;
        }
    }
    const QString exe_dir = QCoreApplication::applicationDirPath();
    const QString alt = exe_dir + QString::fromUtf8("/assets/splash.png");
    if (QFile::exists(alt)) {
        QPixmap pm(alt);
        if (!pm.isNull()) {
            return pm;
        }
    }
    return {};
}

}  // namespace

PipelaSplashProgress::PipelaSplashProgress(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::SplashScreen | Qt::WindowStaysOnTopHint);
    setAttribute(Qt::WA_TranslucentBackground, false);
    background_pixmap_ = loadSplashPixmap();
    if (!background_pixmap_.isNull()) {
        resize(background_pixmap_.size());
    } else {
        resize(520, 292);
    }
    anim_timer_ = new QTimer(this);
    connect(anim_timer_, &QTimer::timeout, this, &PipelaSplashProgress::tickAnim);
    anim_timer_->start(16);
}

void PipelaSplashProgress::setLoadingTarget(double target) {
    target_ = qBound(0.0, target, 1.0);
    if (target_ < display_) {
        display_ = target_;
    }
    update();
}

void PipelaSplashProgress::setLoadingMessage(const QString& message) {
    message_ = message;
    update();
}

bool PipelaSplashProgress::loadAnimQuiescent() const {
    return std::abs(display_ - target_) < 0.002;
}

void PipelaSplashProgress::tickAnim() {
    const double delta = target_ - display_;
    if (std::abs(delta) < 0.002) {
        display_ = target_;
    } else {
        display_ += delta * 0.12;
    }
    update();
}

void PipelaSplashProgress::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    QPainter p(this);
    const int bar_h = 22;
    const int bar_x = 28;
    const int bar_w = width() - 56;
    const int bar_y = height() - 48;

    if (!background_pixmap_.isNull()) {
        p.drawPixmap(0, 0, background_pixmap_);
        p.fillRect(0, static_cast<int>(height() * 0.72), width(), height() - static_cast<int>(height() * 0.72),
                   QColor(0, 0, 0, 140));
    } else {
        p.fillRect(rect(), QColor(18, 22, 28));
        p.setPen(QColor(108, 255, 154));
        QFont title = p.font();
        title.setPointSize(18);
        title.setBold(true);
        p.setFont(title);
        p.drawText(QRect(28, 28, width() - 56, 40), Qt::AlignLeft | Qt::AlignVCenter,
                   QString::fromUtf8("PIP EL.A"));
        p.setPen(QColor(74, 200, 120));
        QFont ver = p.font();
        ver.setPointSize(10);
        ver.setBold(false);
        p.setFont(ver);
        const QString ver_text = QString::fromStdString(pipela::core::appVersion());
        p.drawText(QRect(28, 68, width() - 56, 24), Qt::AlignLeft | Qt::AlignVCenter, ver_text);
    }

    p.setPen(Qt::NoPen);
    p.setBrush(QColor(30, 42, 36));
    p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 8, 8);
    const int fill_w = static_cast<int>(bar_w * display_);
    if (fill_w > 0) {
        p.setBrush(QColor(72, 220, 120));
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 8, 8);
    }
    p.setPen(QColor(200, 230, 210));
    QFont msg = p.font();
    msg.setPointSize(9);
    p.setFont(msg);
    p.drawText(QRect(bar_x, bar_y - 26, bar_w, 22), Qt::AlignLeft | Qt::AlignVCenter, message_);
}

PipelaSplashProgress* createStartupSplash(QApplication& app) {
    if (splashDisabledByEnv()) {
        return nullptr;
    }
    auto* splash = new PipelaSplashProgress();
    splash->setLoadingMessage(QString::fromUtf8("초기화 중…"));
    splash->setLoadingTarget(0.08);
    if (QScreen* screen = QGuiApplication::primaryScreen()) {
        const QRect geo = screen->availableGeometry();
        splash->move(geo.center() - splash->rect().center());
    }
    splash->show();
    app.processEvents();
    return splash;
}

void finishStartupSplash(QApplication& app, PipelaSplashProgress* splash, QWidget* main_window) {
    if (splash == nullptr) {
        if (main_window != nullptr) {
            main_window->show();
        }
        return;
    }
    splash->setLoadingTarget(1.0);
    splash->setLoadingMessage(QString::fromUtf8("시작…"));
    for (int i = 0; i < 120 && !splash->loadAnimQuiescent(); ++i) {
        app.processEvents();
        QThread::msleep(8);
    }
    if (main_window != nullptr) {
        main_window->show();
    }
    splash->close();
    splash->deleteLater();
    app.processEvents();
}
