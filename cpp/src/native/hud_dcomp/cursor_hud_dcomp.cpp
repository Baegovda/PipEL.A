#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

#include <d2d1_1.h>
#include <d2d1helper.h>
#include <dcomp.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <wincodec.h>

#include <algorithm>
#include <mutex>

using Microsoft::WRL::ComPtr;

static const wchar_t* kWndClass = L"PipelaCursorHudDCompHost";

// Resource IDs (match `cursor_hud_dcomp.rc`)
static const int kResPngMove = 101;
static const int kResPngFire = 102;
static const int kResPngRide = 103;

struct HudState {
  std::mutex mu;
  HWND hwnd = nullptr;
  HWND anchor = nullptr;
  bool visible = false;
  int x = 0;
  int y = 0;
  int move_on = 0;
  int fire_on = 0;
  int ride_on = 0;
  RECT last_anchor_rc{};
  bool has_anchor_rc = false;

  // DComp / D2D objects
  ComPtr<ID3D11Device> d3d;
  ComPtr<ID3D11DeviceContext> d3d_ctx;
  ComPtr<IDXGIDevice> dxgi_dev;
  ComPtr<IDCompositionDevice> dcomp;
  ComPtr<IDCompositionTarget> target;
  ComPtr<IDCompositionVisual> visual;
  ComPtr<IDXGISwapChain1> swap_chain;
  ComPtr<ID2D1Factory1> d2d_factory;
  ComPtr<ID2D1Device> d2d_device;
  ComPtr<ID2D1DeviceContext> d2d_ctx;
  ComPtr<ID2D1Bitmap1> d2d_target;

  // WIC (PNG decode) + icon bitmaps (from embedded resources)
  ComPtr<IWICImagingFactory> wic;
  ComPtr<ID2D1Bitmap1> bmp_move;
  ComPtr<ID2D1Bitmap1> bmp_fire;
  ComPtr<ID2D1Bitmap1> bmp_ride;

  int canvas_w = 420;
  int canvas_h = 420;
};

static HudState g;

static HMODULE ThisModule() {
  HMODULE hm = nullptr;
  GetModuleHandleExW(
      GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
      (LPCWSTR)(&ThisModule),
      &hm);
  return hm;
}

static bool EnsureWic() {
  if (g.wic) return true;
  HRESULT hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  (void)hr;
  hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER,
                        IID_PPV_ARGS(&g.wic));
  return SUCCEEDED(hr) && g.wic;
}

static ComPtr<ID2D1Bitmap1> DecodePngResourceToD2DBitmap(int res_id) {
  ComPtr<ID2D1Bitmap1> out;
  if (!g.d2d_ctx) return out;
  if (!EnsureWic()) return out;

  HMODULE hm = ThisModule();
  if (!hm) return out;
  HRSRC hrsrc = FindResourceW(hm, MAKEINTRESOURCEW(res_id), RT_RCDATA);
  if (!hrsrc) return out;
  HGLOBAL hglob = LoadResource(hm, hrsrc);
  if (!hglob) return out;
  DWORD sz = SizeofResource(hm, hrsrc);
  if (sz == 0) return out;
  void* p = LockResource(hglob);
  if (!p) return out;

  ComPtr<IWICStream> stream;
  HRESULT hr = g.wic->CreateStream(&stream);
  if (FAILED(hr) || !stream) return out;
  hr = stream->InitializeFromMemory((BYTE*)p, sz);
  if (FAILED(hr)) return out;

  ComPtr<IWICBitmapDecoder> dec;
  hr = g.wic->CreateDecoderFromStream(stream.Get(), nullptr, WICDecodeMetadataCacheOnLoad, &dec);
  if (FAILED(hr) || !dec) return out;

  ComPtr<IWICBitmapFrameDecode> frame;
  hr = dec->GetFrame(0, &frame);
  if (FAILED(hr) || !frame) return out;

  ComPtr<IWICFormatConverter> conv;
  hr = g.wic->CreateFormatConverter(&conv);
  if (FAILED(hr) || !conv) return out;

  hr = conv->Initialize(frame.Get(), GUID_WICPixelFormat32bppPBGRA, WICBitmapDitherTypeNone,
                        nullptr, 0.0f, WICBitmapPaletteTypeCustom);
  if (FAILED(hr)) return out;

  ComPtr<ID2D1Bitmap> bmp0;
  hr = g.d2d_ctx->CreateBitmapFromWicBitmap(conv.Get(), nullptr, &bmp0);
  if (FAILED(hr) || !bmp0) return out;
  bmp0.As(&out);
  return out;
}

