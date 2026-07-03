# Release Notes

> User-facing release notes. No debug details, no internal refactor descriptions, no file paths.
> Every bullet must answer: "What does this do for me?"

## 0.2.0 — Upcoming

### New

- **System process monitor**: view every running process with CPU and memory bars, sort by any column, and filter by category (apps, MCP servers, agents, dev servers, system daemons).
- **GUI apps included**: Chrome, WeChat, and other macOS apps now appear in the system process list.
- **One-click process termination**: terminate or force-kill a process directly from the dashboard.

### Improved

- **Cleaner dashboard UI**: the system process tab now uses the same filter + table layout as the rest of the dashboard.
- **Launchctl feedback**: stopping an already-stopped service no longer shows a scary failure message.

### Customization

- Personal vendor mappings and process classification rules are now kept in `~/.config/agent-assets/`, making the core project easier to fork and share.

---

## 0.1.0 — Initial

Initial release with local runtime observation tools and a localhost dashboard.
