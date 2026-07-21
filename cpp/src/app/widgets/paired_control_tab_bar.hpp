#pragma once

#include <QTabBar>

class QStyleOptionTab;
class QStylePainter;

namespace pipela::ui::widgets {

// AGENT: Terminal | Settings 50/50 tab bar with clustered paint (Python _PairedControlTabBar).
class PairedControlTabBar : public QTabBar {
    Q_OBJECT
public:
    explicit PairedControlTabBar(QWidget* parent = nullptr);

    QSize tabSizeHint(int index) const override;
    QSize minimumTabSizeHint(int index) const override;
    QSize sizeHint() const override;

signals:
    void terminalGearClicked();

protected:
    void paintEvent(QPaintEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void leaveEvent(QEvent* event) override;
    void showEvent(QShowEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void tabLayoutChange() override;

private:
    int targetBarWidth() const;
    QRect terminalGearHitRect() const;
    void paintOneTab(QStylePainter& painter, QStyleOptionTab& opt, int index);

    bool terminal_gear_hover_{false};
};

}  // namespace pipela::ui::widgets
