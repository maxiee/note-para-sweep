"""配置管理模块"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请复制 config.yaml.template 为 config.yaml 并填入配置"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _validate_config(self):
        """验证配置"""
        required_keys = ["llm", "obsidian"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置文件缺少必需的键: {key}")

        # 验证 LLM 配置
        llm_config = self.config["llm"]
        provider = llm_config.get("provider", "openai")

        if provider not in ["openai", "openrouter"]:
            raise ValueError(f"不支持的LLM提供商: {provider}")

        provider_config = llm_config.get(provider)
        if not provider_config:
            raise ValueError(f"缺少 {provider} 的配置")

        # 验证 API Key
        api_key = provider_config.get("api_key")
        if not api_key or api_key == f"your-{provider}-api-key-here":
            if not self.config.get("safety", {}).get("dry_run_by_default", True):
                raise ValueError(f"请在配置文件中设置有效的 {provider} API Key")
            # 在试运行模式下只发出警告
            print(f"⚠️  警告: 未设置 {provider} API Key，仅可使用试运行模式")

        # 验证 Obsidian 库路径
        vault_path = Path(self.config["obsidian"]["vault_path"])
        if not vault_path.exists():
            if vault_path.as_posix() == "/path/to/your/obsidian/vault":
                print("⚠️  警告: 请在配置文件中设置正确的 Obsidian 库路径")
            else:
                raise ValueError(f"Obsidian 库路径不存在: {vault_path}")

    @property
    def llm_provider(self) -> str:
        return self.config["llm"].get("provider", "openai")

    @property
    def llm_api_key(self) -> str:
        provider = self.llm_provider
        return self.config["llm"][provider]["api_key"]

    @property
    def llm_model(self) -> str:
        provider = self.llm_provider
        return self.config["llm"][provider].get("model", "gpt-4")

    @property
    def llm_base_url(self) -> str:
        provider = self.llm_provider
        return self.config["llm"][provider].get("base_url", "")

    @property
    def openai_api_key(self) -> str:
        return self.config["openai"]["api_key"]

    @property
    def openai_model(self) -> str:
        return self.config["openai"].get("model", "gpt-4")

    @property
    def vault_path(self) -> Path:
        return Path(self.config["obsidian"]["vault_path"])

    @property
    def para_paths(self) -> Dict[str, str]:
        return self.config["obsidian"]["para"]

    @property
    def log_file(self) -> str:
        return self.config.get("logging", {}).get("log_file", "para_sweep.log")

    @property
    def dry_run_by_default(self) -> bool:
        return self.config.get("safety", {}).get("dry_run_by_default", True)

    @property
    def require_confirmation(self) -> bool:
        return self.config.get("safety", {}).get("require_confirmation", True)
