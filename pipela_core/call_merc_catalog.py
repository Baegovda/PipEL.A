"""Call Merc 4단계 — 전역 이름·레지 키 등 순수 데이터( UI 섹션 튜플은 `main` )."""

from __future__ import annotations

CALL_MERC_KINDS: tuple[str, ...] = ("call_merc_1", "call_merc_2", "call_merc_3", "call_merc_4")

CALL_MERC_LOG_PREFIX = "[Call Merc]"

CALL_MERC_LOOP_LOG_TAG: dict[str, str] = {
    "call_merc_1": "trigger",
    "call_merc_2": "contract",
    "call_merc_3": "call",
    "call_merc_4": "close",
}
CALL_MERC_PATH_KEY: dict[str, str] = {
    "call_merc_1": "CALL_MERC_1_IMAGE_PATH",
    "call_merc_2": "CALL_MERC_2_IMAGE_PATH",
    "call_merc_3": "CALL_MERC_3_IMAGE_PATH",
    "call_merc_4": "CALL_MERC_4_IMAGE_PATH",
}
CALL_MERC_REG_DATA_KEY: dict[str, str] = {
    "call_merc_1": "call_merc_1_image_data",
    "call_merc_2": "call_merc_2_image_data",
    "call_merc_3": "call_merc_3_image_data",
    "call_merc_4": "call_merc_4_image_data",
}
CALL_MERC_THR_KEY: dict[str, str] = {
    "call_merc_1": "call_merc_1_threshold",
    "call_merc_2": "call_merc_2_threshold",
    "call_merc_3": "call_merc_3_threshold",
    "call_merc_4": "call_merc_4_threshold",
}
CALL_MERC_SCORE_KEY: dict[str, str] = {
    "call_merc_1": "call_merc_1_score",
    "call_merc_2": "call_merc_2_score",
    "call_merc_3": "call_merc_3_score",
    "call_merc_4": "call_merc_4_score",
}
CALL_MERC_ROI_KEY: dict[str, str] = {
    "call_merc_1": "call_merc_1_match_region",
    "call_merc_2": "call_merc_2_match_region",
    "call_merc_3": "call_merc_3_match_region",
    "call_merc_4": "call_merc_4_match_region",
}
CALL_MERC_FILE_DLG: dict[str, str] = {
    "call_merc_1": "「공격을 지시할 용병이 없습니다」템플릿 이미지 선택",
    "call_merc_2": "「용병 고용계약서」템플릿 이미지 선택",
    "call_merc_3": "「호출」템플릿 이미지 선택",
    "call_merc_4": "「창 닫기」템플릿 이미지 선택",
}
CALL_MERC_BUNDLE_FN: dict[str, str] = {
    "call_merc_1": "공격을 지시할 용병이 없습니다",
    "call_merc_2": "용병 고용계약서",
    "call_merc_3": "호출",
    "call_merc_4": "창 닫기",
}
CALL_MERC_SCORE_BINDINGS: tuple[tuple[str, str, str], ...] = (
    ("call_merc_1", "call_merc_1_score", "call_merc_1_threshold"),
    ("call_merc_2", "call_merc_2_score", "call_merc_2_threshold"),
    ("call_merc_3", "call_merc_3_score", "call_merc_3_threshold"),
    ("call_merc_4", "call_merc_4_score", "call_merc_4_threshold"),
)
# (레거시) Call Merc UI: preview 라벨·접미사 var — main `_CALL_MERC_SETTINGS_SECTIONS`와 대응
CALL_MERC_PREVIEW_ATTR_BY_KIND: dict[str, str] = {
    "call_merc_1": "cm_pr_1",
    "call_merc_2": "cm_pr_2",
    "call_merc_3": "cm_pr_3",
    "call_merc_4": "cm_pr_4",
}
CALL_MERC_SUFFIX_ATTR_BY_KIND: dict[str, str] = {
    "call_merc_1": "_cm_sfx_1",
    "call_merc_2": "_cm_sfx_2",
    "call_merc_3": "_cm_sfx_3",
    "call_merc_4": "_cm_sfx_4",
}
