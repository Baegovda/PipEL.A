#pragma once

#include <functional>

#include <QLineEdit>
#include <QWidget>

namespace pipela::app::widgets {

// AGENT: Key capture row — parity subset of pipela_qt hp/flame/ammo key sections.
class KeyCaptureRow : public QWidget {
    Q_OBJECT
public:
    explicit KeyCaptureRow(const QString& label, QWidget* parent = nullptr);

    void setRegistryKey(const char* key);
    void setVk(int vk);
    int vk() const { return vk_; }

    void setOnSaved(std::function<void(int)> fn) { on_saved_ = std::move(fn); }

signals:
    void vkChanged(int vk);

protected:
    void keyPressEvent(QKeyEvent* event) override;

private:
    void beginCapture();
    void endCapture(bool cancel);
    void refreshDisplay();

    QLineEdit* display_{nullptr};
    const char* registry_key_{nullptr};
    int vk_{0};
    bool capturing_{false};
    std::function<void(int)> on_saved_;
};

}  // namespace pipela::app::widgets
