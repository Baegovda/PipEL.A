#include "panels/kill_counter_tier_table_dialog.hpp"

#include <QHeaderView>
#include <QTableWidget>
#include <QVBoxLayout>

#include "pipela/core/kill_counter/tier_data.hpp"
#include "widgets/card_popup_shell.hpp"

namespace pipela::ui::panels {

namespace {

pipela::ui::widgets::CardFramelessDialog* g_open_dialog = nullptr;

}  // namespace

void showKillCounterTierTableDialog(QWidget* parent) {
    if (g_open_dialog != nullptr) {
        g_open_dialog->close();
        g_open_dialog = nullptr;
        return;
    }
    auto* dlg = new pipela::ui::widgets::CardFramelessDialog(parent);
    dlg->setAttribute(Qt::WA_DeleteOnClose, true);
    dlg->setTitleText(QString::fromUtf8("킬 카운터 등급표"));
    dlg->resize(440, 540);
    auto* table = new QTableWidget(dlg);
    table->setColumnCount(3);
    table->setHorizontalHeaderLabels(
        {QString::fromUtf8("번호"), QString::fromUtf8("호칭"), QString::fromUtf8("누적 킬")});
    table->horizontalHeader()->setStretchLastSection(true);
    table->verticalHeader()->setVisible(false);
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    table->setSelectionMode(QAbstractItemView::SingleSelection);
    table->setAlternatingRowColors(true);
    table->setStyleSheet(
        "QTableWidget { background: #141a1e; color: #e8f0ea; gridline-color: #3a4a42; }"
        "QHeaderView::section { background: #1e262c; color: #9aa8a0; }");
    const auto rows = pipela::core::kill_counter::builtinRankTableRows();
    table->setRowCount(static_cast<int>(rows.size()));
    for (int i = 0; i < static_cast<int>(rows.size()); ++i) {
        const auto& row = rows[static_cast<size_t>(i)];
        table->setItem(i, 0, new QTableWidgetItem(QString::number(row.num)));
        table->setItem(i, 1, new QTableWidgetItem(QString::fromStdString(row.title)));
        table->setItem(i, 2, new QTableWidgetItem(QString::number(row.point)));
    }
    table->resizeColumnsToContents();
    dlg->setBodyWidget(table);
    g_open_dialog = dlg;
    QObject::connect(dlg, &QObject::destroyed, []() { g_open_dialog = nullptr; });
    pipela::ui::widgets::centerCardPopup(dlg, parent);
    dlg->show();
}

}  // namespace pipela::ui::panels
