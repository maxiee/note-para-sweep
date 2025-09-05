"""命令行界面"""

import click
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from .config import Config
from .scanner import DirectoryScanner
from .llm_client import LLMClient
from .file_operations import FileOperator


console = Console()


class LogFileManager:
    """日志文件管理器"""

    def __init__(self, log_file_path: Optional[str] = None):
        self.log_file_path = log_file_path
        self.session_started = False

    def start_session(self, command: str, config_info: dict):
        """开始新的日志会话"""
        if not self.log_file_path:
            return

        from datetime import datetime
        from pathlib import Path
        import sys

        try:
            # 确保日志目录存在
            log_path = Path(self.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.log_file_path, "a", encoding="utf-8") as f:
                if not self.session_started:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Note PARA Sweep - 详细日志\n")
                    f.write(
                        f"会话开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(f"执行命令: {command}\n")
                    f.write(f"Python版本: {sys.version}\n")
                    f.write(f"配置信息: {config_info}\n")
                    f.write(f"{'='*80}\n\n")
                    self.session_started = True
        except Exception as e:
            console.print(
                f"[red]警告: 无法写入日志文件 {self.log_file_path}: {e}[/red]"
            )
            self.log_file_path = None

    def write_log(self, message: str):
        """写入日志消息"""
        if not self.log_file_path:
            return

        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            # 静默失败，避免影响主程序
            pass


# 全局日志文件管理器
_log_manager = LogFileManager()


def verbose_log(message: str, verbose: bool = False, level: str = "info"):
    """条件性日志输出

    Args:
        message: 日志消息
        verbose: 是否启用详细模式
        level: 日志级别 (info, debug, warning, error)
    """
    if not verbose:
        return

    level_colors = {
        "debug": "dim cyan",
        "info": "cyan",
        "warning": "yellow",
        "error": "red",
    }

    color = level_colors.get(level, "white")
    prefix = f"[{level.upper()}]" if level != "info" else "[VERBOSE]"

    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")

    # 控制台输出
    console.print(f"[dim]{timestamp}[/dim] [{color}]{prefix}[/{color}] {message}")

    # 日志文件输出（纯文本格式）
    _log_manager.write_log(f"{timestamp} {prefix} {message}")


def verbose_log_json(label: str, data: dict, verbose: bool = False):
    """格式化输出JSON数据

    Args:
        label: 数据标签
        data: 要输出的字典数据
        verbose: 是否启用详细模式
    """
    if not verbose:
        return

    from datetime import datetime
    import json

    timestamp = datetime.now().strftime("%H:%M:%S")

    # 控制台输出
    console.print(f"\n[dim]{timestamp}[/dim] [dim cyan]━━━ {label} ━━━[/dim cyan]")
    console.print_json(data=data)
    console.print(
        "[dim cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim cyan]"
    )

    # 日志文件输出
    _log_manager.write_log(f"\n{timestamp} ━━━ {label} ━━━")
    _log_manager.write_log(json.dumps(data, ensure_ascii=False, indent=2))
    _log_manager.write_log("━" * 50)


@click.group()
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
@click.option("--dry-run", is_flag=True, help="试运行模式，不执行实际操作")
@click.option("--verbose", "-v", is_flag=True, help="详细输出模式，显示调试信息")
@click.option(
    "--log-file", "-l", help="保存详细日志到指定文件（需要同时启用--verbose）"
)
@click.pass_context
def cli(ctx, config, dry_run, verbose, log_file):
    """Note PARA Sweep - AI 驱动的 Obsidian 笔记 PARA 分类器"""
    ctx.ensure_object(dict)

    try:
        ctx.obj["config"] = Config(config)
        ctx.obj["dry_run"] = dry_run or ctx.obj["config"].dry_run_by_default
        ctx.obj["verbose"] = verbose
        ctx.obj["log_file"] = (
            log_file if verbose else None
        )  # 只有在verbose模式下才启用日志文件

        # 初始化日志文件管理器
        if ctx.obj["log_file"]:
            global _log_manager
            _log_manager = LogFileManager(ctx.obj["log_file"])

        # 显示欢迎信息
        if ctx.invoked_subcommand:
            console.print(
                Panel(
                    "[bold blue]Note PARA Sweep[/bold blue]\n"
                    "AI 驱动的 Obsidian 笔记 PARA 分类器",
                    title="欢迎",
                    expand=False,
                )
            )

            if ctx.obj["dry_run"]:
                console.print(
                    "[yellow]⚠️  当前处于试运行模式，不会执行实际的文件操作[/yellow]"
                )

            if ctx.obj["log_file"]:
                console.print(f"[green]📝 日志将保存到: {ctx.obj['log_file']}[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]配置文件错误: {e}[/red]")
        console.print("[dim]提示: 请确保配置文件存在且格式正确[/dim]")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]配置验证错误: {e}[/red]")
        console.print("[dim]提示: 请检查配置文件中的参数设置[/dim]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]初始化错误: {e}[/red]")
        console.print("[dim]如果问题持续存在，请检查配置文件或联系支持[/dim]")
        raise click.Abort()


