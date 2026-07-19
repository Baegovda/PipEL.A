#pragma once

#include <map>
#include <optional>
#include <string>
#include <vector>

namespace pipela::core::registry {

struct SchemaEntry {
    std::string registry_key;
    std::string value_type;
    std::optional<std::string> global_name;
};

struct SchemaDocument {
    std::string registry_path;
    int schema_version{0};
    std::vector<SchemaEntry> entries;
};

// Load HKCU\Software\Pipela values as REG_SZ strings (Windows only).
std::map<std::string, std::string> loadAllStringValues();

// Parse registry/schema.json bundled beside repo root.
SchemaDocument loadSchemaFromRepo(const std::string& repo_root);

}  // namespace pipela::core::registry
