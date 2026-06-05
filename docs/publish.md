# Publish

This repo is ready to publish when these checks pass:

```bash
python3 -m py_compile bin/agent-assets-*
python3 -m json.tool templates/agent-assets/registry.example.json >/dev/null
python3 -m json.tool templates/agent-assets/discovery-review.example.json >/dev/null
python3 -m json.tool templates/mcp/registry.example.json >/dev/null
rg '/Users/|Authorization|Bearer|api_key|token=' .
```

The last command should not reveal private paths or secret material.

## Create A GitHub Repo Without `gh`

1. Create a new public GitHub repository named `agent-assets-control-plane`.
2. Do not initialize it with README/license because this repo already has them.
3. Run:

```bash
git remote add origin git@github.com:<user-or-org>/agent-assets-control-plane.git
git branch -M main
git push -u origin main
```

## Create With GitHub CLI

If `gh` is installed and authenticated:

```bash
gh repo create agent-assets-control-plane --public --source=. --remote=origin --push
```

## What Not To Publish

Do not copy a real local registry into this repo:

- `~/.config/agent-assets/registry.json`
- `~/.config/agent-assets/discovered.json`
- `~/.config/agent-assets/mcp-health-cache.json`
- `~/.config/mcp/registry.json`

Commit templates and examples instead.

