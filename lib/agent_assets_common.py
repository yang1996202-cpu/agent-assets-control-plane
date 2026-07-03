"""Agent Assets Control Plane — 跨脚本公共工具函数。

背景：bin/ 下多个 CLI 脚本各自实现了 JSON IO、路径判断、HTML chip 渲染等
相同逻辑，导致改动一处需要在多个文件同步，且容易漏。
设计意图：把无状态、无副作用的纯工具函数集中到一个模块，供所有脚本 import。
所有 CLI 脚本通过统一的 sys.path 注入逻辑找到本模块（开发时从 repo lib/，
安装后从 ~/.local/lib/agent-assets/）。
关键约束：
- 本模块只依赖标准库，不引入第三方包。
- 路径常量基于环境变量（AGENT_ASSETS_USER_HOME、XDG_CONFIG_HOME 等）在导入时计算，
  各脚本不要再重复写这套解析。
- HTML 相关函数原本只在 dashboard 使用，但为避免重复也放在这里；非 dashboard
  脚本无需使用。
"""

import datetime as dt
import html
import os
import pathlib
import urllib.parse


# -----------------------------------------------------------------------------
# 路径常量（按 XDG / 项目约定解析，环境变量可覆盖）
# -----------------------------------------------------------------------------

HOME = pathlib.Path(
    os.environ.get("AGENT_ASSETS_USER_HOME", str(pathlib.Path.home()))
).expanduser()
CONFIG_HOME = pathlib.Path(
    os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config"))
).expanduser()
ASSETS_HOME = pathlib.Path(
    os.environ.get("AGENT_ASSETS_HOME", str(CONFIG_HOME / "agent-assets"))
).expanduser()
MCP_HOME = pathlib.Path(
    os.environ.get("AGENT_ASSETS_MCP_HOME", str(CONFIG_HOME / "mcp"))
).expanduser()
STABLE_BIN_DIR = pathlib.Path(
    os.environ.get("AGENT_ASSETS_BIN_DIR", str(HOME / ".local/bin"))
).expanduser()
PROJECTS_DIR = pathlib.Path(
    os.environ.get("AGENT_ASSETS_PROJECTS_DIR", str(HOME / "projects"))
).expanduser()


# -----------------------------------------------------------------------------
# JSON IO
# -----------------------------------------------------------------------------

def load_json(path):
    """读取 JSON 文件；文件不存在时返回空 dict 而不是抛异常。

    背景：CLI 脚本经常面对首次运行、registry 尚未生成的情况，返回 {} 可以让
    调用方直接用 .get/setdefault 继续。
    约束：如果文件存在但 JSON 格式损坏，仍会抛出 json.JSONDecodeError，
    因为这需要调用方显式处理或报告给用户。
    """
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return __import__("json").load(f)


def write_json(path, payload):
    """原子写入 JSON 文件：先写 .tmp 再 replace，避免中断导致半写。

    背景：registry.json / projects.json 等是用户资产的唯一来源，写坏后果严重。
    约束：会自动创建父目录；indent=2、ensure_ascii=False，保持可读性和中文。
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


# -----------------------------------------------------------------------------
# 集合 / 字符串工具
# -----------------------------------------------------------------------------

def listify(value):
    """把 None、字符串、列表统一为字符串列表，过滤 None。

    背景：registry 里同一字段有时是单值有时是列表，渲染/迭代前先归一化。
    """
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def append_unique(target, key, values):
    """向 target[key] 列表追加 value，保持唯一且过滤 falsy。

    背景：registry 拼装时（如 stable_entrypoints、hosts）需要增量追加，
    但不能产生重复项。
    约束：target[key] 会被 setdefault 为列表；values 可以是单个值或列表。
    """
    bucket = target.setdefault(key, [])
    for value in listify(values):
        if value and value not in bucket:
            bucket.append(value)


# -----------------------------------------------------------------------------
# 路径判断
# -----------------------------------------------------------------------------

def safe_resolve(path):
    """安全 resolve：遇到权限或不存在时回退到 expanduser + absolute。

    背景：macOS 上有些路径是 symlinks、权限受限或已删除，直接 resolve 可能抛异常。
    """
    try:
        return pathlib.Path(path).expanduser().resolve(strict=False)
    except Exception:
        return pathlib.Path(path).expanduser().absolute()


def is_under(path, parent):
    """判断 path 是否在 parent 目录下（都经过 safe_resolve 规范化）。"""
    try:
        safe_resolve(path).relative_to(safe_resolve(parent))
        return True
    except ValueError:
        return False


def url_to_path(value):
    """把 file:// URL 转回本地路径；非 file:// 返回空字符串。"""
    if not value or not str(value).startswith("file://"):
        return ""
    parsed = urllib.parse.urlsplit(str(value))
    return urllib.parse.unquote(parsed.path)


