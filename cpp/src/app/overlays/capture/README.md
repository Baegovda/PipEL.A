# Capture overlay subsystem (C++)

Unified template capture, ROI select, and region preview.

| Module | Role |
|--------|------|
| `anchor_overlay_geometry` | HWND client rect → Qt logical geometry (shared) |
| `capture_session` | Freeze snapshot, crop, persist (no QWidget) |
| `capture_overlay_view` | Full-screen drag UI (single instance) |
| `capture_confirm_card` | Post-drag save confirm (`CardFramelessDialog`) |
| `region_preview_view` | Saved ROI pulse preview |
| `capture_overlay_service` | FSM + orchestration |

Public API: `TemplateOverlayController` (unchanged signatures).