@cli.command()
@click.pass_context
def scan(ctx):
    """扫描 PARA 目录结构"""
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    log_file = ctx.obj["log_file"]

    # 初始化日志会话
    if log_file:
        _log_manager.start_session(
            "scan",
            {
                "vault_path": str(config.vault_path),
                "para_paths": config.para_paths,
                "verbose": verbose,
                "log_file": log_file,
            },
        )

    console.print("[blue]正在扫描 PARA 目录结构...[/blue]")
    verbose_log(f"扫描目标路径: {config.vault_path}", verbose)
    verbose_log(f"PARA 路径配置: {config.para_paths}", verbose)

    scanner = DirectoryScanner(config.vault_path, config.para_paths)
    scan_result = scanner.scan()

    verbose_log_json(
        "详细扫描结果",
        {
            "vault_path": str(config.vault_path),
            "scan_details": {
                path: {
                    "note_count": info.note_count,
                    "subdirs": [
                        {
                            "name": sub.name,
                            "note_count": sub.note_count,
                            "path": str(sub.path),
                        }
                        for sub in info.subdirs
                    ],
                }
                for path, info in scan_result.items()
            },
        },
        verbose,
    )

    # 生成并显示结构摘要
    summary = scanner.generate_structure_summary(scan_result)
    console.print(Panel(summary, title="目录结构", expand=True))

    # 统计信息
    total_notes = sum(dir_info.note_count for dir_info in scan_result.values())
    console.print(f"\n[green]✅ 扫描完成！共发现 {total_notes} 篇笔记[/green]")
    verbose_log(
        f"统计详情: {[(path, info.note_count) for path, info in scan_result.items()]}",
        verbose,
    )


@cli.command()
@click.argument("note_path", type=click.Path(exists=True))
@click.pass_context
def classify(ctx, note_path):
    """分类单个笔记文件"""
    config = ctx.obj["config"]
    dry_run = ctx.obj["dry_run"]
    verbose = ctx.obj["verbose"]
    log_file = ctx.obj["log_file"]

    # 初始化日志会话
    if log_file:
        _log_manager.start_session(
            f"classify {note_path}",
            {
                "note_path": str(note_path),
                "vault_path": str(config.vault_path),
                "dry_run": dry_run,
                "verbose": verbose,
                "log_file": log_file,
            },
        )

    note_path = Path(note_path)

    console.print(f"[blue]正在分析笔记: {note_path}[/blue]")

    try:
        # 读取笔记内容
        with open(note_path, "r", encoding="utf-8") as f:
            note_content = f.read()

        # 获取 PARA 结构
        scanner = DirectoryScanner(config.vault_path, config.para_paths)
        scan_result = scanner.scan()
        para_structure = scanner.generate_structure_summary(scan_result)

        # 初始化 LLM 客户端
        llm_client = LLMClient(
            config, verbose=verbose, log_file_manager=_log_manager if log_file else None
        )

        console.print("[yellow]正在使用 AI 分析笔记...[/yellow]")
        console.print(
            f"[dim]使用提供商: {config.llm_provider} | 模型: {config.llm_model}[/dim]"
        )

        # 调用 AI 分类
        result = llm_client.classify_note(note_content, para_structure)

        if not result["success"]:
            console.print(f"[red]AI 分析失败: {result['error']}[/red]")
            if "raw_response" in result:
                console.print(f"[dim]原始响应: {result['raw_response'][:200]}...[/dim]")
            return

        classification = result["classification"]

        # 检查是否是question类型的回复
        if classification.get("action_type") == "question":
            question = classification.get("question", "")
            question_context = classification.get("question_context", "")

            console.print(
                "\n[bold blue]🤖 AI 需要更多信息来准确分类这个笔记：[/bold blue]"
            )
            console.print(f"[yellow]{question}[/yellow]")

            if question_context:
                console.print(f"[dim]背景：{question_context}[/dim]")

            console.print(
                f"\n[dim]分类原因：{classification.get('reasoning', '无原因说明')}[/dim]"
            )
            console.print("\n[dim]请提供相关信息，或输入 'cancel' 取消分类[/dim]")

            user_answer = click.prompt(
                "你的回答", default="", show_default=False
            ).strip()

            if not user_answer or user_answer.lower() in ["cancel", "取消"]:
                console.print("[yellow]分类操作已取消[/yellow]")
                return

            # 基于用户回答重新分类
            console.print("[dim]AI正在基于你的回答重新分类...[/dim]")

            try:
                follow_up_prompt = f"""
基于用户的回答，请重新分类这个笔记。

原始问题：{question}
用户回答：{user_answer}
笔记内容：{note_content[:1000]}

请返回具体的分类结果：
{{
    "category": "projects|areas|resources|archives",
    "subcategory": "具体的子分类名称",
    "target_path": "具体的完整目标文件路径（包含.md扩展名）",
    "confidence": 0.85,
    "reasoning": "基于用户回答的分类理由",
    "action_type": "move|create_and_move",
    "create_directories": ["需要创建的目录路径"]
}}
"""

                messages = [
                    {
                        "role": "system",
                        "content": "你是PARA方法专家，根据用户提供的信息重新分类笔记。必须返回有效的JSON格式。",
                    },
                    {"role": "user", "content": follow_up_prompt},
                ]

                response = llm_client.chat_completion(messages, temperature=0.3)
                classification = llm_client._parse_json_response(response)

                console.print(
                    "\n[bold green]✅ 基于你的回答，AI 重新分类了这个笔记：[/bold green]"
                )

            except Exception as e:
                console.print(f"[red]重新分类失败: {str(e)}[/red]")
                return

        # 显示分类结果
        _display_classification_result(classification, result)

        # 用户确认
        if classification.get("confidence", 0) < 0.7:
            console.print("[yellow]⚠️  AI 对此分类的信心较低，请仔细检查建议[/yellow]")

        if dry_run:
            console.print("[yellow]试运行模式：以下是将要执行的操作预览[/yellow]")
            _preview_operations(classification, note_path, config.vault_path)
        else:
            if Confirm.ask("是否执行此分类操作？"):
                # 执行文件操作
                file_operator = FileOperator(dry_run=False)
                operation_result = file_operator.execute_classification(
                    note_path, classification, config.vault_path
                )

                _display_operation_result(operation_result)
            else:
                console.print("[yellow]操作已取消[/yellow]")

    except Exception as e:
        console.print(f"[red]分类失败: {e}[/red]")


