"""드래그 캡처 확인 후 PNG를 레지·경로 전역에 반영."""

from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping

from PIL import Image

from pipela_core.image_registry import load_image_data, save_image_to_registry
from pipela_core.paths import template_capture_user_storage_dir
from pipela_core.template_capture_catalog import (
    TEMPLATE_CAPTURE_KIND_PATH_BINDING,
    get_template_capture_kind_meta,
)
from pipela_core.vision_lazy import ensure_cv2_numpy_mss


def template_capture_output_path_for_kind(kind: str) -> str | None:
    """캡처 확인 후 저장할 PNG 절대 경로(kind별 파일명). kind 미지원 시 None."""
    meta = get_template_capture_kind_meta(kind)
    if meta is None:
        return None
    fn, _, _ = meta
    return os.path.join(template_capture_user_storage_dir(), fn)


def write_pil_rgb_to_png_cv2(pil_image: Image.Image, out_path: str) -> bool:
    """PIL RGB → BGR 후 cv2.imwrite."""
    cv2, np, _ = ensure_cv2_numpy_mss()
    rgb = np.array(pil_image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bool(cv2.imwrite(out_path, bgr))


def apply_template_capture_png(
    kind: str,
    abs_png_path: str,
    g: MutableMapping[str, Any],
) -> bool:
    """PNG 경로를 해당 기능의 매칭 템플릿으로 등록(레지 이미지 데이터 + 경로 전역)."""
    meta = get_template_capture_kind_meta(kind)
    bind = TEMPLATE_CAPTURE_KIND_PATH_BINDING.get(kind)
    if meta is None or bind is None or not os.path.isfile(abs_png_path):
        return False
    _fname, reg_key, _label = meta
    ok = save_image_to_registry(abs_png_path, reg_key)
    path_attr, data_attr = bind
    g[path_attr] = abs_png_path
    if data_attr is not None:
        g[data_attr] = bool(ok)
    return True


def template_capture_load_existing_pil(
    kind: str,
    g: Mapping[str, Any],
) -> Image.Image | None:
    """현재 지정된 매칭 템플릿을 PIL RGB로. 없으면 None."""
    cv2, _, _ = ensure_cv2_numpy_mss()
    meta = get_template_capture_kind_meta(kind)
    bind = TEMPLATE_CAPTURE_KIND_PATH_BINDING.get(kind)
    if meta is None or bind is None:
        return None
    _, reg_key, _ = meta
    path = g.get(bind[0])
    if not path:
        return None
    bgr = load_image_data(str(path), reg_key)
    if bgr is None:
        return None
    try:
        return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    except Exception:
        return None
