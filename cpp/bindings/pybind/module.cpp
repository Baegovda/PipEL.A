#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "pipela/core/kill_counter/tier_data.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/version.hpp"
#include "pipela/core/vision/template_match.hpp"
#include "pipela/core/win32/dock_layout.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/workers/worker_runtime.hpp"

namespace py = pybind11;
using pipela::core::state::AppState;
using pipela::core::workers::WorkerRuntime;

PYBIND11_MODULE(pipela_native, m) {
    m.doc() = "Pipela native core (C++ / pybind11)";
    m.attr("__version__") = pipela::core::appVersion();

    m.def("app_version", &pipela::core::appVersion);
    m.def("parse_bool", &pipela::core::registry::parseBool);
    m.def("clamp_match_threshold", &pipela::core::registry::clampMatchThreshold01);
    m.def("load_registry_strings", &pipela::core::registry::loadAllStringValues);
    m.def("rank_tier_count", &pipela::core::kill_counter::rankTierCount);
    m.def("load_schema", &pipela::core::registry::loadSchemaFromFile, py::arg("path"));
    m.def("capture_client_bgr", [](std::intptr_t hwnd) {
        int w = 0;
        int h = 0;
        auto bytes = pipela::core::win32::captureClientBgr(hwnd, &w, &h);
        return py::make_tuple(py::bytes(reinterpret_cast<const char*>(bytes.data()), bytes.size()), w, h);
    });
    m.def("builtin_rank_rows", []() {
        py::list out;
        for (const auto& r : pipela::core::kill_counter::builtinRankTableRows()) {
            py::dict row;
            row["num"] = r.num;
            row["title"] = r.title;
            row["point"] = r.point;
            if (r.next_cap.has_value()) {
                row["next_cap"] = *r.next_cap;
            } else {
                row["next_cap"] = py::none();
            }
            out.append(row);
        }
        return out;
    });

    py::class_<AppState>(m, "AppState")
        .def(py::init<>())
        .def("seed_from_defaults", &AppState::seedFromDefaults)
        .def("has", &AppState::has)
        .def("increment_int", &AppState::incrementInt, py::arg("key"), py::arg("delta") = 1);

    py::class_<WorkerRuntime>(m, "WorkerRuntime")
        .def(py::init<AppState&>())
        .def("start_all", &WorkerRuntime::startAll)
        .def("stop_all", &WorkerRuntime::stopAll)
        .def("running", &WorkerRuntime::running);

    m.def(
        "clamp_dock_logical_geometry",
        [](int x, int y, int w, int h) {
            return pipela::core::win32::clampDockLogicalGeometry(x, y, w, h);
        },
        py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"));

    py::class_<pipela::core::vision::MatchResult>(m, "MatchResult")
        .def_readonly("score", &pipela::core::vision::MatchResult::score)
        .def_readonly("top_left_x", &pipela::core::vision::MatchResult::top_left_x)
        .def_readonly("top_left_y", &pipela::core::vision::MatchResult::top_left_y)
        .def_readonly("valid", &pipela::core::vision::MatchResult::valid);

    m.def(
        "match_template_ccoeff_normed_max",
        [](py::bytes screen, int sw, int sh, int sstride, py::bytes templ, int tw, int th, int tstride) {
            std::string s = screen;
            std::string t = templ;
            return pipela::core::vision::matchTemplateCcoeffNormedMax(
                reinterpret_cast<const unsigned char*>(s.data()), sw, sh, sstride,
                reinterpret_cast<const unsigned char*>(t.data()), tw, th, tstride);
        },
        py::arg("screen_bgr"), py::arg("screen_w"), py::arg("screen_h"), py::arg("screen_stride"),
        py::arg("template_bgr"), py::arg("template_w"), py::arg("template_h"),
        py::arg("template_stride"));
}
