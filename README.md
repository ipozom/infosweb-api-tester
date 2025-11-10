# Activate & Deactivate Accounts by Profile Date

Automatically activate or deactivate Okta user accounts when the profile contains an activation or deactivation date that matches the current day. The workflow runs on two schedules: one that looks for staged users to activate and another that finds active users to deactivate.

## Prerequisites

- **Okta Workflows** tenant with an available connection to the Okta connector.
- Okta user profile attributes named `account_activation_date` and `account_deactivation_date` that store dates in `MM/DD/YYYY` format.
- Administrative privileges to import, edit, and schedule flows.

## Files

- `workflow.flopack` – Original Okta-centric scheduled flows for activating/deactivating users by profile date.
- `workflow_infosweb.flopack` – New helper-only pack that calls Infosweb OAuth/token, activate, and deactivate endpoints through the HTTP connector.
- `workflow.json` – Metadata describing the flows, connectors, and hash of the original flopack.
- `README.md` – This guide.
- `json/Banesco-Modernizacion.postman_collection.json` – Reference Postman collection illustrating the Infosweb token and activate/deactivate endpoints.
- `docs/infosweb-flopack-process.md` – Step-by-step build and troubleshooting notes for the Infosweb helper flopacks.
- `src/infosweb_client.py` – Python helper that wraps the Infosweb API for local testing or automation.
- `requirements.txt` – Python dependencies for the helper CLI.

## Flow summary

### Okta profile-date workflow (`workflow.flopack`)

| Flow | Type | Purpose |
| --- | --- | --- |
| `1A Find users to activate by profile date` | Scheduled | Searches for staged users whose `account_activation_date` equals today, then invokes the helper to activate them. |
| `1B Activate account helper` | Helper | Activates a user in Okta using the supplied ID or login and returns the response status. |
| `2A Find users to deactivate by profile date` | Scheduled | Searches for active users whose `account_deactivation_date` equals today, then invokes the helper to deactivate them. |
| `2B Deactivate account helper` | Helper | Deactivates a user in Okta using the supplied ID or login and returns the response status. |

### Infosweb HTTP helpers (`workflow_infosweb.flopack`)

| Flow | Type | Purpose |
| --- | --- | --- |
| `Infosweb request token` | Helper | Calls `POST /Banesco/integracion/oauth/token` (grant type `client_credentials`) and returns the token payload. |
| `Infosweb activate user` | Helper | Calls `POST /Banesco/integracion/api/v1/usuarios/activar` with `nombre_usuario` in the JSON body and returns the HTTP response. |
| `Infosweb deactivate user` | Helper | Calls `POST /Banesco/integracion/api/v1/usuarios/desactivar` with `nombre_usuario` in the JSON body and returns the HTTP response. |

## Import and configuration

### Okta pack (`workflow.flopack`)

1. Download `workflow.flopack` and import it into Okta Workflows.
2. Reassign the Okta connection on each flow (activate and deactivate helper flows plus both scheduled flows) to a valid connection in your tenant.
3. Confirm the scheduled flows (`1A` and `2A`) have appropriate run times and time zone. They are preconfigured for 9:00 AM and 11:59 PM Pacific; adjust the cron schedules or the `Convert` card time zone if needed.
4. Ensure every user you expect to process has the `account_activation_date` and/or `account_deactivation_date` profile attributes populated in `MM/DD/YYYY` format.
5. (Optional) Update the `Send Email?` input on the Okta Activate/Deactivate cards if you want Okta to send user notifications.

### Infosweb helpers (`workflow_infosweb.flopack`)

1. Import `workflow_infosweb.flopack` into Okta Workflows. The flows will appear inside the *Infosweb API helpers* folder.
2. Create or select an **HTTP** connection, then configure it with the Infosweb base URL (for example `https://<hostname>`). All three flows share the connection named **Infosweb HTTP**.
3. Edit the **Custom API Action** cards in each flow to supply the correct headers:
	- For the token flow, set `Authorization` to `Basic <base64(client_id:client_secret)>` and keep `Content-Type: application/json`.
	- For activate/deactivate, set `Authorization` to `Bearer {{Access Token}}`. If you call the token helper first, bring the token into the downstream flow via the returned body.
4. Update the request body template if your environment needs additional attributes besides `nombre_usuario`.
5. Test each helper by running it with sample inputs. The flows return the HTTP status code and parsed JSON body to the caller.

## Procedure followed

### Okta pack refresh

The current `workflow.flopack` was produced and validated with the following steps to confirm Okta Workflows implementation feasibility:

1. Exported the original sample pack (`workflow_base.flopack`) from Okta Workflows for reference.
2. Removed the Microsoft Teams helper flow, renamed the remaining flows, and updated descriptions to reflect the activation/deactivation use case.
3. Simplified the helper inputs so they only require the user `ID`, dropping unused `Login` pins and related For Each mappings.
4. Saved the trimmed pack as `workflow.flopack` and recomputed its checksum.
5. Imported the updated pack into the target Okta Workflows tenant, reassigned connector credentials, and executed a smoke run to verify activation/deactivation cards behave as expected.

