#pragma once

class QIcon;

namespace pipela::ui::shell {

// AGENT: Same candidates as pipela_qt/qt_icons.py — vaultboy.png, then Pipela.ico.
QIcon pipelaApplicationIcon();
// AGENT: Windows tray — explicit pixmap sizes + Win32 ICO load (see qt_icons.cpp).
QIcon pipelaTrayIcon();

}  // namespace pipela::ui::shell
