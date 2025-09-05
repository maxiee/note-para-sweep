"""Note PARA Sweep - AI 驱动的 Obsidian 笔记 PARA 分类器"""

__version__ = "0.1.0"
__author__ = "Maxiee"
__email__ = "maxieewong@gmail.com"

from .config import Config
from .scanner import DirectoryScanner, DirectoryInfo

__all__ = ["Config", "DirectoryScanner", "DirectoryInfo"]
