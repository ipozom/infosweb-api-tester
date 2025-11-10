# Infosweb Flopack Build & Troubleshooting Guide

This guide documents how the `workflow_infosweb.flopack` and the diagnostic `workflow_infosweb_activate_only.flopack` were produced, validated, and corrected so they import cleanly into Okta Workflows. Follow the same steps to regenerate or extend the helpers.

## 📦 Deliverables

| File | Purpose |
| --- | --- |
| `workflow_infosweb.flopack` | Bundles the token, activate, and deactivate helper flows that call the Infosweb API through the HTTP connector. |
| `workflow_infosweb_activate_only.flopack` | Minimal pack that contains just the activate helper, used to debug import issues. |
| `json/Banesco-Modernizacion.postman_collection.json` | Postman collection that defines the baseline request/response shapes for all Infosweb endpoints. |
| `makeApiRequestsWithTheHttpRequestCard.folder` | Okta reference pack used to verify tree, ordering, and mapping metadata for HTTP Raw Request flows. |

## 🧱 Flow Anatomy

Each helper flow follows the same structure:

1. **Callable** (`control:callable`) exposes the helper entry point.
2. **Comment** documents the operation (optional but keeps parity with Okta templates).
3. **HTTP Raw Request** (`httpfunctions:raw`, partner channel key `65`) performs the API call. Inputs map to URL, method, headers, query, and body.
4. **Return** (`control:return`) surfaces the HTTP status code and body to the caller.

All flows live inside the shared folder `Infosweb API helpers` (UUID `1d661389-c35a-457f-96c0-a065b8f030fa`) so they import together.

## 🛠️ Build Process

1. **Collect request specs**  
   Use the Postman collection to confirm the Infosweb endpoints, required headers, and payload shapes for token, activate, and deactivate operations.

2. **Inspect a known-good template**  
   Export `makeApiRequestsWithTheHttpRequestCard.folder` from Okta Workflows. This pack clarifies how callable helpers that drive HTTP Raw Request cards should describe:
   - `tree` metadata (`id: 3`, `name: "empty"`),
   - method ordering arrays (`orderings`),
   - pin definitions and connector metadata.

3. **Author the flows**  
   Create three flow definitions that mirror the template structure. Ensure every method block has a unique `uuid` and that pins route outputs from the HTTP card to the Return card. Populate descriptive comments and configure the HTTP card inputs with moustache placeholders such as `{{Base URL}}` and `{{Access Token}}`.

4. **Assemble the flopack envelope**  
   Wrap the flow definitions inside the flopack payload:
   - Set `type` to `flopack` and `version` to `1.5.0`.
   - Include the shared folder entry under `data.groups`.
   - Leave `configs` and `tables` empty (the helpers do not provision tables or connections).

5. **Generate a diagnostic pack (optional)**  
   Copy the activate helper into `workflow_infosweb_activate_only.flopack` to isolate issues during import. This keeps the same folder metadata but only ships one flow.

6. **Validate JSON structure**  
   Run `python -m json.tool` over both flopacks before importing them to catch syntax errors.

   ```bash
   python -m json.tool workflow_infosweb.flopack > /dev/null
   python -m json.tool workflow_infosweb_activate_only.flopack > /dev/null
   ```

## 🐞 Debugging Timeline (Nov 2025)

| Step | Action | Result |
| --- | --- | --- |
| 1 | Imported `workflow_infosweb.flopack` into Okta Workflows. | Token and deactivate helpers succeeded; activate helper raised `TypeError: flo.id is not a function`. |
| 2 | Generated `workflow_infosweb_activate_only.flopack` to reproduce the error with a single flow. | Error persisted, proving the issue lived inside the activate flow metadata. |
| 3 | Compared the activate flow’s metadata against `makeApiRequestsWithTheHttpRequestCard.folder`. | Noticed that the `orderings` arrays still referenced UUIDs from a copied deactivate flow. |
| 4 | Updated the `orderings` arrays so they list the actual method UUIDs (`callable → comment → HTTP raw → return`). | Re-import succeeded; the `flo.id` error disappeared. |
| 5 | Revalidated both flopacks with `python -m json.tool` and archived the fixed files. | Packs are ready for distribution. |

### Why the importer failed

Okta relies on the `orderings` arrays to know the execution sequence between method UUIDs. Because the activate flow still referenced the deactivate flow’s UUIDs, the importer attempted to resolve non-existent nodes, producing the `flo.id is not a function` error. Aligning the sequence with the real UUIDs fixed the problem without needing `floMapping` entries.

## 🔁 Rebuilding or Extending the Helpers

1. **Add new flows** by copying an existing helper block and giving every method/card a new UUID. Update the orderings to match the new UUIDs.
2. **Adjust inputs/outputs** by editing the `callable` metadata (`inputs.data`) and the `return` card pins.
3. **Change endpoints** by modifying the HTTP card `URL`, `Method`, `Headers`, and `Body` fields. Keep placeholders (`{{ }}`) for values supplied at runtime.
4. **Re-run JSON validation** and re-import the flopack to confirm the new flow shows up inside the `Infosweb API helpers` folder.

## ✅ Final Checklist Before Shipping

- [x] `orderings` in every flow reference only UUIDs present in that flow’s `methods` list.
- [x] `tree.id` is set to `3` (async addressing) for each flow.
- [x] HTTP Raw Request cards use partner channel key `65`.
- [x] Folder metadata (`data.groups`) includes the flow folder UUID and friendly name.
- [x] `python -m json.tool` passes for every flopack file.
- [x] Import succeeds in the target Okta Workflows tenant and each helper runs end-to-end.

Documenting the process ensures the Infosweb helpers remain maintainable and highlights the critical metadata (particularly `orderings`) that must stay in sync whenever new cards are introduced.
