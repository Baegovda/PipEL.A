#include <catch2/catch_test_macros.hpp>

#include "pipela/core/update/manifest.hpp"

TEST_CASE("version tuple compare", "[golden][update]") {
    using pipela::core::update::compareVersions;
    REQUIRE(compareVersions("0.9.13", "0.10.0") < 0);
    REQUIRE(compareVersions("1.2.3", "1.2.3") == 0);
    REQUIRE(compareVersions("1.2.3-beta", "1.2.3") == 0);
    REQUIRE(compareVersions("2.0.0", "1.9.99") > 0);
}

TEST_CASE("manifest url helpers", "[golden][update]") {
    nlohmann::json obj = {{"download_url", "https://example.com/a.exe"},
                          {"release_url", "https://example.com/release"}};
    REQUIRE(pipela::core::update::manifestDownloadUrl(obj) == "https://example.com/a.exe");
    REQUIRE(pipela::core::update::manifestBrowserUrl(obj) == "https://example.com/release");
}