static void EnsureIconBitmaps() {
  if (g.bmp_move && g.bmp_fire && g.bmp_ride) return;
  if (!g.d2d_ctx) return;
  if (!g.bmp_move) g.bmp_move = DecodePngResourceToD2DBitmap(kResPngMove);
  if (!g.bmp_fire) g.bmp_fire = DecodePngResourceToD2DBitmap(kResPngFire);
  if (!g.bmp_ride) g.bmp_ride = DecodePngResourceToD2DBitmap(kResPngRide);
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM w, LPARAM l) {
  switch (msg) {
    case WM_NCHITTEST:
      return HTTRANSPARENT;  // click-through
    case WM_ERASEBKGND:
      return 1;
    case WM_DESTROY:
      return 0;
    default:
      return DefWindowProcW(hwnd, msg, w, l);
  }
}

static bool EnsureWindow() {
  if (g.hwnd) return true;
  HINSTANCE hinst = GetModuleHandleW(nullptr);

  WNDCLASSEXW wc{};
  wc.cbSize = sizeof(wc);
  wc.hInstance = hinst;
  wc.lpszClassName = kWndClass;
  wc.lpfnWndProc = WndProc;
  wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
  wc.style = CS_HREDRAW | CS_VREDRAW;

  RegisterClassExW(&wc);

  DWORD ex = WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE;
  DWORD st = WS_POPUP;
  HWND hwnd = CreateWindowExW(
      ex,
      kWndClass,
      L"",
      st,
      -10000, -10000, 1, 1,
      nullptr,
      nullptr,
      hinst,
      nullptr);
  if (!hwnd) return false;

  // fully transparent; DComp swapchain is premultiplied alpha
  SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA);
  g.hwnd = hwnd;
  return true;
}

static bool UpdateAnchorRect() {
  if (!g.anchor) return false;
  if (!IsWindow(g.anchor)) {
    g.has_anchor_rc = false;
    return false;
  }
  RECT rc{};
  if (!GetWindowRect(g.anchor, &rc)) return false;
  bool changed = !g.has_anchor_rc || memcmp(&rc, &g.last_anchor_rc, sizeof(RECT)) != 0;
  if (changed) {
    g.last_anchor_rc = rc;
    g.has_anchor_rc = true;
  }
  return changed;
}

static void ResetSwapchainAndTarget() {
  g.d2d_target.Reset();
  g.swap_chain.Reset();
  // Invalidate icon bitmaps tied to this device context target.
  g.bmp_move.Reset();
  g.bmp_fire.Reset();
  g.bmp_ride.Reset();
}

static void HideHostNow() {
  if (!g.hwnd) return;
  ShowWindow(g.hwnd, SW_HIDE);
  SetWindowPos(g.hwnd, HWND_TOPMOST, -10000, -10000, 1, 1, SWP_NOACTIVATE | SWP_NOZORDER);
}

static void EnsureHostPlaced() {
  if (!g.hwnd) return;
  if (!g.visible || !g.has_anchor_rc) {
    HideHostNow();
    return;
  }
  const RECT rc = g.last_anchor_rc;
  const int w = (int)(rc.right - rc.left);
  const int h = (int)(rc.bottom - rc.top);
  SetWindowPos(g.hwnd, HWND_TOPMOST, rc.left, rc.top, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW);
}

