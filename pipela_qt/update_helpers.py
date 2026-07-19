"""Update UI helpers (main thread only)."""

from __future__ import annotations

import webbrowser

from PyQt6.QtWidgets import QWidget

from pipela_qt.card_popup_shell import (
    confirm_card_dialog,
    message_card_dialog,
    tri_choice_card_dialog,
)


def qt_message(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    tone: str = "info",
) -> None:
    message_card_dialog(parent, title, text, tone=tone)


def qt_ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    return confirm_card_dialog(
        parent,
        title=title,
        message=text,
        confirm_text="예",
        cancel_text="아니오",
        message_tone="muted",
        default_confirm=True,
    )


def qt_ask_yes_no_cancel(parent: QWidget | None, title: str, text: str) -> bool | None:
    return tri_choice_card_dialog(
        parent,
        title=title,
        message=text,
        yes_text="예",
        no_text="아니오",
        cancel_text="취소",
        message_tone="muted",
        default_which="yes",
    )


def qt_open_update_download(
    parent: QWidget | None,
    download_url: str,
    *,
    browser_url: str | None = None,
) -> None:
    """Open release page or direct zip URL in the default browser."""
    url = (browser_url or download_url or "").strip()
    if not url:
        qt_message(parent, "업데이트", "다운로드 URL을 확인할 수 없습니다.", tone="danger")
        return
    try:
        webbrowser.open(url)
    except Exception as ex:
        qt_message(
            parent,
            "업데이트",
            f"브라우저를 열 수 없습니다.\n\n{url}\n\n{ex}",
            tone="danger",
        )
