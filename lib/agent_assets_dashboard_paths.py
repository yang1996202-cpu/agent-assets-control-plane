"""Agent Assets Dashboard — 路径常量与外部命令发现。

背景：dashboard 需要知道各类资产文件、registry、缓存和外部命令的位置；
这些位置受环境变量覆盖，并支持开发时 repo 内 fallback 与安装后 stable bin fallback。
设计意图：把路径常量和命令发现逻辑集中到一处，避免 dashboard 各模块重复解析。
关键约束：
- 所有 Path 都在导入时根据环境变量计算一次，后续只读。
- 外部命令（discover / projects / runtime）优先使用环境变量或 stable bin；
  不存在时回退到 repo 本地脚本或 legacy 名称。
"""

import os
import pathlib


HOME = pathlib.Path(os.environ.get("AGENT_ASSETS_USER_HOME", str(pathlib.Path.home()))).expanduser()
CONFIG_HOME = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config"))).expanduser()
ASSETS_HOME = pathlib.Path(os.environ.get("AGENT_ASSETS_HOME", str(CONFIG_HOME / "agent-assets"))).expanduser()
MCP_HOME = pathlib.Path(os.environ.get("AGENT_ASSETS_MCP_HOME", str(CONFIG_HOME / "mcp"))).expanduser()
STABLE_BIN_DIR = pathlib.Path(os.environ.get("AGENT_ASSETS_BIN_DIR", str(HOME / ".local/bin"))).expanduser()
PROJECTS_DIR = pathlib.Path(os.environ.get("AGENT_ASSETS_PROJECTS_DIR", str(HOME / "projects"))).expanduser()
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent / "bin"

REGISTRY = pathlib.Path(os.environ.get("AGENT_ASSETS_REGISTRY", str(ASSETS_HOME / "registry.json"))).expanduser()
MCP_REGISTRY = pathlib.Path(os.environ.get("AGENT_ASSETS_MCP_REGISTRY", str(MCP_HOME / "registry.json"))).expanduser()
DISCOVERED = pathlib.Path(os.environ.get("AGENT_ASSETS_DISCOVERED", str(ASSETS_HOME / "discovered.json"))).expanduser()
MACOS_SIGNALS = pathlib.Path(os.environ.get("AGENT_ASSETS_MACOS_SIGNALS", str(ASSETS_HOME / "macos-signals.json"))).expanduser()
REVIEW = pathlib.Path(os.environ.get("AGENT_ASSETS_DISCOVERY_REVIEW", str(ASSETS_HOME / "discovery-review.json"))).expanduser()
PROJECT_INDEX = pathlib.Path(
    os.environ.get(
        "AGENT_ASSETS_PROJECT_INDEX",
        os.environ.get("AGENT_ASSETS_PROJECTS", str(ASSETS_HOME / "projects.json")),
    )
).expanduser()
MCP_HEALTH_CACHE = pathlib.Path(os.environ.get("AGENT_ASSETS_MCP_HEALTH_CACHE", str(ASSETS_HOME / "mcp-health-cache.json"))).expanduser()
OUT = pathlib.Path(os.environ.get("AGENT_ASSETS_DASHBOARD_HTML", str(ASSETS_HOME / "dashboard.html"))).expanduser()
START_FILE = pathlib.Path(os.environ.get("AGENT_ASSETS_START_FILE", str(HOME / "AGENT_START_HERE.md"))).expanduser()
ACTION_LOG = pathlib.Path(os.environ.get("AGENT_ASSETS_ACTION_LOG", str(ASSETS_HOME / "action-log.json"))).expanduser()
PRODUCT_MAP = pathlib.Path(os.environ.get("AGENT_ASSETS_PRODUCT_MAP", str(ASSETS_HOME / "product-map.json"))).expanduser()
RUNTIME_CLASSIFICATION = pathlib.Path(os.environ.get("AGENT_ASSETS_RUNTIME_CLASSIFICATION", str(ASSETS_HOME / "runtime-classification.json"))).expanduser()
CLAUDE = pathlib.Path(os.environ.get("AGENT_ASSETS_CLAUDE", str(STABLE_BIN_DIR / "claude"))).expanduser()

ASSET_DISCOVER = pathlib.Path(os.environ.get("AGENT_ASSETS_DISCOVER_CMD", str(STABLE_BIN_DIR / "agent-assets-discover"))).expanduser()
if not ASSET_DISCOVER.exists():
    repo_local_discover = SCRIPT_DIR / "agent-assets-discover"
    legacy_discover = STABLE_BIN_DIR / "asset-discover"
    if repo_local_discover.exists():
        ASSET_DISCOVER = repo_local_discover
    elif legacy_discover.exists():
        ASSET_DISCOVER = legacy_discover

ASSET_PROJECTS = pathlib.Path(os.environ.get("AGENT_ASSETS_PROJECTS_CMD", str(STABLE_BIN_DIR / "agent-assets-projects"))).expanduser()
if not ASSET_PROJECTS.exists():
    repo_local_projects = SCRIPT_DIR / "agent-assets-projects"
    legacy_projects = STABLE_BIN_DIR / "asset-projects"
    if repo_local_projects.exists():
        ASSET_PROJECTS = repo_local_projects
    elif legacy_projects.exists():
        ASSET_PROJECTS = legacy_projects

ASSET_RUNTIME = pathlib.Path(os.environ.get("AGENT_ASSETS_RUNTIME_CMD", str(STABLE_BIN_DIR / "asset-runtime"))).expanduser()
if not ASSET_RUNTIME.exists():
    repo_local_runtime = SCRIPT_DIR / "agent-assets-runtime"
    if repo_local_runtime.exists():
        ASSET_RUNTIME = repo_local_runtime

ASSET_MACOS_SIGNALS = pathlib.Path(os.environ.get("AGENT_ASSETS_MACOS_SIGNALS_CMD", str(STABLE_BIN_DIR / "agent-assets-macos-signals"))).expanduser()
if not ASSET_MACOS_SIGNALS.exists():
    repo_local_signals = SCRIPT_DIR / "agent-assets-macos-signals"
    if repo_local_signals.exists():
        ASSET_MACOS_SIGNALS = repo_local_signals
