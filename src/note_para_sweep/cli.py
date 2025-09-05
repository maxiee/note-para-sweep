"""命令行界面"""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .config import Config
from .scanner import DirectoryScanner


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

    if dry_run:
        console.print("[yellow]试运行模式：这里将展示 AI 分析结果和建议操作[/yellow]")
    else:
        console.print("[red]此功能还在开发中...[/red]")


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

    if dry_run:
        console.print("[yellow]试运行模式：这里将展示结构优化建议[/yellow]")
    else:
        console.print("[red]此功能还在开发中...[/red]")


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
