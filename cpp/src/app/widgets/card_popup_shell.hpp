#pragma once

#include <QDialog>

class QWidget;

namespace pipela::ui::widgets {

// AGENT: Minimal frameless card dialog — parity subset of pipela_qt/card_popup_shell.py.
class CardFramelessDialog : public QDialog {
    Q_OBJECT
public:
    explicit CardFramelessDialog(QWidget* parent = nullptr);

    void setBodyWidget(QWidget* body);
    void setTitleText(const QString& title);

protected:
    void paintEvent(QPaintEvent* event) override;

private:
    QWidget* card_{nullptr};
    QWidget* body_host_{nullptr};
};

void centerCardPopup(QWidget* widget, QWidget* parent_or_anchor);

void messageCardDialog(QWidget* parent, const QString& title, const QString& message,
                       const QString& tone = QString::fromUtf8("info"));

bool confirmCardDialog(QWidget* parent, const QString& title, const QString& message,
                       const QString& confirm_text = QString::fromUtf8("예"),
                       const QString& cancel_text = QString::fromUtf8("아니오"));

void openUrlInBrowser(QWidget* parent, const QString& url, const QString& browser_url = {});

}  // namespace pipela::ui::widgets
