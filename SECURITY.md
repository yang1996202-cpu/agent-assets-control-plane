# Security

This project is a local inventory and dashboard for agent-facing assets.

Do not commit real local registries if they contain private paths, internal project names, or secret locations you do not want public.

Registries must never contain:

- API keys
- bearer tokens
- Authorization headers
- cookies
- passwords
- private keys

The dashboard binds to `127.0.0.1` by default. Do not expose it publicly.

If you find a vulnerability, open a private security advisory if the host supports it, or contact the maintainer without posting exploit details publicly.

