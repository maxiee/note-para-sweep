"""命令行界面"""

import click
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


@click.group()
@click.option("--config", "-c", default="config.yaml", help="配置文件路径")
@click.option("--dry-run", is_flag=True, help="试运行模式，不执行实际操作")
@click.pass_context
def cli(ctx, config, dry_run):
    """Note PARA Sweep - AI 驱动的 Obsidian 笔记 PARA 分类器"""
    ctx.ensure_object(dict)

    try:
        ctx.obj["config"] = Config(config)
        ctx.obj["dry_run"] = dry_run or ctx.obj["config"].dry_run_by_default

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

    except Exception as e:
        console.print(f"[red]配置错误: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.pass_context
def scan(ctx):
    """扫描 PARA 目录结构"""
    config = ctx.obj["config"]

    console.print("[blue]正在扫描 PARA 目录结构...[/blue]")

    scanner = DirectoryScanner(config.vault_path, config.para_paths)
    scan_result = scanner.scan()

    # 生成并显示结构摘要
    summary = scanner.generate_structure_summary(scan_result)
    console.print(Panel(summary, title="目录结构", expand=True))

    # 统计信息
    total_notes = sum(dir_info.note_count for dir_info in scan_result.values())
    console.print(f"\n[green]✅ 扫描完成！共发现 {total_notes} 篇笔记[/green]")


@cli.command()
@click.argument("note_path", type=click.Path(exists=True))
@click.pass_context
def classify(ctx, note_path):
    """分类单个笔记文件"""
    config = ctx.obj["config"]
    dry_run = ctx.obj["dry_run"]

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
        llm_client = LLMClient(config)

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

    console.print("[blue]正在分析整体 PARA 结构...[/blue]")

    if not Confirm.ask("这将分析你的整个知识库结构，继续吗？"):
        console.print("操作已取消")
        return

    try:
        # 扫描目录结构
        scanner = DirectoryScanner(config.vault_path, config.para_paths)
        scan_result = scanner.scan()
        para_structure = scanner.generate_structure_summary(scan_result)

        # 生成笔记概览
        notes_overview = _generate_notes_overview(scan_result)

        # 初始化 LLM 客户端
        llm_client = LLMClient(config)

        console.print("[yellow]正在使用 AI 分析结构优化机会...[/yellow]")
        console.print(
            f"[dim]使用提供商: {config.llm_provider} | 模型: {config.llm_model}[/dim]"
        )

        # 调用结构优化分析
        result = llm_client.optimize_structure(para_structure, notes_overview)

        if not result["success"]:
            console.print(f"[red]结构分析失败: {result['error']}[/red]")
            return

        optimization = result["optimization"]

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

        # 逐条处理建议
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"\n[bold cyan]建议 {i}/{len(suggestions)}:[/bold cyan]")
            _display_optimization_suggestion(suggestion)

            if dry_run:
                console.print("[yellow]试运行模式：显示建议但不执行操作[/yellow]")
                continue

            # 用户选择
            choice = click.prompt(
                "选择操作",
                type=click.Choice(["y", "n", "s", "q"]),
                default="n",
                show_choices=True,
                help="y=执行, n=跳过, s=全部跳过, q=退出",
            )

            if choice == "q":
                console.print("退出优化模式")
                break
            elif choice == "s":
                console.print("跳过剩余所有建议")
                break
            elif choice == "y":
                # 这里应该执行具体的优化操作
                console.print("[yellow]优化操作执行功能正在开发中...[/yellow]")
            else:
                console.print("跳过此建议")

    except Exception as e:
        console.print(f"[red]结构优化失败: {e}[/red]")


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


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