def _display_classification_result(classification: dict, result: dict):
    """显示分类结果"""
    table = Table(title="AI 分类结果")
    table.add_column("属性", style="cyan")
    table.add_column("值", style="white")

    table.add_row("分类", classification.get("category", "未知").upper())
    table.add_row("子分类", classification.get("subcategory", "未指定"))
    table.add_row("目标路径", classification.get("target_path", "未指定"))
    table.add_row("信心度", f"{classification.get('confidence', 0):.2f}")
    table.add_row("操作类型", classification.get("action_type", "move"))

    console.print(table)

    # 显示分类理由
    reasoning = classification.get("reasoning", "无理由说明")
    console.print(Panel(reasoning, title="分类理由", expand=False))


def _preview_operations(classification: dict, source_path: Path, vault_path: Path):
    """预览将要执行的操作"""
    console.print("\n[bold]将要执行的操作：[/bold]")

    # 显示目录创建操作
    create_dirs = classification.get("create_directories", [])
    if create_dirs:
        console.print("[cyan]创建目录：[/cyan]")
        for dir_path in create_dirs:
            console.print(f"  📁 {vault_path / dir_path}")

    # 显示文件移动操作
    target_path = classification.get("target_path", "")
    if target_path:
        console.print(f"[cyan]移动文件：[/cyan]")
        console.print(f"  📄 {source_path} → {vault_path / target_path}")


def _display_operation_result(operation_result: dict):
    """显示操作执行结果"""
    if operation_result["success"]:
        console.print(
            f"[green]✅ 分类完成！文件已移动到: {operation_result['final_path']}[/green]"
        )
    else:
        console.print(f"[red]❌ 操作失败: {operation_result['error']}[/red]")

    # 显示操作详情
    operations = operation_result.get("operations", [])
    if operations:
        console.print("\n[bold]操作详情：[/bold]")
        for i, op in enumerate(operations, 1):
            status = "✅" if op["success"] else "❌"
            op_type = op["operation"].replace("_", " ").title()
            console.print(f"  {i}. {status} {op_type}")
            if "error" in op and op["error"]:
                console.print(f"     [red]错误: {op['error']}[/red]")


