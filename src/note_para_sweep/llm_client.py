"""LLM 客户端模块"""

import openai
from typing import Dict, Any, Optional
from .config import Config


class LLMClient:
    """LLM 客户端，支持多个提供商"""

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.llm_provider
        self.api_key = config.llm_api_key
        self.model = config.llm_model
        self.base_url = config.llm_base_url

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化 LLM 客户端"""
        if self.provider == "openai":
            self.client = openai.OpenAI(
                api_key=self.api_key, base_url=self.base_url if self.base_url else None
            )
        elif self.provider == "openrouters":
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")

    def chat_completion(self, messages: list, **kwargs) -> str:
        """发送聊天完成请求

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            AI 的回复内容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API 调用失败 ({self.provider}): {str(e)}")

    def classify_note(self, note_content: str, para_structure: str) -> Dict[str, Any]:
        """分类笔记到 PARA 系统

        Args:
            note_content: 笔记内容
            para_structure: PARA 目录结构描述

        Returns:
            分类结果字典
        """
        prompt = f"""
请分析以下笔记内容，并根据 PARA 方法将其分类到合适的类别中。

PARA 方法说明：
- Projects: 具体、有 deadline 的项目
- Areas: 持续管理的责任领域
- Resources: 参考资料和工具
- Archives: 已完成的项目和非活跃内容

当前 PARA 结构：
{para_structure}

笔记内容：
{note_content}

请返回 JSON 格式的结果：
{{
    "category": "projects|areas|resources|archives",
    "subcategory": "具体的子分类名称",
    "confidence": 0.0-1.0,
    "reasoning": "分类理由"
}}
"""

        messages = [
            {"role": "system", "content": "你是一个 PARA 方法专家，帮助用户组织笔记。"},
            {"role": "user", "content": prompt},
        ]

        response = self.chat_completion(messages, temperature=0.3)

        # 这里应该解析 JSON 响应，但为了简化暂时返回文本
        return {"response": response, "provider": self.provider, "model": self.model}
