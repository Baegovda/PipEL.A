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
    std::optional<std::string> default_value;
};

struct SchemaDocument {
    std::string registry_path;
    int schema_version{0};
    int entry_count{0};
    std::vector<SchemaEntry> entries;
};

// Load HKCU\Software\Pipela values as REG_SZ strings (Windows only).
std::map<std::string, std::string> loadAllStringValues();

// Write one REG_SZ value (creates Software\Pipela if missing). Returns false on failure.
bool saveStringValue(const std::string& name, const std::string& value);

// Bool as lowercase "true"/"false" (matches merc_fire save style; parseBool accepts both).
bool saveBoolValue(const std::string& name, bool value);

// Parse registry/schema.json (nlohmann/json).
SchemaDocument loadSchemaFromFile(const std::string& path);

}  // namespace pipela::core::registry