Result: the import completed successfully on 10 Nov 2025, demonstrating that flopack generation plus subsequent import into Okta Workflows is feasible for this scenario.

### Infosweb helper pack generation

To create the Infosweb-only helper pack without altering the Okta flows, the following scripted process was executed on 10 Nov 2025:

1. Parsed the Postman collection to confirm request structure (paths, headers, form body).
2. Authored a Python generator that serializes three helper flows (`Infosweb request token`, `Infosweb activate user`, `Infosweb deactivate user`) with unique UUIDs and a shared HTTP connection placeholder.
3. Ran the generator inside the project virtual environment, producing `workflow_infosweb.flopack` alongside the original packs.
4. Inspected the generated flopack to verify each flow contains a callable entry, descriptive comment, HTTP custom request card, and return block exposing `Status Code` and `Body` outputs.

Result: the new pack can be imported independently, letting downstream flows swap from Okta-specific actions to Infosweb HTTP calls while keeping the original automation intact for reference.

### Validation checklist

- Run `sha512sum workflow.flopack` and confirm the output matches `2b8b6aea062fd164322b53189a12c89a1cfc9f031c9a5a80f172f36b783b2df143dd9b721e3ef35962c610715c7e727ca610519addd3cd82cf2c6df589eef3c4`.
- Import `workflow_infosweb.flopack` and wire the **HTTP** connection before attempting to run the helpers.
- After import, reassign the Okta connector (for the original pack) and execute each helper flow once to confirm activation/deactivation succeed without errors.
- Review Flow History to ensure scheduled runs complete without missing inputs.

For Infosweb-only implementations, run the three helper flows in sequence (token → activate/deactivate) to verify the HTTP responses mirror the Postman collection outputs.

## Infosweb API helper

The project now includes a Python CLI (`src/infosweb_client.py`) that mirrors the three calls from the Postman collection:

1. Request an OAuth token using the client-credentials flow.
2. Deactivate a user by `nombre_usuario`.
3. Reactivate the same user.

### Configuration

Set the following environment variables (or pass them as CLI flags) before executing the helper:

- `INFOSWEB_BASE_URL` – Base host for the API. Defaults to `http://129.80.151.82:8081` using the Postman sample.
- `INFOSWEB_CLIENT_ID` – OAuth client identifier (Basic auth username from Postman).
- `INFOSWEB_CLIENT_SECRET` – OAuth client secret (Basic auth password from Postman).

Install dependencies and invoke the helper:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Retrieve a token (prints JSON with access_token and metadata)
python -m src.infosweb_client token

# Just the raw token value
python -m src.infosweb_client token --raw

# Deactivate or activate a user
python -m src.infosweb_client deactivate CCISNEROS@INFOSGROUP.COM
python -m src.infosweb_client activate CCISNEROS@INFOSGROUP.COM
```

Each `activate`/`deactivate` command will fetch a token automatically unless `--access-token` is supplied.

### Sample test run (10 Nov 2025)

The following session was executed from the repository root to validate the CLI against the Infosweb API:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Obtain a raw token
python -m src.infosweb_client token --raw
# -> nmiro-VfjgSE6kvOqQApfA

# Deactivate the user
python -m src.infosweb_client deactivate oipozo@Panama.Banesco.Lac
# {
#   "estado": "PROCESADO",
#   "detalle": [
#     {
#       "modulo": "AUTOSERVICIO",
#       "estado": "DESACTIVADO"
#     }
#   ]
# }

# Reactivate the user
python -m src.infosweb_client activate oipozo@Panama.Banesco.Lac
# {
#   "estado": "PROCESADO",
#   "detalle": [
#     {
#       "modulo": "AUTOSERVICIO",
#       "estado": "ACTIVADO"
#     }
#   ]
# }
```

This confirms the helper successfully toggles the Infosweb user status using the same endpoints that Okta Workflows will call.

### Using with Okta Workflows

- The CLI is intended as a thin layer for local validation or to be hosted behind a lightweight HTTPS service. Once hosted, an Okta Workflows flow can invoke it through the **HTTP** connector.
- Alternatively, reproduce the same HTTP requests directly inside Okta Workflows using the **Custom API Action** card: first call the token endpoint (Basic auth + form body), parse the returned `access_token`, then call either the activate or deactivate endpoint with a JSON body containing `nombre_usuario` and a Bearer header.
- The provided Postman collection (`json/Banesco-Modernizacion.postman_collection.json`) maps one-to-one with the steps needed in Okta Workflows and can be used as a reference for card configuration.

## Testing tips

- Start with a single test user and manually run the helper flows (`1B` or `2B`) to confirm the connector permissions.
- Temporarily convert the scheduled flows to **Test** mode (`Call Flow`) to verify the search results without running on a schedule.
- Review the Flow History after each run to confirm the number of users found and any connector errors.

## Customization ideas

- Use the `Result Set` input on the search cards to switch between the first 200 users or streaming mode for higher volume environments.
- Add additional filters on the user search (for example, limiting to a specific group or organization unit).
- Extend the helper flows with logging or notifications to other systems.