@cli.command()
@click.pass_context
def optimize(ctx):
    """优化整体 PARA 结构"""
    config = ctx.obj["config"]
    dry_run = ctx.obj["dry_run"]
    verbose = ctx.obj["verbose"]
    log_file = ctx.obj["log_file"]

    # 初始化日志会话
    if log_file:
        _log_manager.start_session(
            "optimize",
            {
                "vault_path": str(config.vault_path),
                "para_paths": config.para_paths,
                "dry_run": dry_run,
                "verbose": verbose,
                "log_file": log_file,
            },
        )

    console.print("[blue]正在分析整体 PARA 结构...[/blue]")

    if not Confirm.ask("这将分析你的整个知识库结构，继续吗？"):
        console.print("操作已取消")
        return

    try:
        # 扫描目录结构
        verbose_log("开始扫描目录结构", verbose)
        scanner = DirectoryScanner(config.vault_path, config.para_paths)
        scan_result = scanner.scan()

        verbose_log_json(
            "目录扫描结果",
            {
                "para_paths": config.para_paths,
                "vault_path": str(config.vault_path),
                "scan_summary": {
                    path: {
                        "note_count": info.note_count,
                        "subdirs": [
                            {"name": sub.name, "note_count": sub.note_count}
                            for sub in info.subdirs
                        ],
                    }
                    for path, info in scan_result.items()
                },
            },
            verbose,
        )

        para_structure = scanner.generate_structure_summary(scan_result)
        verbose_log(f"生成的PARA结构摘要:\n{para_structure}", verbose)

        # 生成笔记概览
        notes_overview = _generate_notes_overview(scan_result)
        verbose_log(f"生成的笔记概览:\n{notes_overview}", verbose)

        # 初始化 LLM 客户端和文件操作器
        verbose_log(
            f"初始化LLM客户端 - 提供商: {config.llm_provider}, 模型: {config.llm_model}",
            verbose,
        )
        llm_client = LLMClient(
            config, verbose=verbose, log_file_manager=_log_manager if log_file else None
        )
        file_operator = FileOperator(dry_run=dry_run)

        # 加载建议历史
        verbose_log("加载建议历史", verbose)
        file_operator.load_suggestion_history()

        console.print("[yellow]正在使用 AI 分析结构优化机会...[/yellow]")
        console.print(
            f"[dim]使用提供商: {config.llm_provider} | 模型: {config.llm_model}[/dim]"
        )

        # 记录LLM请求
        verbose_log("准备发送LLM请求进行结构分析", verbose)
        verbose_log_json(
            "LLM请求参数",
            {
                "para_structure_length": len(para_structure),
                "notes_overview_length": len(notes_overview),
                "provider": config.llm_provider,
                "model": config.llm_model,
            },
            verbose,
        )

        # 调用结构优化分析
        result = llm_client.optimize_structure(para_structure, notes_overview)

        verbose_log_json("LLM完整响应", result, verbose)

        if not result["success"]:
            console.print(f"[red]结构分析失败: {result['error']}[/red]")
            verbose_log(f"失败详情: {result}", verbose, "error")
            return

        optimization = result["optimization"]
        verbose_log_json("解析后的优化建议", optimization, verbose)

        # 显示整体评估
        _display_structure_assessment(optimization)

        # 显示优化建议
        suggestions = optimization.get("suggestions", [])
        if not suggestions:
            console.print(
                "[green]🎉 你的 PARA 结构看起来很不错，暂无优化建议！[/green]"
            )
            return

        console.print(f"\n[bold]发现 {len(suggestions)} 条优化建议：[/bold]")
        verbose_log(f"建议总数: {len(suggestions)}", verbose)

        # 逐条处理建议
        for i, suggestion in enumerate(suggestions, 1):
            verbose_log_json(f"处理建议 {i}", suggestion, verbose)

            console.print(f"\n[bold cyan]建议 {i}/{len(suggestions)}:[/bold cyan]")

            # 特殊处理question类型的建议
            if suggestion.get("type") == "question":
                _display_optimization_suggestion(suggestion)

                if dry_run:
                    console.print("[yellow]试运行模式：显示问题但不处理[/yellow]")
                    continue

                # 处理AI的问题并获取新建议
                new_suggestion = _handle_question_suggestion(suggestion, llm_client)
                if new_suggestion:
                    # 验证新建议的路径
                    is_valid, error_message = _validate_suggestion_paths(
                        new_suggestion, config.vault_path
                    )
                    if is_valid:
                        _display_optimization_suggestion(new_suggestion)
                        if Confirm.ask("执行这个基于你回答生成的建议吗？"):
                            execution_result = _execute_suggestion(
                                new_suggestion, config, file_operator, verbose
                            )
                            _display_execution_result(execution_result, new_suggestion)
                    else:
                        console.print(
                            f"[red]生成的建议路径验证失败: {error_message}[/red]"
                        )
                else:
                    console.print("跳过此建议")
                continue

            # 验证建议中的路径
            is_valid, error_message = _validate_suggestion_paths(
                suggestion, config.vault_path
            )
            if not is_valid:
                console.print(f"[red]⚠️  建议路径验证失败: {error_message}[/red]")
                console.print(
                    "[yellow]建议内容可能包含描述性文本而非具体路径，请修改后重试[/yellow]"
                )

                # 显示原始建议供参考
                _display_optimization_suggestion(suggestion)

                if not dry_run:
                    console.print(
                        "[dim]选项: n=跳过, d=与AI讨论修正, s=全部跳过, q=退出[/dim]"
                    )
                    choice = click.prompt(
                        "选择操作",
                        type=click.Choice(["n", "d", "s", "q"]),
                        default="n",
                        show_choices=True,
                    )

                    if choice == "q":
                        console.print("退出优化模式")
                        break
                    elif choice == "s":
                        console.print("跳过剩余所有建议")
                        break
                    elif choice == "d":
                        # 进入讨论模式修正路径
                        console.print("[yellow]请与AI讨论以修正路径信息[/yellow]")
                        final_suggestion = _interactive_discussion(
                            llm_client, suggestion
                        )
                        if final_suggestion:
                            # 重新验证修正后的建议
                            is_valid_after, error_after = _validate_suggestion_paths(
                                final_suggestion, config.vault_path
                            )
                            if is_valid_after:
                                console.print(
                                    "\n[bold cyan]修正后的建议通过验证：[/bold cyan]"
                                )
                                _display_optimization_suggestion(final_suggestion)
                                if Confirm.ask("执行这个修正后的建议吗？"):
                                    execution_result = _execute_suggestion(
                                        final_suggestion, config, file_operator, verbose
                                    )
                                    _display_execution_result(
                                        execution_result, final_suggestion
                                    )
                            else:
                                console.print(
                                    f"[red]修正后的建议仍然验证失败: {error_after}[/red]"
                                )
                continue

            _display_optimization_suggestion(suggestion)

            if dry_run:
                console.print("[yellow]试运行模式：显示建议但不执行操作[/yellow]")
                continue

            # 用户选择
            console.print(
                "[dim]选项: y=执行, n=跳过, d=与AI讨论, s=全部跳过, q=退出[/dim]"
            )
            choice = click.prompt(
                "选择操作",
                type=click.Choice(["y", "n", "d", "s", "q"]),
                default="n",
                show_choices=True,
            )

            verbose_log(f"用户选择: {choice}", verbose)

            if choice == "q":
                console.print("退出优化模式")
                break
            elif choice == "s":
                console.print("跳过剩余所有建议")
                break
            elif choice == "d":
                verbose_log("进入交互式讨论模式", verbose)
                # 进入与AI的交互式讨论
                final_suggestion = _interactive_discussion(llm_client, suggestion)
                if final_suggestion:
                    # 记录建议历史
                    conversation_history = (
                        llm_client.conversation_history
                        if hasattr(llm_client, "conversation_history")
                        else []
                    )
                    verbose_log_json(
                        "对话历史", {"conversation": conversation_history}, verbose
                    )

                    file_operator.record_suggestion_history(
                        original_suggestion=suggestion,
                        final_suggestion=final_suggestion,
                        conversation_history=conversation_history,
                        user_decision="discussed",
                    )

                    # 显示最终建议
                    console.print("\n[bold cyan]讨论后的最终建议：[/bold cyan]")
                    _display_optimization_suggestion(final_suggestion)

                    if Confirm.ask("执行这个最终建议吗？"):
                        file_operator.record_suggestion_history(
                            original_suggestion=suggestion,
                            final_suggestion=final_suggestion,
                            conversation_history=conversation_history,
                            user_decision="accepted",
                        )
                        # 执行最终建议
                        console.print("[yellow]正在执行建议...[/yellow]")
                        execution_result = _execute_suggestion(
                            final_suggestion, config, file_operator, verbose
                        )
                        _display_execution_result(execution_result, final_suggestion)
                    else:
                        file_operator.record_suggestion_history(
                            original_suggestion=suggestion,
                            final_suggestion=final_suggestion,
                            conversation_history=conversation_history,
                            user_decision="rejected_after_discussion",
                        )
                        console.print("跳过此建议")
                else:
                    # 记录取消的讨论
                    file_operator.record_suggestion_history(
                        original_suggestion=suggestion,
                        user_decision="discussion_cancelled",
                    )
                    console.print("[yellow]讨论已取消[/yellow]")
            elif choice == "y":
                # 记录直接接受的建议
                file_operator.record_suggestion_history(
                    original_suggestion=suggestion, user_decision="accepted_directly"
                )
                # 执行建议
                console.print("[yellow]正在执行建议...[/yellow]")
                execution_result = _execute_suggestion(
                    suggestion, config, file_operator, verbose
                )
                _display_execution_result(execution_result, suggestion)
            else:
                # 记录跳过的建议
                file_operator.record_suggestion_history(
                    original_suggestion=suggestion, user_decision="skipped"
                )
                console.print("跳过此建议")

    except Exception as e:
        console.print(f"[red]结构优化失败: {e}[/red]")
        verbose_log(f"异常详情: {str(e)}", verbose, "error")
        if verbose:
            import traceback

            verbose_log(f"完整堆栈跟踪:\n{traceback.format_exc()}", verbose, "error")