static bool RecreateD2DTarget() {
  if (!g.swap_chain || !g.d2d_ctx) return false;
  g.d2d_target.Reset();
  ComPtr<IDXGISurface> surf;
  HRESULT hr = g.swap_chain->GetBuffer(0, IID_PPV_ARGS(&surf));
  if (FAILED(hr)) return false;
  float dpiX = 96.0f;
  float dpiY = 96.0f;
  D2D1_BITMAP_PROPERTIES1 props = D2D1::BitmapProperties1(
      D2D1_BITMAP_OPTIONS_TARGET | D2D1_BITMAP_OPTIONS_CANNOT_DRAW,
      D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED),
      dpiX,
      dpiY);
  hr = g.d2d_ctx->CreateBitmapFromDxgiSurface(surf.Get(), &props, &g.d2d_target);
  if (FAILED(hr)) return false;
  g.d2d_ctx->SetTarget(g.d2d_target.Get());
  // Target recreation may invalidate cached device-context dependent resources; re-decode on demand.
  g.bmp_move.Reset();
  g.bmp_fire.Reset();
  g.bmp_ride.Reset();
  return true;
}

static bool EnsureSwapchainAndD2D() {
  if (g.swap_chain && g.d2d_ctx && g.d2d_target) return true;
  if (!g.dcomp || !g.dxgi_dev) return false;

  HRESULT hr = S_OK;
  if (!g.d2d_factory) {
    D2D1_FACTORY_OPTIONS opts{};
    hr = D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, __uuidof(ID2D1Factory1), &opts,
                           (void**)g.d2d_factory.GetAddressOf());
    if (FAILED(hr)) return false;
  }
  if (!g.d2d_device) {
    hr = g.d2d_factory->CreateDevice(g.dxgi_dev.Get(), &g.d2d_device);
    if (FAILED(hr)) return false;
  }
  if (!g.d2d_ctx) {
    hr = g.d2d_device->CreateDeviceContext(D2D1_DEVICE_CONTEXT_OPTIONS_NONE, &g.d2d_ctx);
    if (FAILED(hr)) return false;
  }

  if (!g.swap_chain) {
    ComPtr<IDXGIAdapter> adapter;
    {
      ComPtr<IDXGIDevice> dxgi = g.dxgi_dev;
      ComPtr<IDXGIAdapter> ad;
      hr = dxgi->GetAdapter(&ad);
      if (FAILED(hr)) return false;
      adapter = ad;
    }
    ComPtr<IDXGIFactory2> factory;
    hr = CreateDXGIFactory1(IID_PPV_ARGS(&factory));
    if (FAILED(hr)) return false;

    DXGI_SWAP_CHAIN_DESC1 desc{};
    desc.Width = (UINT)g.canvas_w;
    desc.Height = (UINT)g.canvas_h;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.Stereo = FALSE;
    desc.SampleDesc.Count = 1;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.BufferCount = 2;
    desc.Scaling = DXGI_SCALING_STRETCH;
    desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
    desc.AlphaMode = DXGI_ALPHA_MODE_PREMULTIPLIED;
    desc.Flags = 0;

    hr = factory->CreateSwapChainForComposition(g.d3d.Get(), &desc, nullptr, &g.swap_chain);
    if (FAILED(hr)) return false;
    hr = g.visual->SetContent(g.swap_chain.Get());
    if (FAILED(hr)) return false;
  }

  if (!RecreateD2DTarget()) return false;
  return true;
}

static bool InitDComp() {
  if (g.dcomp) return true;
  if (!EnsureWindow()) return false;

  HRESULT hr = S_OK;

  // D3D11 device (BGRA for D2D interop)
  UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
  D3D_FEATURE_LEVEL fls[] = {D3D_FEATURE_LEVEL_11_1, D3D_FEATURE_LEVEL_11_0};
  D3D_FEATURE_LEVEL fl{};
  hr = D3D11CreateDevice(
      nullptr,
      D3D_DRIVER_TYPE_HARDWARE,
      nullptr,
      flags,
      fls,
      ARRAYSIZE(fls),
      D3D11_SDK_VERSION,
      &g.d3d,
      &fl,
      &g.d3d_ctx);
  if (FAILED(hr)) return false;
  hr = g.d3d.As(&g.dxgi_dev);
  if (FAILED(hr)) return false;

  // DComp device
  hr = DCompositionCreateDevice(g.dxgi_dev.Get(), IID_PPV_ARGS(&g.dcomp));
  if (FAILED(hr)) return false;

  hr = g.dcomp->CreateTargetForHwnd(g.hwnd, TRUE, &g.target);
  if (FAILED(hr)) return false;
  hr = g.dcomp->CreateVisual(&g.visual);
  if (FAILED(hr)) return false;

  hr = g.target->SetRoot(g.visual.Get());
  if (FAILED(hr)) return false;
  if (!EnsureSwapchainAndD2D()) return false;

  return true;
}

