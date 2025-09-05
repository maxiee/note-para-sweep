"""LLM 客户端模块"""

import openai
import json
import re
from typing import Dict, Any, Optional
from .config import Config

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class LLMClient:
    """LLM 客户端，支持多个提供商"""

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.llm_provider
        self.api_key = config.llm_api_key
        self.model = config.llm_model
        self.base_url = config.llm_base_url
        self.proxy = config.llm_proxy

        # 检查是否为mock模式（API Key为空或包含mock）
        self.mock_mode = not self.api_key or "mock" in self.api_key.lower()

        # 对话历史管理
        self.conversation_history = []

        # 初始化客户端
        if not self.mock_mode:
            self._init_client()

    def _init_client(self):
        """初始化 LLM 客户端"""
        # 准备客户端参数
        client_kwargs = {
            "api_key": self.api_key,
        }

        # 如果设置了base_url，添加到参数中
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        # 如果设置了代理，创建带有代理的HTTP客户端
        if self.proxy and HTTPX_AVAILABLE:
            # 修复：proxies应该是字典格式，支持http和https
            proxies = {"http://": self.proxy, "https://": self.proxy}
            client_kwargs["http_client"] = httpx.Client(
                proxies=proxies, timeout=30.0  # 30秒超时
            )
        elif self.proxy and not HTTPX_AVAILABLE:
            print(f"⚠️  警告: 配置了代理但未安装 httpx，无法使用代理功能")
            print("请运行: pip install httpx")

        # 初始化客户端
        if self.provider == "openai":
            self.client = openai.OpenAI(**client_kwargs)
        elif self.provider == "openrouter":
            self.client = openai.OpenAI(**client_kwargs)
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

        # 输入验证
        if not messages or not isinstance(messages, list):
            raise ValueError("messages 参数必须是非空列表")

        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise ValueError("消息格式错误，必须包含 role 和 content 字段")

        # 带重试的API调用
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, **kwargs
                )

                if not response.choices or not response.choices[0].message:
                    raise Exception("API 返回了空响应")

                content = response.choices[0].message.content
                if not content:
                    raise Exception("API 返回了空内容")

                return content

            except openai.RateLimitError as e:
                last_error = f"请求频率限制: {str(e)}"
                if attempt < max_retries - 1:
                    import time

                    time.sleep(2**attempt)  # 指数退避
                    continue
            except openai.APIError as e:
                last_error = f"API 错误: {str(e)}"
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1)
                    continue
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1)
                    continue

        raise Exception(
            f"LLM API 调用失败 ({self.provider}) - 已重试 {max_retries} 次: {last_error}"
        )

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

    def classify_note(
        self,
        note_content: str,
        para_structure: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

    def refine_suggestion_interactive(
        self,
        original_suggestion: Dict[str, Any],
        user_feedback: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """交互式完善建议

        Args:
            original_suggestion: 原始建议
            user_feedback: 用户反馈
            context: 额外上下文信息

        Returns:
            完善后的建议字典
        """
        if context is None:
            context = {}

        prompt = f"""
你之前给出了一个PARA结构优化建议，现在用户提供了反馈，请根据反馈调整建议。

原始建议：
{json.dumps(original_suggestion, ensure_ascii=False, indent=2)}

用户反馈：
{user_feedback}

额外上下文：
{json.dumps(context, ensure_ascii=False, indent=2) if context else "无"}

请返回调整后的建议，保持相同的JSON格式。如果用户的反馈表明原建议不合适，请提供替代方案。
如果用户提供了具体的名称、时间等信息，请使用用户提供的准确信息替换之前的推测。

返回严格的JSON格式：
{{
    "type": "rename|move|merge|create",
    "priority": "high|medium|low", 
    "description": "调整后的建议描述",
    "current_path": "当前路径",
    "suggested_path": "调整后的建议路径",
    "reasoning": "调整理由，解释为什么根据用户反馈做出这些改变",
    "changes_made": "相比原建议的具体改动说明"
}}
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个PARA方法专家，善于根据用户反馈调整建议。你必须只返回有效的JSON格式。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.chat_completion(messages, temperature=0.3)
            parsed_result = self._parse_json_response(response)

            return {
                "success": True,
                "refined_suggestion": parsed_result,
                "raw_response": response,
                "original_suggestion": original_suggestion,
                "user_feedback": user_feedback,
                "provider": self.provider,
                "model": self.model,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"建议完善失败: {str(e)}",
                "original_suggestion": original_suggestion,
                "user_feedback": user_feedback,
                "provider": self.provider,
                "model": self.model,
            }

    def start_suggestion_conversation(
        self, suggestion: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ):
        """开始建议讨论对话

        Args:
            suggestion: 要讨论的建议
            context: 相关上下文
        """
        self.conversation_history = []

        # 添加初始建议到对话历史
        initial_message = {
            "role": "assistant",
            "content": f"我建议进行以下操作：\n\n"
            f"类型：{suggestion.get('type', '未知')}\n"
            f"描述：{suggestion.get('description', '无描述')}\n"
            f"当前路径：{suggestion.get('current_path', '无')}\n"
            f"建议路径：{suggestion.get('suggested_path', '无')}\n"
            f"理由：{suggestion.get('reasoning', '无理由')}\n\n"
            f"你对这个建议有什么想法或需要调整的地方吗？",
        }
        self.conversation_history.append(initial_message)

        # 保存原始建议和上下文
        self.current_suggestion = suggestion.copy()
        self.conversation_context = context or {}

    def continue_suggestion_conversation(self, user_input: str) -> Dict[str, Any]:
        """继续建议讨论对话

        Args:
            user_input: 用户输入

        Returns:
            AI回复和更新后的建议
        """
        if not hasattr(self, "conversation_history"):
            return {
                "success": False,
                "error": "尚未开始对话，请先调用 start_suggestion_conversation",
            }

        # 添加用户输入到对话历史
        self.conversation_history.append({"role": "user", "content": user_input})

        # 构建完整的对话上下文
        conversation_prompt = self._build_conversation_prompt(user_input)

        try:
            response = self.chat_completion(
                [
                    {
                        "role": "system",
                        "content": "你是PARA方法专家，正在与用户讨论结构优化建议。请友好地回应用户，并根据反馈调整建议。",
                    },
                    {"role": "user", "content": conversation_prompt},
                ],
                temperature=0.3,
            )

            # 添加AI回复到对话历史
            self.conversation_history.append({"role": "assistant", "content": response})

            # 尝试更新建议（如果用户提供了具体信息）
            updated_suggestion = self._extract_updated_suggestion(response, user_input)

            return {
                "success": True,
                "ai_response": response,
                "updated_suggestion": updated_suggestion,
                "conversation_history": self.conversation_history.copy(),
                "provider": self.provider,
                "model": self.model,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"对话失败: {str(e)}",
                "provider": self.provider,
                "model": self.model,
            }

    def _build_conversation_prompt(self, user_input: str) -> str:
        """构建对话提示"""
        prompt_parts = [
            "当前对话上下文：",
            f"原始建议：{json.dumps(self.current_suggestion, ensure_ascii=False, indent=2)}",
            "",
            "对话历史：",
        ]

        for msg in self.conversation_history[-3:]:  # 只保留最近3轮对话
            role = "用户" if msg["role"] == "user" else "AI"
            prompt_parts.append(f"{role}: {msg['content']}")

        prompt_parts.extend(
            [
                "",
                f"用户最新输入: {user_input}",
                "",
                "请回应用户的反馈，如果用户提供了具体信息（如准确的项目名称、时间等），"
                "请相应调整建议。保持友好的对话语调。",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_updated_suggestion(
        self, ai_response: str, user_input: str
    ) -> Dict[str, Any]:
        """从AI回复中提取更新的建议"""
        # 检查用户是否提供了具体的更正信息
        suggestion_updated = False
        updated_suggestion = self.current_suggestion.copy()

        # 简单的关键词检测和更新逻辑
        user_lower = user_input.lower()

        # 检查是否提到了具体的名称或时间
        if any(
            keyword in user_lower
            for keyword in ["应该叫", "改成", "实际是", "正确的是", "名字是"]
        ):
            # 这里可以添加更复杂的NLP提取逻辑
            # 目前先标记为已更新，具体提取逻辑可以后续完善
            suggestion_updated = True
            updated_suggestion["reasoning"] = (
                f"{updated_suggestion.get('reasoning', '')} (根据用户反馈调整)"
            )

        if suggestion_updated:
            self.current_suggestion = updated_suggestion

        return updated_suggestion

    def get_final_suggestion(self) -> Optional[Dict[str, Any]]:
        """获取最终完善后的建议"""
        if not hasattr(self, "current_suggestion"):
            return None
        return self.current_suggestion.copy()