# -----------------------------------------------------------------------------
# 标识符规范化（主要供 macos-signals 使用）
# -----------------------------------------------------------------------------

def normalize_identifier(value):
    """去掉前导序号、首尾空格，把标识符统一成可比较的字符串。"""
    value = str(value or "").strip()
    value = __import__("re").sub(r"^\d+\.", "", value)
    return value.strip()


def item_key(*values):
    """从多个候选值里挑第一个可用的作为 item 主键。

    背景：BTM / launchd / privileged-helper 三处来源的字段命名不一致，
    需要按优先级（identifier > name > executable basename）合并成同一个 key。
    约束：过滤空值和占位符 "(null)" / "Unknown Developer"。
    """
    for value in values:
        value = normalize_identifier(value)
        if value and value not in {"(null)", "Unknown Developer"}:
            return value
    return "unknown"


# -----------------------------------------------------------------------------
# 时间
# -----------------------------------------------------------------------------

def now_iso():
    """返回 UTC ISO8601 时间戳，秒级，带 Z 后缀。"""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# -----------------------------------------------------------------------------
# HTML / 渲染辅助（dashboard 主要使用）
# -----------------------------------------------------------------------------

def h(value):
    """HTML escape，包含引号，用于把任意值安全地放进 HTML 属性或文本。"""
    return html.escape(str(value), quote=True)


def path_part(value):
    """从可能带冒号后缀的字符串里提取实际存在的本地路径部分。

    背景：dashboard 里有些字段值是 "path:location" 形式（如 MCP location），
    渲染时需要把 path 部分拿出来做 file:// 链接和存在性判断。
    约束：只处理绝对路径；路径不存在时也返回截取到的绝对路径字符串。
    """
    if not value or not str(value).startswith("/"):
        return None
    raw = str(value)
    candidate = pathlib.Path(raw)
    if candidate.exists() or candidate.is_symlink():
        return raw
    for idx, char in enumerate(raw):
        if char != ":":
            continue
        candidate = raw[:idx]
        if pathlib.Path(candidate).exists() or pathlib.Path(candidate).is_symlink():
            return candidate
    return raw


def href_for_path(value):
    """为存在的本地路径生成 file:// URL；无法生成时返回空字符串。"""
    path = path_part(value)
    if not path:
        return ""
    return "file://" + urllib.parse.quote(str(path))


def path_state(value):
    """判断一个路径字符串的当前状态，用于 chip 右侧小标签。

    返回状态语义：
    - exec / file / dir / file-ref：存在且可执行/文件/目录/带引用后缀
    - broken-link：symlink 但目标不存在
    - missing：路径不存在
    - ref：不是以 / 开头的纯引用
    """
    path_value = path_part(value)
    if not path_value:
        return "ref"
    path = pathlib.Path(path_value)
    if path.exists():
        if path_value != str(value):
            return "file-ref"
        if path.is_dir():
            return "dir"
        if os.access(path, os.X_OK):
            return "exec"
        return "file"
    if path.is_symlink():
        return "broken-link"
    return "missing"


def chip(value, css_class=""):
    """渲染一个带状态标签和 file:// 链接的 chip HTML 元素。

    背景：dashboard 里大量路径/URL 需要可视化其存在性和可点击跳转。
    约束：value 会被 HTML escape；只有本地路径才会生成链接。
    """
    value = str(value)
    state = path_state(value)
    href = href_for_path(value)
    label = h(value)
    state_label = h(state)
    classes = "chip " + h(css_class)
    if href:
        return f'<a class="{classes}" href="{h(href)}"><span>{label}</span><b>{state_label}</b></a>'
    return f'<span class="{classes}"><span>{label}</span><b>{state_label}</b></span>'


# -----------------------------------------------------------------------------
# Host 配置键（dashboard + macos-signals 共用）
# -----------------------------------------------------------------------------

def host_config_keys():
    """返回当前需要扫描的 host MCP config 键列表。

    背景：dashboard 做 MCP audit、macos-signals 判断 agent-service 时都需要知道
    本机有哪些 agent host。之前这些键在多处硬编码，新增 host 要改多份代码。
    设计意图：默认值覆盖当前已知的 4 个 host，同时允许通过环境变量追加或覆盖。
    约束：环境变量 AGENT_ASSETS_HOST_CONFIG_KEYS 使用逗号分隔；为空时使用默认值。
    """
    env = os.environ.get("AGENT_ASSETS_HOST_CONFIG_KEYS", "").strip()
    if env:
        return [k.strip() for k in env.split(",") if k.strip()]
    return [
        "claude_mcp_config",
        "cursor_mcp_config",
        "workbuddy_mcp_config",
        "project_xz_mcp_config",
    ]