def _generate_notes_overview(scan_result: dict) -> str:
    """生成笔记概览信息"""
    overview_lines = ["# 笔记概览\n"]

    total_notes = 0
    for para_type, dir_info in scan_result.items():
        total_notes += dir_info.note_count
        overview_lines.append(f"## {para_type.upper()}: {dir_info.note_count} 篇笔记")

        # 添加子目录信息
        if dir_info.subdirs:
            for subdir in dir_info.subdirs:
                overview_lines.append(f"  - {subdir.name}: {subdir.note_count} 篇")

    overview_lines.insert(1, f"总笔记数: {total_notes}\n")
    return "\n".join(overview_lines)


def _display_structure_assessment(optimization: dict):
    """显示结构评估结果"""
    assessment = optimization.get("overall_assessment", "无评估")
    score = optimization.get("structure_score", 0)
    issues = optimization.get("main_issues", [])

    # 评估面板
    assessment_text = f"[bold]整体评估：[/bold]{assessment}\n"
    assessment_text += f"[bold]结构评分：[/bold]{score:.2f}/1.0\n"

    if issues:
        assessment_text += f"\n[bold]主要问题：[/bold]\n"
        for issue in issues:
            assessment_text += f"• {issue}\n"

    console.print(Panel(assessment_text, title="PARA 结构分析", expand=False))


def _validate_suggestion_paths(suggestion: dict, vault_path: Path) -> tuple[bool, str]:
    """验证建议中的路径是否有效

    Args:
        suggestion: 要验证的建议
        vault_path: vault根目录路径

    Returns:
        (is_valid, error_message) - 验证结果和错误信息
    """
    suggestion_type = suggestion.get("type", "")
    current_path = suggestion.get("current_path", "")
    suggested_path = suggestion.get("suggested_path", "")

    # 对于question类型的建议，不需要验证路径
    if suggestion_type == "question":
        return True, ""

    # 检查是否包含描述性文本而非具体路径
    descriptive_patterns = [
        "对应",
        "合适的",
        "相关的",
        "适当的",
        "正确的",
        "P/A/R",
        "子目录",
        "目录",
        "位置",
        "地方",
    ]

    for pattern in descriptive_patterns:
        if pattern in current_path or pattern in suggested_path:
            return False, f"路径包含描述性文本而非具体路径: {pattern}"

    # 检查是否为空或过于泛化
    if not current_path.strip() and suggestion.get("type") in ["move", "rename"]:
        return False, "移动/重命名操作必须指定具体的当前路径"

    if not suggested_path.strip():
        return False, "必须指定具体的目标路径"

    # 检查路径格式是否合理
    if suggested_path in ["无", "未知", "待定", "TBD"]:
        return False, f"路径格式无效: {suggested_path}"

    # 检查是否包含PARA标准目录结构
    para_prefixes = [
        "0. Inbox",
        "1. Projects",
        "2. Areas",
        "3. Resources",
        "4. Archives",
    ]
    if suggestion.get("type") in ["move", "create"] and not any(
        suggested_path.startswith(prefix) for prefix in para_prefixes
    ):
        return (
            False,
            f"目标路径应该基于PARA结构 (0. Inbox, 1. Projects, 2. Areas, 3. Resources, 4. Archives): {suggested_path}",
        )

    # 对于移动操作，检查当前路径是否存在（如果不为空）
    if current_path and suggestion.get("type") in ["move", "rename"]:
        current_full_path = vault_path / current_path
        if not current_full_path.exists():
            return False, f"当前路径不存在: {current_path}"

    return True, ""


