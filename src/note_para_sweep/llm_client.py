"""LLM 客户端模块"""

import openai
import json
import re
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

        # 检查是否为mock模式（API Key为空或包含mock）
        self.mock_mode = not self.api_key or "mock" in self.api_key.lower()

        # 初始化客户端
        if not self.mock_mode:
            self._init_client()

    def _init_client(self):
        """初始化 LLM 客户端"""
        if self.provider == "openai":
            self.client = openai.OpenAI(
                api_key=self.api_key, base_url=self.base_url if self.base_url else None
            )
        elif self.provider == "openrouter":
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
        if self.mock_mode:
            return self._mock_response(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API 调用失败 ({self.provider}): {str(e)}")

    def _mock_response(self, messages: list) -> str:
        """模拟AI响应，用于演示"""
        # 根据消息内容生成合理的mock响应
        last_message = messages[-1]["content"] if messages else ""

        if "分析以下笔记内容" in last_message:
            # 笔记分类的mock响应
            return """
{
    "category": "resources",
    "subcategory": "编程资源",
    "target_path": "3. Resources/编程资源/收件箱整理笔记.md",
    "confidence": 0.85,
    "reasoning": "这是一个包含随机想法和灵感的笔记，适合作为参考资料保存在Resources分类中。内容提到了整理分类的需求，可以归入编程资源子分类。",
    "action_type": "move",
    "create_directories": []
}
"""
        elif "分析以下PARA知识库结构" in last_message:
            # 结构优化的mock响应
            return """
{
    "overall_assessment": "整体结构较为清晰，符合PARA方法论的基本原则。各个分类目录结构合理，但可以进一步优化。",
    "suggestions": [
        {
            "type": "create",
            "priority": "medium",
            "description": "在Areas中创建学习管理子目录",
            "current_path": "",
            "suggested_path": "2. Areas/学习管理",
            "reasoning": "技能学习目录为空，建议创建更具体的学习管理子目录来组织学习相关内容"
        },
        {
            "type": "move",
            "priority": "low",
            "description": "考虑将收件箱笔记移动到合适分类",
            "current_path": "0. Inbox/待分类笔记.md",
            "suggested_path": "3. Resources/通用资料",
            "reasoning": "收件箱中的笔记应该及时分类，避免堆积"
        }
    ],
    "structure_score": 0.78,
    "main_issues": ["收件箱有未分类笔记", "部分子目录为空需要进一步组织"]
}
"""
        else:
            return "Mock模式：模拟AI响应"

    def classify_note(self, note_content: str, para_structure: str) -> Dict[str, Any]:
        """分类笔记到 PARA 系统

        Args:
            note_content: 笔记内容
            para_structure: PARA 目录结构描述

        Returns:
            分类结果字典，包含解析后的分类信息
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
{note_content[:2000]}  

请返回严格的 JSON 格式结果（不要包含任何其他文本）：
{{
    "category": "projects|areas|resources|archives",
    "subcategory": "具体的子分类名称或路径",
    "target_path": "建议的完整目标路径（相对于vault根目录）",
    "confidence": 0.85,
    "reasoning": "详细的分类理由",
    "action_type": "move|create_and_move",
    "create_directories": ["需要创建的目录路径1", "需要创建的目录路径2"]
}}
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个 PARA 方法专家，帮助用户组织笔记。你必须只返回有效的JSON格式，不要包含任何其他文本。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.chat_completion(messages, temperature=0.3)

            # 尝试从响应中提取JSON
            parsed_result = self._parse_json_response(response)

            return {
                "success": True,
                "classification": parsed_result,
                "raw_response": response,
                "provider": self.provider,
                "model": self.model,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析失败: {str(e)}",
                "raw_response": response,
                "provider": self.provider,
                "model": self.model,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM API 调用失败: {str(e)}",
                "provider": self.provider,
                "model": self.model,
            }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应

        Args:
            response: LLM的原始响应

        Returns:
            解析后的字典

        Raises:
            json.JSONDecodeError: 如果无法解析JSON
        """
        # 移除可能的markdown代码块标记
        response = response.strip()
        response = re.sub(r"^```json\s*", "", response)
        response = re.sub(r"\s*```$", "", response)

        # 尝试解析JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise

    def optimize_structure(
        self, para_structure: str, notes_overview: str
    ) -> Dict[str, Any]:
        """分析并优化整体PARA结构

        Args:
            para_structure: 当前PARA目录结构
            notes_overview: 笔记概览信息

        Returns:
            优化建议字典
        """
        prompt = f"""
请分析以下PARA知识库结构，并提供优化建议。

当前结构：
{para_structure}

笔记概览：
{notes_overview}

请返回严格的JSON格式优化建议（不要包含任何其他文本）：
{{
    "overall_assessment": "整体评估",
    "suggestions": [
        {{
            "type": "rename|move|merge|create",
            "priority": "high|medium|low",
            "description": "建议描述",
            "current_path": "当前路径",
            "suggested_path": "建议路径",
            "reasoning": "建议理由"
        }}
    ],
    "structure_score": 0.75,
    "main_issues": ["主要问题1", "主要问题2"]
}}
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个知识管理专家，专门优化PARA系统结构。你必须只返回有效的JSON格式。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.chat_completion(messages, temperature=0.3)
            parsed_result = self._parse_json_response(response)

            return {
                "success": True,
                "optimization": parsed_result,
                "raw_response": response,
                "provider": self.provider,
                "model": self.model,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"结构优化分析失败: {str(e)}",
                "provider": self.provider,
                "model": self.model,
            }
