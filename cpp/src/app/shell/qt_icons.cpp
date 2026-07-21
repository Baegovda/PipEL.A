#include "shell/qt_icons.hpp"

#include <QApplication>
#include <QCoreApplication>
#include <QFile>
#include <QIcon>
#include <QImage>
#include <QPixmap>
#include <QStyle>

#include "pipela/core/paths.hpp"

#include <cstdio>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::ui::shell {

namespace {

bool trayDebugEnabled() {
    const QByteArray raw = qgetenv("PIPELA_DEBUG_TRAY");
    const QByteArray v = raw.trimmed().toLower();
    return v == "1" || v == "true" || v == "yes" || v == "on";
}

void trayDebugLog(const char* message) {
    if (!trayDebugEnabled()) {
        return;
    }
    fprintf(stderr, "[Tray][debug] %s\n", message);
}

bool iconHasTrayPixmap(const QIcon& ic) {
    if (ic.isNull()) {
        return false;
    }
    for (const int sz : {16, 20, 24, 32}) {
        if (!ic.pixmap(sz, sz).isNull()) {
            return true;
        }
    }
    return false;
}

QIcon buildTrayIconFromPixmap(const QPixmap& src) {
    if (src.isNull()) {
        return {};
    }
    QIcon icon;
    for (const int sz : {16, 20, 24, 32, 48}) {
        icon.addPixmap(src.scaled(sz, sz, Qt::KeepAspectRatio, Qt::SmoothTransformation));
    }
    return iconHasTrayPixmap(icon) ? icon : QIcon{};
}

QPixmap loadPixmapAny(const QString& path) {
    if (path.startsWith(QString::fromUtf8(":/"))) {
        return QPixmap(path);
    }
    if (!QFile::exists(path)) {
        return {};
    }
    return QPixmap(path);
}

QIcon iconFromPixmapPath(const QString& path) {
    return buildTrayIconFromPixmap(loadPixmapAny(path));
}

#ifdef _WIN32
QIcon iconFromWin32IcoFile(const QString& path) {
    if (!QFile::exists(path)) {
        return {};
    }
    const std::wstring wpath = path.toStdWString();
    HICON h = reinterpret_cast<HICON>(LoadImageW(
        nullptr, wpath.c_str(), IMAGE_ICON, GetSystemMetrics(SM_CXSMICON),
        GetSystemMetrics(SM_CYSMICON), LR_LOADFROMFILE));
    if (h == nullptr) {
        h = reinterpret_cast<HICON>(LoadImageW(nullptr, wpath.c_str(), IMAGE_ICON, 0, 0,
                                               LR_LOADFROMFILE | LR_DEFAULTSIZE));
    }
    if (h == nullptr) {
        return {};
    }
    const QImage img = QImage::fromHICON(h);
    DestroyIcon(h);
    return buildTrayIconFromPixmap(QPixmap::fromImage(img));
}
#endif

QIcon loadFirstTrayIcon(const QString* paths, std::size_t count) {
    for (std::size_t i = 0; i < count; ++i) {
#ifdef _WIN32
        if (paths[i].endsWith(QString::fromUtf8(".ico"), Qt::CaseInsensitive)) {
            if (const QIcon ic = iconFromWin32IcoFile(paths[i]); iconHasTrayPixmap(ic)) {
                trayDebugLog(paths[i].toUtf8().constData());
                return ic;
            }
        }
#endif
        if (const QIcon ic = iconFromPixmapPath(paths[i]); iconHasTrayPixmap(ic)) {
            trayDebugLog(paths[i].toUtf8().constData());
            return ic;
        }
    }
    return {};
}

}  // namespace

QIcon pipelaApplicationIcon() { return pipelaTrayIcon(); }

QIcon pipelaTrayIcon() {
    const QString exe_dir = QCoreApplication::applicationDirPath();
    const QString root = QString::fromStdString(pipela::core::resolveRepoRoot());
    const QString assets = QString::fromStdString(pipela::core::assetsDir());
    const QString candidates[] = {
        exe_dir + QString::fromUtf8("/Pipela.ico"),
        QString::fromUtf8(":/icons/pipela.ico"),
        exe_dir + QString::fromUtf8("/assets/vaultboy.png"),
        QString::fromUtf8(":/icons/vaultboy.png"),
        assets + QString::fromUtf8("/vaultboy.png"),
        root + QString::fromUtf8("/Pipela.ico"),
    };
    if (QIcon ic = loadFirstTrayIcon(candidates, sizeof(candidates) / sizeof(candidates[0]));
        iconHasTrayPixmap(ic)) {
        return ic;
    }
    if (QApplication* app = qApp) {
        const QIcon fallback = app->style()->standardIcon(QStyle::SP_ComputerIcon);
        if (iconHasTrayPixmap(fallback)) {
            trayDebugLog("QStyle::SP_ComputerIcon");
            return fallback;
        }
    }
    trayDebugLog("no icon loaded");
    return {};
}

}  // namespace pipela::ui::shell