def _display_optimization_suggestion(suggestion: dict):
    """显示单个优化建议"""
    suggestion_type = suggestion.get("type", "unknown")
    priority = suggestion.get("priority", "medium")
    description = suggestion.get("description", "无描述")
    reasoning = suggestion.get("reasoning", "无理由")
    current_path = suggestion.get("current_path", "")
    suggested_path = suggestion.get("suggested_path", "")

    # 优先级颜色
    priority_colors = {"high": "red", "medium": "yellow", "low": "green"}
    priority_color = priority_colors.get(priority, "white")

    # 特殊处理question类型
    if suggestion_type == "question":
        question = suggestion.get("question", "无问题")
        question_context = suggestion.get("question_context", "")

        table = Table(title="❓ AI 需要更多信息")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="white")

        table.add_row(
            "优先级", f"[{priority_color}]{priority.upper()}[/{priority_color}]"
        )
        table.add_row("问题", question)
        if question_context:
            table.add_row("背景", question_context)
        if current_path:
            table.add_row("相关路径", current_path)

        console.print(table)
        console.print(Panel(reasoning, title="AI 为什么需要这个信息", expand=False))
        return

    # 普通建议的显示
    table = Table(title=f"{suggestion_type.upper()} 建议")
    table.add_column("属性", style="cyan")
    table.add_column("值", style="white")

    table.add_row("优先级", f"[{priority_color}]{priority.upper()}[/{priority_color}]")
    table.add_row("描述", description)
    if current_path:
        table.add_row("当前路径", current_path)
    if suggested_path:
        table.add_row("建议路径", suggested_path)

    console.print(table)
    console.print(Panel(reasoning, title="建议理由", expand=False))


def _handle_question_suggestion(
    suggestion: dict, llm_client: LLMClient
) -> Optional[dict]:
    """处理question类型的建议，与用户交互获取信息后生成新建议

    Args:
        suggestion: question类型的建议
        llm_client: LLM客户端

    Returns:
        用户提供信息后生成的新建议，如果用户取消则返回None
    """
    question = suggestion.get("question", "")
    question_context = suggestion.get("question_context", "")

    console.print("\n[bold blue]🤖 AI 需要更多信息来提供准确的建议：[/bold blue]")
    console.print(f"[yellow]{question}[/yellow]")

    if question_context:
        console.print(f"[dim]背景：{question_context}[/dim]")

    console.print("\n[dim]请提供相关信息，或输入 'skip' 跳过此建议[/dim]")

    # 获取用户输入
    user_answer = click.prompt("你的回答", default="", show_default=False).strip()

    if not user_answer or user_answer.lower() in ["skip", "跳过"]:
        console.print("[yellow]已跳过此建议[/yellow]")
        return None

    # 使用LLM基于用户提供的信息生成新建议
    console.print("[dim]AI正在基于你的回答生成具体建议...[/dim]")

    try:
        # 构建包含用户回答的prompt
        follow_up_prompt = f"""
基于用户的回答，请提供具体的操作建议。

原始问题：{question}
用户回答：{user_answer}
原始建议上下文：{suggestion.get('reasoning', '')}

请返回具体的操作建议，必须包含明确的路径。格式如下：
{{
    "type": "rename|move|merge|create",
    "priority": "high|medium|low",
    "description": "具体的操作描述",
    "current_path": "当前路径（如果适用）",
    "suggested_path": "具体的目标路径",
    "reasoning": "基于用户回答的具体理由"
}}
"""

        messages = [
            {
                "role": "system",
                "content": "你是PARA方法专家，根据用户提供的信息生成具体的操作建议。必须返回有效的JSON格式。",
            },
            {"role": "user", "content": follow_up_prompt},
        ]

        response = llm_client.chat_completion(messages, temperature=0.3)
        new_suggestion = llm_client._parse_json_response(response)

        console.print(
            "\n[bold green]✅ 基于你的回答，AI 生成了以下具体建议：[/bold green]"
        )
        return new_suggestion

    except Exception as e:
        console.print(f"[red]生成新建议失败: {str(e)}[/red]")
        return None


