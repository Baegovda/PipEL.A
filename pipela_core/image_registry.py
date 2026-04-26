"""레지스트리(REG_SZ base64) ↔ PNG 파일 — 이미지 템플릿 저장/로드."""

from __future__ import annotations

import base64
import os
import winreg
from typing import Any

from pipela_core.registry_constants import REGISTRY_PATH
from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_core.vision_lazy import ensure_cv2_numpy_mss


def save_image_to_registry(image_path: str, registry_key_name: str) -> bool:
    """이미지 파일을 읽어 레지스트리에 base64로 저장."""
    try:
        if not os.path.exists(image_path):
            return False

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.CloseKey(key)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, registry_key_name, 0, winreg.REG_SZ, image_base64)
        winreg.CloseKey(key)

        return True
    except Exception as e:
        print(f"[{PIPELA_APP_DISPLAY_NAME}] 이미지 저장 FAIL: {e}")
        return False


def load_image_from_registry(
    registry_key_name: str,
    legacy_registry_key_name: str | None = None,
) -> Any:
    """레지스트리에서 base64 이미지를 디코드해 BGR ndarray. legacy 키는 구버전 호환."""
    cv2, np, _mss = ensure_cv2_numpy_mss()
    names_to_try = [registry_key_name]
    if legacy_registry_key_name:
        names_to_try.append(legacy_registry_key_name)
    for name in names_to_try:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
            image_base64 = winreg.QueryValueEx(key, name)[0]
            winreg.CloseKey(key)

            image_bytes = base64.b64decode(image_base64.encode("utf-8"))

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            return img
        except (FileNotFoundError, ValueError, Exception):
            continue
    return None


def load_image_data(
    image_path: str,
    registry_key_name: str,
    legacy_registry_key_name: str | None = None,
) -> Any:
    """레지스트리 우선, 없으면 파일 경로. 파일 로드 성공 시 레지에 저장 시도."""
    cv2, _np, _mss = ensure_cv2_numpy_mss()
    img = load_image_from_registry(registry_key_name, legacy_registry_key_name)
    if img is not None:
        return img

    if os.path.exists(image_path):
        img = cv2.imread(image_path)
        if img is not None:
            try:
                save_image_to_registry(image_path, registry_key_name)
            except Exception:
                pass
        return img

    return None


def load_image_data_if_path_changed(
    image_path: str | None,
    registry_key_name: str,
    last_path: str | None,
    cached: Any,
    *,
    legacy_registry_key_name: str | None = None,
) -> tuple[Any, str | None]:
    """경로가 바뀌었거나 캐시가 없을 때만 `load_image_data` 호출."""
    if image_path != last_path or cached is None:
        return (
            load_image_data(
                image_path or "",
                registry_key_name,
                legacy_registry_key_name,
            ),
            image_path,
        )
    return cached, last_path
