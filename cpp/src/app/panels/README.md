# Settings panels (C++ Qt)

19 panels in `settings_panel_defs.cpp`. `panel_factory.cpp` routes:

- **Worker template** — `worker_template_panel` + `widgets/template_probe_section` (ride, hp_refill, reload, ammo_restock, call_merc): threshold + path thumb
- **Dedicated** — `interface`, `console`, `left_click`
- **Registry prefix** — editable bool/int/double for remaining prefixed keys
- **Placeholder** — KC tier table, calendar, template thumb preview, …

Regenerate parity map: `python tools/codegen/export_parity_matrix.py`