def _execute_suggestion(
    suggestion: dict, config: Config, file_operator: FileOperator, verbose: bool = False
) -> dict:
    """执行优化建议

    Args:
        suggestion: 要执行的建议
        config: 配置对象
        file_operator: 文件操作器
        verbose: 是否详细输出

    Returns:
        执行结果字典
    """
    suggestion_type = suggestion.get("type", "").lower()
    current_path = suggestion.get("current_path", "")
    suggested_path = suggestion.get("suggested_path", "")

    result = {
        "success": False,
        "operation": suggestion_type,
        "details": [],
        "error": None,
    }

    try:
        vault_path = config.vault_path

        # 最后一次路径验证
        is_valid, error_message = _validate_suggestion_paths(suggestion, vault_path)
        if not is_valid:
            result["error"] = f"执行前路径验证失败: {error_message}"
            return result

        # 构建完整路径
        if current_path and not current_path.startswith("/"):
            current_full_path = vault_path / current_path
        else:
            current_full_path = (
                vault_path / current_path.lstrip("/") if current_path else None
            )

        if suggested_path and not suggested_path.startswith("/"):
            suggested_full_path = vault_path / suggested_path
        else:
            suggested_full_path = vault_path / suggested_path.lstrip("/")

        verbose_log(f"执行建议类型: {suggestion_type}", verbose)
        if current_full_path:
            verbose_log(f"当前路径: {current_full_path}", verbose)
        verbose_log(f"目标路径: {suggested_full_path}", verbose)

        # 执行前的安全检查和用户确认
        if suggestion_type in ["move", "rename"] and current_full_path:
            if not current_full_path.exists():
                result["error"] = f"源路径不存在: {current_full_path}"
                return result

            # 检查目标路径是否会覆盖现有文件/目录
            if suggested_full_path.exists():
                console.print(
                    f"[yellow]⚠️  目标路径已存在: {suggested_full_path}[/yellow]"
                )
                if not Confirm.ask("是否要覆盖现有的文件/目录？"):
                    result["error"] = "用户取消操作：目标路径已存在"
                    return result

        # 根据建议类型执行相应操作
        if suggestion_type == "move":
            if not current_full_path:
                result["error"] = "移动操作需要指定当前路径"
                return result
            return _execute_move_suggestion(
                current_full_path, suggested_full_path, file_operator, verbose
            )
        elif suggestion_type == "rename":
            if not current_full_path:
                result["error"] = "重命名操作需要指定当前路径"
                return result
            return _execute_rename_suggestion(
                current_full_path, suggested_full_path, file_operator, verbose
            )
        elif suggestion_type == "create":
            return _execute_create_suggestion(
                suggested_full_path, file_operator, verbose
            )
        elif suggestion_type == "merge":
            if not current_full_path:
                result["error"] = "合并操作需要指定当前路径"
                return result
            return _execute_merge_suggestion(
                current_full_path, suggested_full_path, file_operator, verbose
            )
        else:
            result["error"] = f"不支持的建议类型: {suggestion_type}"
            return result

    except Exception as e:
        result["error"] = f"执行建议时发生错误: {str(e)}"
        verbose_log(f"执行建议失败: {str(e)}", verbose, "error")
        return result


def _execute_move_suggestion(
    current_path: Path, target_path: Path, file_operator: FileOperator, verbose: bool
) -> dict:
    """执行移动建议"""
    result = {"success": False, "operation": "move", "details": [], "error": None}

    try:
        # 检查源路径是否存在
        if not current_path.exists():
            result["error"] = f"源路径不存在: {current_path}"
            return result

        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if current_path.is_file():
            # 移动文件
            move_result = file_operator.move_file(current_path, target_path)
            result["details"].append(move_result)
            result["success"] = move_result["success"]
            if not move_result["success"]:
                result["error"] = move_result["error"]
        elif current_path.is_dir():
            # 移动目录（重命名）
            import shutil

            if not file_operator.dry_run:
                shutil.move(str(current_path), str(target_path))
            result["success"] = True
            result["details"].append(
                {
                    "operation": "move_directory",
                    "source": str(current_path),
                    "target": str(target_path),
                    "success": True,
                }
            )
            verbose_log(f"目录移动完成: {current_path} -> {target_path}", verbose)

        return result

    except Exception as e:
        result["error"] = f"移动操作失败: {str(e)}"
        return result


def _execute_rename_suggestion(
    current_path: Path, target_path: Path, file_operator: FileOperator, verbose: bool
) -> dict:
    """执行重命名建议"""
    # 重命名实际上就是移动操作
    return _execute_move_suggestion(current_path, target_path, file_operator, verbose)


def _execute_create_suggestion(
    target_path: Path, file_operator: FileOperator, verbose: bool
) -> dict:
    """执行创建建议"""
    result = {"success": False, "operation": "create", "details": [], "error": None}

    try:
        if target_path.suffix == ".md" or "." in target_path.name:
            # 创建文件
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_operator.dry_run:
                target_path.touch()
            result["success"] = True
            result["details"].append(
                {"operation": "create_file", "path": str(target_path), "success": True}
            )
            verbose_log(f"文件创建完成: {target_path}", verbose)
        else:
            # 创建目录
            create_result = file_operator.create_directory(target_path)
            result["details"].append(create_result)
            result["success"] = create_result["success"]
            if not create_result["success"]:
                result["error"] = create_result["error"]

        return result

    except Exception as e:
        result["error"] = f"创建操作失败: {str(e)}"
        return result


