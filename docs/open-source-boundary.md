# Open Source Boundary

Do open-source:

- generic scripts
- templates
- schemas and examples
- docs explaining the control-plane pattern

Do not open-source:

- a user's real `registry.json`
- real MCP host configs with secrets
- private project names if sensitive
- local token paths if revealing them is risky
- screenshots that reveal private tools or customer data

The important product idea is portable:

> A local machine needs a single visible control plane for agent-facing assets.

The user's private inventory is not portable and should stay local.

