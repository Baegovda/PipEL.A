#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "pipela/core/kill_counter/tier_data.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/snapshot.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/version.hpp"
#include "pipela/core/vision/capture.hpp"
#include "pipela/core/vision/template_match.hpp"
#include "pipela/core/win32/dock_layout.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_runtime.hpp"

namespace py = pybind11;
using pipela::core::registry::RegistrySnapshot;
using pipela::core::state::AppState;
using pipela::core::state::StateValue;
using pipela::core::workers::WorkerContext;
using pipela::core::workers::WorkerRuntime;

namespace {

py::object stateValueToPy(const StateValue& value) {
    if (std::holds_alternative<std::monostate>(value)) {
        return py::none();
    }
    if (const auto* b = std::get_if<bool>(&value)) {
        return py::bool_(*b);
    }
    if (const auto* i = std::get_if<int>(&value)) {
        return py::int_(*i);
    }
    if (const auto* l = std::get_if<std::int64_t>(&value)) {
        return py::int_(*l);
    }
    if (const auto* d = std::get_if<double>(&value)) {
        return py::float_(*d);
    }
    if (const auto* s = std::get_if<std::string>(&value)) {
        return py::str(*s);
    }
    return py::none();
}

std::optional<StateValue> pyToStateValue(const py::handle& obj) {
    if (obj.is_none()) {
        return std::nullopt;
    }
    if (py::isinstance<py::bool_>(obj)) {
        return StateValue{obj.cast<bool>()};
    }
    if (py::isinstance<py::int_>(obj)) {
        return StateValue{obj.cast<std::int64_t>()};
    }
    if (py::isinstance<py::float_>(obj)) {
        return StateValue{obj.cast<double>()};
    }
    if (py::isinstance<py::str>(obj)) {
        return StateValue{obj.cast<std::string>()};
    }
    return std::nullopt;
}

RegistrySnapshot snapshotFromPyDict(const py::dict& values) {
    RegistrySnapshot snap;
    for (const auto& item : values) {
        const auto key = py::str(item.first).cast<std::string>();
        const py::handle val = item.second;
        if (val.is_none()) {
            continue;
        }
        if (py::isinstance<py::bool_>(val)) {
            snap.setBool(key, val.cast<bool>());
        } else if (py::isinstance<py::int_>(val)) {
            snap.setInt(key, val.cast<int>());
        } else if (py::isinstance<py::float_>(val)) {
            snap.setDouble(key, val.cast<double>());
        } else {
            snap.set(key, py::str(val));
        }
    }
    return snap;
}

}  // namespace

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

    py::class_<RegistrySnapshot>(m, "RegistrySnapshot")
        .def(py::init<>())
        .def("set", &RegistrySnapshot::set)
        .def("set_bool", &RegistrySnapshot::setBool)
        .def("set_int", &RegistrySnapshot::setInt)
        .def("set_double", &RegistrySnapshot::setDouble)
        .def("has", &RegistrySnapshot::has)
        .def("snapshot_bool", &RegistrySnapshot::snapshotBool, py::arg("key"), py::arg("fallback") = false)
        .def("snapshot_int", &RegistrySnapshot::snapshotInt, py::arg("key"), py::arg("fallback") = 0)
        .def("snapshot_float", &RegistrySnapshot::snapshotFloat, py::arg("key"), py::arg("fallback") = 0.0)
        .def("builtin_key_names", &RegistrySnapshot::builtinKeyNames)
        .def_static("from_string_map", &RegistrySnapshot::fromStringMap)
        .def_static("from_dict", [](const py::dict& values) { return snapshotFromPyDict(values); });

    py::class_<AppState>(m, "AppState")
        .def(py::init<>())
        .def("seed_from_defaults", &AppState::seedFromDefaults)
        .def("has", &AppState::has)
        .def(
            "get",
            [](const AppState& state, const std::string& key) -> py::object {
                const auto value = state.get(key);
                if (!value) {
                    return py::none();
                }
                return stateValueToPy(*value);
            },
            py::arg("key"))
        .def(
            "set",
            [](AppState& state, const std::string& key, py::object value) -> bool {
                const auto parsed = pyToStateValue(value);
                if (!parsed) {
                    return false;
                }
                return state.set(key, *parsed);
            },
            py::arg("key"),
            py::arg("value"))
        .def("increment_int", &AppState::incrementInt, py::arg("key"), py::arg("delta") = 1);

    py::class_<WorkerRuntime>(m, "WorkerRuntime")
        .def(py::init<AppState&>())
        .def("start_all", &WorkerRuntime::startAll)
        .def("stop_all", &WorkerRuntime::stopAll)
        .def("running", &WorkerRuntime::running);

    m.def("set_snapshot_provider", [](py::object callback) {
        WorkerContext::setSnapshotProvider([callback = std::move(callback)]() {
            py::gil_scoped_acquire gil;
            py::dict values = callback().cast<py::dict>();
            return snapshotFromPyDict(values);
        });
    });

    m.def("set_template_bgr_loader", [](py::object callback) {
        WorkerContext::setTemplateBgrLoader([callback = std::move(callback)](const std::string& key) {
            py::gil_scoped_acquire gil;
            py::object result = callback(key);
            if (result.is_none()) {
                return std::optional<pipela::core::vision::BgrImage>{};
            }
            const py::tuple tup = result.cast<py::tuple>();
            if (tup.size() != 3) {
                return std::optional<pipela::core::vision::BgrImage>{};
            }
            const py::bytes raw = tup[0].cast<py::bytes>();
            const int w = tup[1].cast<int>();
            const int h = tup[2].cast<int>();
            const std::string bytes = raw;
            pipela::core::vision::BgrImage image;
            image.width = w;
            image.height = h;
            image.bytes.assign(reinterpret_cast<const unsigned char*>(bytes.data()),
                               reinterpret_cast<const unsigned char*>(bytes.data()) + bytes.size());
            return std::optional<pipela::core::vision::BgrImage>{std::move(image)};
        });
    });

#if defined(PIPELA_HAS_OPENCV)
    m.def("load_bgr_from_path", [](const std::string& path) {
        const auto image = pipela::core::vision::loadBgrFromPath(path);
        if (!image) {
            return py::make_tuple(py::none(), 0, 0);
        }
        return py::make_tuple(
            py::bytes(reinterpret_cast<const char*>(image->bytes.data()), image->bytes.size()),
            image->width,
            image->height);
    });
#endif

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
