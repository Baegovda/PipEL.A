#!/usr/bin/env python3
"""Golden: Python vs C++ template match scores (synthetic BGR if no assets)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PIPELA_NATIVE_CORE", "1")


def _synthetic_pair():
    import numpy as np

    screen = np.zeros((120, 160, 3), dtype=np.uint8)
    templ = np.full((20, 30, 3), 200, dtype=np.uint8)
    screen[40:60, 50:80] = templ
    return screen, templ


def main() -> int:
    from pipela_core.template_matching import match_template_ccoeff_normed_max
    from pipela_core.vision_lazy import ensure_cv2_numpy_mss

    screen, templ = _synthetic_pair()
    py_score, py_loc = match_template_ccoeff_normed_max(screen, templ)
    cv2, _, _ = ensure_cv2_numpy_mss()
    pure_score, pure_loc = (0.0, None)
    if cv2 is not None:
        result = cv2.matchTemplate(screen, templ, cv2.TM_CCOEFF_NORMED)
        _, pure_score, _, pure_loc = cv2.minMaxLoc(result)
    print(f"python path score={py_score:.6f} loc={py_loc}")
    print(f"opencv pure score={pure_score:.6f} loc={pure_loc}")
    if abs(float(py_score) - float(pure_score)) > 1e-5:
        print("FAIL: score drift > 1e-5")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