static void Render() {
  if (!g.d2d_ctx || !g.swap_chain) return;
  g.d2d_ctx->BeginDraw();
  g.d2d_ctx->Clear(D2D1::ColorF(0, 0, 0, 0));

  auto mkBrush = [&](float r, float gg, float b, float a) -> ComPtr<ID2D1SolidColorBrush> {
    ComPtr<ID2D1SolidColorBrush> br;
    g.d2d_ctx->CreateSolidColorBrush(D2D1::ColorF(r, gg, b, a), &br);
    return br;
  };
  const bool any_on = (g.move_on != 0) || (g.fire_on != 0) || (g.ride_on != 0);
  if (!any_on) {
    HRESULT hr = g.d2d_ctx->EndDraw();
    if (FAILED(hr)) {
      if (hr == D2DERR_RECREATE_TARGET) {
        ResetSwapchainAndTarget();
        EnsureSwapchainAndD2D();
      }
      return;
    }
    HRESULT pr = g.swap_chain->Present(0, 0);
    if (FAILED(pr)) {
      ResetSwapchainAndTarget();
      EnsureSwapchainAndD2D();
      return;
    }
    if (g.dcomp) g.dcomp->Commit();
    return;
  }

  EnsureIconBitmaps();

  const float cx = (float)g.canvas_w * 0.5f;
  const float cy = (float)g.canvas_h * 0.5f;

  auto drawPngCenteredFitAspect = [&](ID2D1Bitmap1* bmp, float x, float y, float max_side) -> bool {
    if (!bmp) return false;
    const D2D1_SIZE_F sz = bmp->GetSize();
    const float bw = (sz.width > 0.0f) ? sz.width : 1.0f;
    const float bh = (sz.height > 0.0f) ? sz.height : 1.0f;
    const float s = (max_side > 1.0f) ? max_side : 1.0f;
    const float k = (std::min)(s / bw, s / bh);
    const float dw = bw * k;
    const float dh = bh * k;
    float l = x - dw * 0.5f;
    float t = y - dh * 0.5f;
    float r2 = x + dw * 0.5f;
    float b2 = y + dh * 0.5f;
    // Pixel-snap for tiny icons to reduce blur.
    if (max_side <= 56.0f) {
      l = roundf(l);
      t = roundf(t);
      r2 = roundf(r2);
      b2 = roundf(b2);
    }
    D2D1_BITMAP_INTERPOLATION_MODE interp = D2D1_BITMAP_INTERPOLATION_MODE_LINEAR;
    if (max_side <= 56.0f) {
      interp = D2D1_BITMAP_INTERPOLATION_MODE_NEAREST_NEIGHBOR;
    }
    g.d2d_ctx->DrawBitmap(bmp, D2D1::RectF(l, t, r2, b2), 1.0f, interp, nullptr);
    return true;
  };

  // Tunables: icon spacing around cursor (canvas space)
  const float dx_lr = 88.0f;
  const float dy_ride = 96.0f;
  // Per-icon nudges (relative to cursor anchor) — requested tuning
  const float nudge_lr_x = 20.0f;
  const float nudge_lr_y = 30.0f;
  const float nudge_ride_x = 30.0f;
  const float nudge_ride_y = 0.0f;

  const float xMove = cx - dx_lr + nudge_lr_x;
  const float xFire = cx + dx_lr + nudge_lr_x;
  const float yMid = cy + nudge_lr_y;
  const float xRide = cx + nudge_ride_x;
  const float yRide = cy + dy_ride + nudge_ride_y;

  // Prefer embedded PNGs (no badge/background). Fallback per-icon to vector if decode failed.
  const float pngSide = 48.0f;
  const bool move_png_ok = g.move_on && drawPngCenteredFitAspect(g.bmp_move.Get(), xMove, yMid, pngSide);
  const bool fire_png_ok = g.fire_on && drawPngCenteredFitAspect(g.bmp_fire.Get(), xFire, yMid, pngSide);
  const bool ride_png_ok = g.ride_on && drawPngCenteredFitAspect(g.bmp_ride.Get(), xRide, yRide, pngSide);

  // Move icon: right-pointing arrow
  if (g.move_on) {
    if (move_png_ok) {
      // already drawn as PNG
    } else {
    ComPtr<ID2D1PathGeometry> geo;
    if (SUCCEEDED(g.d2d_factory->CreatePathGeometry(&geo))) {
      ComPtr<ID2D1GeometrySink> sink;
      if (SUCCEEDED(geo->Open(&sink))) {
        const float s = 46.0f;
        D2D1_POINT_2F p0 = D2D1::Point2F(xMove - s * 0.65f, yMid - s * 0.35f);
        D2D1_POINT_2F p1 = D2D1::Point2F(xMove + s * 0.25f, yMid - s * 0.35f);
        D2D1_POINT_2F p2 = D2D1::Point2F(xMove + s * 0.25f, yMid - s * 0.70f);
        D2D1_POINT_2F p3 = D2D1::Point2F(xMove + s * 0.95f, yMid);
        D2D1_POINT_2F p4 = D2D1::Point2F(xMove + s * 0.25f, yMid + s * 0.70f);
        D2D1_POINT_2F p5 = D2D1::Point2F(xMove + s * 0.25f, yMid + s * 0.35f);
        D2D1_POINT_2F p6 = D2D1::Point2F(xMove - s * 0.65f, yMid + s * 0.35f);
        sink->BeginFigure(p0, D2D1_FIGURE_BEGIN_FILLED);
        D2D1_POINT_2F pts[] = {p1, p2, p3, p4, p5, p6};
        sink->AddLines(pts, ARRAYSIZE(pts));
        sink->EndFigure(D2D1_FIGURE_END_CLOSED);
        sink->Close();
      }
      auto br = mkBrush(0.0f, 0.0f, 0.0f, 0.55f);
      g.d2d_ctx->FillGeometry(geo.Get(), br.Get());
    }
    }
  }

  // Fire icon: 8-ray starburst
  if (g.fire_on) {
    if (fire_png_ok) {
      // already drawn as PNG
    } else {
    auto br = mkBrush(0.0f, 0.0f, 0.0f, 0.55f);
    const float s = 46.0f;
    for (int i = 0; i < 8; i++) {
      const float a = (3.1415926f * 2.0f) * (float)i / 8.0f;
      const float c = cosf(a);
      const float sn = sinf(a);
      D2D1_POINT_2F a0 = D2D1::Point2F(xFire + c * (s * 0.15f), yMid + sn * (s * 0.15f));
      D2D1_POINT_2F a1 = D2D1::Point2F(xFire + c * (s * 0.95f), yMid + sn * (s * 0.95f));
      g.d2d_ctx->DrawLine(a0, a1, br.Get(), 8.0f, nullptr);
    }
    }
  }

  // Ride icon: simple chopper-like silhouette
  if (g.ride_on) {
    if (ride_png_ok) {
      // already drawn as PNG
    } else {
    auto br = mkBrush(0.0f, 0.0f, 0.0f, 0.55f);
    const float s = 60.0f;
    // wheels
    g.d2d_ctx->DrawEllipse(D2D1::Ellipse(D2D1::Point2F(xRide - s * 0.55f, yRide + s * 0.25f), 18.0f, 18.0f), br.Get(), 8.0f);
    g.d2d_ctx->DrawEllipse(D2D1::Ellipse(D2D1::Point2F(xRide + s * 0.55f, yRide + s * 0.25f), 18.0f, 18.0f), br.Get(), 8.0f);
    // frame
    g.d2d_ctx->DrawLine(D2D1::Point2F(xRide - s * 0.55f, yRide + s * 0.25f), D2D1::Point2F(xRide, yRide - s * 0.05f), br.Get(), 10.0f);
    g.d2d_ctx->DrawLine(D2D1::Point2F(xRide, yRide - s * 0.05f), D2D1::Point2F(xRide + s * 0.55f, yRide + s * 0.25f), br.Get(), 10.0f);
    // handlebar
    g.d2d_ctx->DrawLine(D2D1::Point2F(xRide + s * 0.05f, yRide - s * 0.20f), D2D1::Point2F(xRide + s * 0.38f, yRide - s * 0.38f), br.Get(), 7.0f);
    // seat
    D2D1_RECT_F seat = D2D1::RectF(xRide - s * 0.10f, yRide - s * 0.25f, xRide + s * 0.28f, yRide - s * 0.10f);
    g.d2d_ctx->FillRectangle(seat, br.Get());
    }
  }

  HRESULT hr = g.d2d_ctx->EndDraw();
  if (FAILED(hr)) {
    if (hr == D2DERR_RECREATE_TARGET) {
      ResetSwapchainAndTarget();
      EnsureSwapchainAndD2D();
    }
    return;
  }
  HRESULT pr = g.swap_chain->Present(0, 0);
  if (FAILED(pr)) {
    ResetSwapchainAndTarget();
    EnsureSwapchainAndD2D();
    return;
  }
  if (g.dcomp) g.dcomp->Commit();
}

