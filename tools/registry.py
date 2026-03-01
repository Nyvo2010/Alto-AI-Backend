import importlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).resolve().parent


class ToolManifest:
    def __init__(self, data: dict, folder: Path) -> None:
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.version: str = data.get("version", "1.0.0")
        self.active_when: list[str] = data.get("active_when", [])
        self.trigger: dict | None = data.get("trigger")
        self.agent_schema: dict | None = data.get("agent_schema")
        self.settings_schema: list[dict] = data.get("settings_schema", [])
        self.folder = folder

    @property
    def has_trigger(self) -> bool:
        return (self.folder / "trigger.py").exists()

    @property
    def has_tool(self) -> bool:
        return (self.folder / "tool.py").exists()


class ToolRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, ToolManifest] = {}
        self._executors: dict[str, Callable] = {}
        self._trigger_starters: dict[str, Callable] = {}

    def scan(self) -> None:
        self._manifests.clear()
        self._executors.clear()
        self._trigger_starters.clear()

        for folder in sorted(TOOLS_DIR.iterdir()):
            manifest_file = folder / "manifest.json"
            if not folder.is_dir() or not manifest_file.exists():
                continue
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest = ToolManifest(data, folder)
                self._manifests[manifest.id] = manifest
                self._load_executor(manifest)
                self._load_trigger(manifest)
                logger.info("Loaded tool: %s (v%s)", manifest.id, manifest.version)
            except Exception:
                logger.exception("Failed to load tool from %s", folder.name)

    def _load_executor(self, manifest: ToolManifest) -> None:
        if not manifest.has_tool:
            return
        module_path = f"tools.{manifest.folder.name}.tool"
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, "execute"):
                self._executors[manifest.id] = mod.execute
        except Exception:
            logger.exception("Failed to import executor for %s", manifest.id)

    def _load_trigger(self, manifest: ToolManifest) -> None:
        if not manifest.has_trigger:
            return
        module_path = f"tools.{manifest.folder.name}.trigger"
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, "start"):
                self._trigger_starters[manifest.id] = mod.start
        except Exception:
            logger.exception("Failed to import trigger for %s", manifest.id)

    def is_active(self, tool_id: str) -> bool:
        manifest = self._manifests.get(tool_id)
        if not manifest:
            return False

        from config.store import get as get_setting

        default_enabled = os.getenv("DEFAULT_TOOL_ENABLED", "true").lower() == "true"
        enabled = get_setting(f"{tool_id}__enabled", default_enabled)
        if not enabled:
            return False

        for key in manifest.active_when:
            schema_entry = next(
                (s for s in manifest.settings_schema if s["key"] == key), None
            )
            if schema_entry and schema_entry.get("source") == "env":
                env_var = schema_entry.get("env_var", "")
                if not os.getenv(env_var):
                    return False
            else:
                if not get_setting(key):
                    return False
        return True

    def get_active_tools(self) -> list[ToolManifest]:
        return [m for m in self._manifests.values() if self.is_active(m.id)]

    def get_all(self) -> list[ToolManifest]:
        return list(self._manifests.values())

    def get(self, tool_id: str) -> ToolManifest | None:
        return self._manifests.get(tool_id)

    def get_executor(self, tool_id: str) -> Callable | None:
        return self._executors.get(tool_id)

    def get_trigger_starters(self) -> dict[str, Callable]:
        return {
            tid: starter
            for tid, starter in self._trigger_starters.items()
            if self.is_active(tid)
        }

    def get_tool_descriptions(self) -> list[dict]:
        descriptions = []
        for m in self.get_active_tools():
            if m.agent_schema:
                descriptions.append({
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "functions": m.agent_schema.get("functions", []),
                })
        return descriptions

    def get_mistral_tools(self, tool_ids: list[str]) -> list[dict]:
        tools = []
        for tid in tool_ids:
            manifest = self._manifests.get(tid)
            if not manifest or not manifest.agent_schema:
                continue
            for func in manifest.agent_schema.get("functions", []):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    },
                })
        return tools

    def find_tool_by_function(self, function_name: str) -> str | None:
        for manifest in self._manifests.values():
            if not manifest.agent_schema:
                continue
            for func in manifest.agent_schema.get("functions", []):
                if func["name"] == function_name:
                    return manifest.id
        return None


registry = ToolRegistry()
