#!/usr/bin/env python3
"""
交互式建议讨论功能测试脚本
演示如何使用新的对话功能
"""

from pathlib import Path
import sys
import json

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from note_para_sweep.config import Config
from note_para_sweep.llm_client import LLMClient
from note_para_sweep.file_operations import FileOperator


def test_interactive_discussion():
    """测试交互式讨论功能"""
    print("🧪 测试交互式建议讨论功能\n")

    # 初始化配置（使用mock模式）
    config = Config("config.yaml")
    llm_client = LLMClient(config)
    file_operator = FileOperator(dry_run=True)

    # 模拟一个建议
    mock_suggestion = {
        "type": "rename",
        "priority": "high",
        "description": "将'移动应用开发'重命名为'App v1.0 2024-Q3'",
        "current_path": "1. Projects/移动应用开发",
        "suggested_path": "1. Projects/App v1.0 2024-Q3",
        "reasoning": "项目必须可完成且可衡量，模糊名称会拖延闭环。",
    }

    print("📋 模拟建议:")
    print(json.dumps(mock_suggestion, ensure_ascii=False, indent=2))
    print()

    # 开始对话
    print("🤖 开始对话...")
    llm_client.start_suggestion_conversation(mock_suggestion)

    # 模拟用户反馈
    user_feedbacks = [
        "这个项目实际上叫'智能记账App'，计划在2025年2月发布",
        "很好，但是我觉得不需要加月份，只写年份就够了",
        "满意",
    ]

    for i, feedback in enumerate(user_feedbacks, 1):
        print(f"[{i}] 用户: {feedback}")

        if feedback == "满意":
            break

        result = llm_client.continue_suggestion_conversation(feedback)

        if result["success"]:
            print(f"🤖 AI: {result['ai_response']}")
            print()
        else:
            print(f"❌ 对话失败: {result['error']}")
            break

    # 获取最终建议
    final_suggestion = llm_client.get_final_suggestion()
    if final_suggestion:
        print("✅ 最终建议:")
        print(json.dumps(final_suggestion, ensure_ascii=False, indent=2))
        print()

        # 记录建议历史
        conversation_history = getattr(llm_client, "conversation_history", [])
        file_operator.record_suggestion_history(
            original_suggestion=mock_suggestion,
            final_suggestion=final_suggestion,
            conversation_history=conversation_history,
            user_decision="accepted",
        )

        print("📝 建议历史已记录")

        # 显示历史记录摘要
        history = file_operator.get_suggestion_history()
        if history:
            latest = history[-1]
            print(f"📊 历史记录摘要:")
            print(f"   - 建议ID: {latest['suggestion_id']}")
            print(f"   - 用户决定: {latest['user_decision']}")
            print(f"   - 对话轮数: {len(latest.get('conversation_history', []))}")
            print(f"   - 时间戳: {latest['timestamp']}")


def test_suggestion_refinement():
    """测试建议完善功能"""
    print("\n" + "=" * 50)
    print("🧪 测试建议完善功能\n")

    config = Config("config.yaml")
    llm_client = LLMClient(config)

    original_suggestion = {
        "type": "create",
        "priority": "medium",
        "description": "在Areas下新增'职业成长'责任区",
        "current_path": "2. Areas",
        "suggested_path": "2. Areas/职业成长",
        "reasoning": "需要覆盖更多人生维度",
    }

    user_feedback = (
        "我觉得'职业成长'太宽泛了，能不能更具体一些？比如分成技术能力和软技能？"
    )

    print("📋 原始建议:")
    print(json.dumps(original_suggestion, ensure_ascii=False, indent=2))
    print(f"\n💬 用户反馈: {user_feedback}")

    result = llm_client.refine_suggestion_interactive(
        original_suggestion=original_suggestion, user_feedback=user_feedback
    )

    if result["success"]:
        print("\n✅ 完善后的建议:")
        print(json.dumps(result["refined_suggestion"], ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ 建议完善失败: {result['error']}")


if __name__ == "__main__":
    print("🚀 Note PARA Sweep - 交互式建议讨论功能测试\n")

    try:
        test_interactive_discussion()
        test_suggestion_refinement()

        print("\n" + "=" * 50)
        print("✅ 所有测试完成！")
        print("\n💡 使用提示:")
        print(
            "   运行 'poetry run note-para-sweep optimize' 然后选择 'd' 来体验交互式讨论功能"
        )

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