static void ApplyPosition() {
  if (!g.visual) return;
  if (!g.has_anchor_rc) return;
  // Place the canvas centered at cursor, inside the fixed host window (anchor rect origin).
  const int ax = g.last_anchor_rc.left;
  const int ay = g.last_anchor_rc.top;
  const int anchor_nudge_x = 0;
  const int anchor_nudge_y = 0;
  const float ox = (float)(g.x + anchor_nudge_x - ax - g.canvas_w / 2);
  const float oy = (float)(g.y + anchor_nudge_y - ay - g.canvas_h / 2);
  g.visual->SetOffsetX(ox);
  g.visual->SetOffsetY(oy);
}

extern "C" {

__declspec(dllexport) int hud_init(unsigned long long anchor_hwnd) {
  std::lock_guard<std::mutex> lk(g.mu);
  g.anchor = (HWND)(uintptr_t)anchor_hwnd;
  if (!InitDComp()) return 0;
  UpdateAnchorRect();
  g.visible = false;
  EnsureHostPlaced();
  Render();
  return 1;
}

__declspec(dllexport) void hud_set_visible(int visible) {
  std::lock_guard<std::mutex> lk(g.mu);
  g.visible = visible ? true : false;
  UpdateAnchorRect();
  if (g.visible && !g.has_anchor_rc) {
    g.visible = false;
    HideHostNow();
    return;
  }
  EnsureHostPlaced();
  if (g.visible) {
    ApplyPosition();
    Render();
  }
}

__declspec(dllexport) void hud_set_icons(int move_on, int fire_on, int ride_on) {
  std::lock_guard<std::mutex> lk(g.mu);
  g.move_on = move_on;
  g.fire_on = fire_on;
  g.ride_on = ride_on;
  if (g.visible) Render();
}

__declspec(dllexport) void hud_set_position(int x_phys, int y_phys) {
  std::lock_guard<std::mutex> lk(g.mu);
  g.x = x_phys;
  g.y = y_phys;
  const bool anchor_changed = UpdateAnchorRect();
  if (!g.has_anchor_rc) {
    HideHostNow();
    return;
  }
  if (anchor_changed) {
    EnsureHostPlaced();
  }
  if (!g.visible) {
    return;
  }
  // AGENT: Position-only — DComp visual offset; skip full D2D redraw (hook-rate safe).
  ApplyPosition();
  if (g.dcomp) {
    g.dcomp->Commit();
  }
}

__declspec(dllexport) void hud_shutdown() {
  std::lock_guard<std::mutex> lk(g.mu);
  g.visible = false;
  HideHostNow();
  if (g.hwnd) {
    DestroyWindow(g.hwnd);
    g.hwnd = nullptr;
  }
  g.anchor = nullptr;
  g.has_anchor_rc = false;
  g.bmp_move.Reset();
  g.bmp_fire.Reset();
  g.bmp_ride.Reset();
  g.wic.Reset();
  g.d2d_target.Reset();
  g.d2d_ctx.Reset();
  g.d2d_device.Reset();
  g.d2d_factory.Reset();
  g.swap_chain.Reset();
  g.visual.Reset();
  g.target.Reset();
  g.dcomp.Reset();
  g.dxgi_dev.Reset();
  g.d3d_ctx.Reset();
  g.d3d.Reset();
}

}  // extern "C"

