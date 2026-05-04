#!/usr/bin/env python3
"""
配置管理模块
集中管理所有配置项，便于维护和扩展
"""

import os
import yaml
from pathlib import Path
from typing import List, Any

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """配置类，管理所有配置项"""

    def _clean_string(self, value: str) -> str:
        """清理字符串中的特殊字符"""
        if not value:
            return value
        # 移除不间断空格和其他不可见字符
        return value.replace('\xa0', ' ').strip()

    def _safe_int(self, value: Any, default: str) -> int:
        """安全的整数转换"""
        if value is None:
            return int(default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return int(default)

    def __init__(self):
        """初始化配置，从文件和环境变量读取"""
        
        # 1. 设置路径
        self.BASE_DIR = Path(__file__).parent.parent
        self.CONFIG_FILE = self.BASE_DIR / "config.yml"
        
        # 2. 从YAML文件加载默认配置
        self._config = self._load_from_yaml()

        # 3. 从环境变量加载并覆盖配置
        self._load_from_env()

        # 4. 设置派生配置和路径
        self._set_derived_paths()

    def _load_from_yaml(self) -> dict:
        """从YAML文件加载配置"""
        if not self.CONFIG_FILE.exists():
            print("⚠️ 未找到 config.yml 文件，将仅使用环境变量和默认值。")
            return {}
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_from_env(self):
        """从环境变量加载配置，覆盖YAML中的值"""
        # 遍历 self._config 的键，以便我们知道要从环境中查找哪些变量
        config_keys = list(self._config.keys())

        # 也包括那些可能不在YAML中但可以通过env设置的敏感键
        sensitive_keys = [
            "QWEN_API_KEY", "QWEN_MODEL",
            "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL",
            "GLM_API_KEY", "GLM_MODEL",
            "SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD",
            "EMAIL_FROM", "EMAIL_TO", "GITHUB_REPO_URL"
        ]

        for key in config_keys + sensitive_keys:
            env_value = os.getenv(key)
            if env_value is not None:
                self._config[key] = env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持默认值"""
        return self._config.get(key, default)

    def _set_derived_paths(self):
        """设置所有派生路径"""
        self.PAPERS_DIR = self.BASE_DIR / "storage" / "papers"
        self.CONCLUSION_FILE = self.BASE_DIR / "storage" / "conclusion.md"
        self.HTML_REPORT_FILE = self.BASE_DIR / "storage" / "report.html"
        self.TEMPLATES_DIR = self.BASE_DIR / "src" / "output" / "templates"
        self.DB_PATH = self.BASE_DIR / "storage" / "papers.db"
        self.LOGS_DIR = self.BASE_DIR / "storage" / "logs"

    def __getattr__(self, name: str) -> Any:
        """使配置项可以作为属性访问"""
        # 将属性名转为大写以匹配环境变量和YAML键
        key = name.upper()
        
        # 特殊处理布尔值
        if key == "ENABLE_PARALLEL":
            value = self.get(key, "true")
            return str(value).lower() == "true"
            
        # 特殊处理列表
        if key == "CATEGORIES":
            value = self.get(key, "cs.RO,cs.MA,eess.SY")
            return [cat.strip() for cat in value.split(",") if cat.strip()]
        
        if key == "EMAIL_TO":
            value = self.get(key, "")
            return [email.strip() for email in value.split(",") if email.strip()]

        # 处理需要是整数的数字
        numeric_keys = [
            "MAX_PAPERS", "SEARCH_DAYS", "API_RETRY_TIMES", "API_DELAY",
            "API_TIMEOUT", "SMTP_PORT", "MAX_WORKERS", "BATCH_SIZE",
            "ARXIV_CLIENT_NUM_RETRIES"
        ]
        if key in numeric_keys:
            default_map = {
                "MAX_PAPERS": "50", "SEARCH_DAYS": "2", "API_RETRY_TIMES": "3",
                "API_DELAY": "2", "API_TIMEOUT": "60", "SMTP_PORT": "587",
                "MAX_WORKERS": "0", "BATCH_SIZE": "20", "ARXIV_CLIENT_NUM_RETRIES": "3"
            }
            value = self.get(key, default_map.get(key))
            return self._safe_int(value, default_map.get(key))

        # 处理需要是浮点数的数字
        if key == "ARXIV_CLIENT_DELAY_SECONDS":
             return float(self.get(key, "5.0"))
             
        # 对于其他所有字符串值
        return self.get(name.upper())

    def validate(self) -> bool:
        """验证配置是否完整"""
        # 检查AI API密钥（至少需要一个）
        if not self.GLM_API_KEY and not self.DEEPSEEK_API_KEY and not self.QWEN_API_KEY:
            print("❌ 未配置AI API密钥，请配置 QWEN_API_KEY、GLM_API_KEY 或 DEEPSEEK_API_KEY")
            return False

        required_email_configs = [
            self.SMTP_SERVER, self.SMTP_USERNAME, self.SMTP_PASSWORD, self.EMAIL_FROM
        ]
        if any(not config for config in required_email_configs):
            print(f"❌ 缺少一个或多个必需的邮件配置(SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM)")
            return False

        if not self.EMAIL_TO:
            print("❌ 缺少收件人邮箱配置 (EMAIL_TO)")
            return False

        # 显示使用的模型
        if self.QWEN_API_KEY:
            print(f"✅ 配置验证通过！使用Qwen模型: {self.QWEN_MODEL or 'qwen3-max'}")
        elif self.GLM_API_KEY:
            print(f"✅ 配置验证通过！使用智谱GLM模型: {self.GLM_MODEL or 'glm-4.6'}")
        else:
            print(f"✅ 配置验证通过！使用DeepSeek模型: {self.DEEPSEEK_MODEL}")
        return True

    def create_directories(self):
        """创建必要的目录"""
        self.PAPERS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        # 确保storage目录存在
        (self.BASE_DIR / "storage").mkdir(parents=True, exist_ok=True)
