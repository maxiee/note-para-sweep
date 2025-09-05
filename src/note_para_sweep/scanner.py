"""目录结构扫描模块"""

import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DirectoryInfo:
    """目录信息"""

    path: Path
    name: str
    type: str  # 'projects', 'areas', 'resources', 'archives', 'inbox'
    subdirs: List["DirectoryInfo"]
    note_count: int


class DirectoryScanner:
    """PARA 目录结构扫描器"""

    def __init__(self, vault_path: Path, para_paths: Dict[str, str]):
        self.vault_path = vault_path
        self.para_paths = para_paths

    def scan(self, max_depth: int = 3) -> Dict[str, DirectoryInfo]:
        """扫描 PARA 目录结构

        Args:
            max_depth: 最大扫描深度

        Returns:
            包含各个 PARA 类别的目录信息字典
        """
        result = {}

        for para_type, dir_name in self.para_paths.items():
            dir_path = self.vault_path / dir_name
            if dir_path.exists():
                result[para_type] = self._scan_directory(dir_path, para_type, max_depth)

        return result

    def _scan_directory(
        self, path: Path, para_type: str, max_depth: int
    ) -> DirectoryInfo:
        """递归扫描单个目录"""
        subdirs = []
        note_count = 0

        if max_depth > 0:
            try:
                for item in path.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        subdir_info = self._scan_directory(
                            item, para_type, max_depth - 1
                        )
                        subdirs.append(subdir_info)
                    elif item.is_file() and item.suffix.lower() == ".md":
                        note_count += 1
            except PermissionError:
                # 如果没有权限访问某个目录，跳过
                pass

        return DirectoryInfo(
            path=path,
            name=path.name,
            type=para_type,
            subdirs=subdirs,
            note_count=note_count,
        )

    def generate_structure_summary(self, scan_result: Dict[str, DirectoryInfo]) -> str:
        """生成目录结构摘要文本，用于 AI 分析"""
        lines = ["# PARA 目录结构摘要\n"]

        for para_type, dir_info in scan_result.items():
            lines.append(f"## {para_type.upper()}: {dir_info.name}")
            lines.append(f"路径: {dir_info.path}")
            lines.append(f"笔记数量: {dir_info.note_count}")

            if dir_info.subdirs:
                lines.append("子目录:")
                self._add_subdirs_to_summary(dir_info.subdirs, lines, indent=1)

            lines.append("")

        return "\n".join(lines)

    def _add_subdirs_to_summary(
        self, subdirs: List[DirectoryInfo], lines: List[str], indent: int = 0
    ):
        """递归添加子目录信息到摘要"""
        prefix = "  " * indent + "- "

        for subdir in subdirs:
            lines.append(f"{prefix}{subdir.name} ({subdir.note_count} 篇笔记)")

            if subdir.subdirs:
                self._add_subdirs_to_summary(subdir.subdirs, lines, indent + 1)
