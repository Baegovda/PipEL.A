#pragma once

#include <functional>
#include <memory>

#include <QObject>
#include <QString>

namespace pipela::core::input {
class LeftClickController;
}
namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays {
class CursorHudController;
}

namespace pipela::app::input {

// AGENT: Bridges pipela_input_hooks DLL callbacks to Qt main thread + AppState.
class InputHooksBridge : public QObject {
    Q_OBJECT
public:
    explicit InputHooksBridge(QObject* parent = nullptr);
    ~InputHooksBridge() override;

    void bindState(pipela::core::state::AppState* state);
    void setCursorHudController(pipela::ui::overlays::CursorHudController* controller);
    void setQuitCallback(std::function<void()> callback);

    bool start();
    void stop();

signals:
    void inputEventQueued(const QString& line);
    void quitRequested();
    void cursorMoved(int x_phys, int y_phys);

private:
    void processMouse(int x, int y, int button, int pressed, unsigned hook_flags);
    void processLeftClick(int x, int y, bool is_down, unsigned hook_flags);
    void processKeyboard(unsigned int vk, int is_down);
    void buildLeftClickController();

    static void onMouse(int x, int y, int button, int pressed, unsigned hook_flags, void* user);
    static void onKeyboard(unsigned int vk, int is_down, void* user);

    void queueLine(const QString& line);
    bool registryBool(const char* key, bool fallback) const;
    double registryFloat(const char* key, double fallback) const;
    bool stateBool(const char* key, bool fallback) const;
    void setStateBool(const char* key, bool value);
    int stateInt(const char* key, int fallback) const;
    int incrementInt(const char* key, int delta);
    std::intptr_t targetHwnd() const;
    bool mouseInGameClient() const;
    void pauseLcRhForFlameTrigger();

    pipela::core::state::AppState* state_{nullptr};
    pipela::ui::overlays::CursorHudController* cursor_hud_{nullptr};
    std::unique_ptr<pipela::core::input::LeftClickController> left_click_;
    std::function<void()> quit_callback_;
    bool started_{false};
};

}  // namespace pipela::app::input