def _execute_merge_suggestion(
    source_path: Path, target_path: Path, file_operator: FileOperator, verbose: bool
) -> dict:
    """执行合并建议"""
    result = {"success": False, "operation": "merge", "details": [], "error": None}

    try:
        # 合并操作比较复杂，这里实现一个简单版本：移动源目录下的所有内容到目标目录
        if not source_path.exists() or not source_path.is_dir():
            result["error"] = f"源目录不存在或不是目录: {source_path}"
            return result

        # 确保目标目录存在
        target_path.mkdir(parents=True, exist_ok=True)

        # 移动源目录下的所有内容
        moved_items = []
        for item in source_path.iterdir():
            target_item = target_path / item.name
            if item.is_file():
                move_result = file_operator.move_file(item, target_item)
                moved_items.append(move_result)
            elif item.is_dir():
                import shutil

                if not file_operator.dry_run:
                    shutil.move(str(item), str(target_item))
                moved_items.append(
                    {
                        "operation": "move_directory",
                        "source": str(item),
                        "target": str(target_item),
                        "success": True,
                    }
                )

        # 删除空的源目录
        if not file_operator.dry_run and not any(source_path.iterdir()):
            source_path.rmdir()

        result["details"] = moved_items
        result["success"] = all(item.get("success", False) for item in moved_items)
        verbose_log(f"合并操作完成: {len(moved_items)} 个项目已移动", verbose)

        return result

    except Exception as e:
        result["error"] = f"合并操作失败: {str(e)}"
        return result


def _display_execution_result(result: dict, suggestion: dict):
    """显示执行结果"""
    if result["success"]:
        console.print(f"[green]✅ {result['operation'].upper()} 操作执行成功！[/green]")

        # 显示操作详情
        if result["details"]:
            console.print("\n[bold]操作详情：[/bold]")
            for i, detail in enumerate(result["details"], 1):
                status = "✅" if detail.get("success", False) else "❌"
                op_name = detail.get("operation", "unknown").replace("_", " ").title()
                console.print(f"  {i}. {status} {op_name}")

                if "source" in detail and "target" in detail:
                    console.print(f"     {detail['source']} → {detail['target']}")
                elif "path" in detail:
                    console.print(f"     {detail['path']}")

                if "error" in detail and detail["error"]:
                    console.print(f"     [red]错误: {detail['error']}[/red]")
    else:
        console.print(f"[red]❌ {result['operation'].upper()} 操作执行失败[/red]")
        if result["error"]:
            console.print(f"[red]错误: {result['error']}[/red]")


def _interactive_discussion(llm_client: LLMClient, suggestion: dict) -> Optional[dict]:
    """与AI进行交互式建议讨论

    Args:
        llm_client: LLM客户端
        suggestion: 要讨论的建议

    Returns:
        最终确定的建议，如果取消则返回None
    """
    console.print("\n[bold blue]🤖 进入与AI的交互式讨论模式[/bold blue]")
    console.print("[dim]你可以告诉AI你的想法、提供准确信息或要求调整建议[/dim]")
    console.print("[dim]输入 'exit' 或 'quit' 结束讨论[/dim]\n")

    # 开始对话
    llm_client.start_suggestion_conversation(suggestion)

    # 显示AI的初始建议说明
    console.print("[bold cyan]🤖 AI：[/bold cyan]")
    console.print("我刚才给出了这个建议。你觉得怎么样？有什么地方需要调整吗？")
    console.print("比如，如果我猜测的项目名称或时间不准确，请告诉我正确的信息。\n")

    conversation_count = 0
    max_conversations = 10  # 限制对话轮数

    while conversation_count < max_conversations:
        # 获取用户输入
        user_input = click.prompt(
            f"[{conversation_count + 1}] 你", default="", show_default=False
        ).strip()

        if not user_input:
            continue

        # 检查是否要退出
        if user_input.lower() in ["exit", "quit", "退出", "结束"]:
            if Confirm.ask("确定要结束讨论吗？"):
                console.print("[yellow]讨论已结束[/yellow]")
                return None
            else:
                continue

        # 获取AI回复
        console.print("[dim]AI正在思考...[/dim]")
        result = llm_client.continue_suggestion_conversation(user_input)

        if not result["success"]:
            console.print(f"[red]对话出错: {result['error']}[/red]")
            continue

        # 显示AI回复
        console.print(f"\n[bold cyan]🤖 AI：[/bold cyan]")
        console.print(result["ai_response"])

        # 检查建议是否有更新
        updated_suggestion = result.get("updated_suggestion")
        if updated_suggestion and updated_suggestion != suggestion:
            console.print("\n[yellow]💡 建议已根据你的反馈进行调整[/yellow]")
            console.print("[dim]更新后的建议：[/dim]\n")
            _display_optimization_suggestion(updated_suggestion)
            suggestion = updated_suggestion  # 更新当前建议

        conversation_count += 1
        console.print()  # 空行分隔

        # 询问是否满意当前建议
        if conversation_count >= 3:  # 至少讨论3轮后询问
            if Confirm.ask("你对当前的建议满意吗？"):
                break

    if conversation_count >= max_conversations:
        console.print("[yellow]⚠️  已达到最大对话轮数限制[/yellow]")

    # 获取最终建议
    final_suggestion = llm_client.get_final_suggestion()

    if final_suggestion:
        console.print("\n[bold green]✅ 讨论完成！[/bold green]")
        return final_suggestion
    else:
        console.print("\n[yellow]讨论已取消[/yellow]")
        return None


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
