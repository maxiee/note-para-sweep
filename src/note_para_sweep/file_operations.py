"""文件操作模块 - 安全的文件和目录操作"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class FileOperationLogger:
    """文件操作日志记录器"""

    def __init__(self, log_file: Path = None):
        if log_file is None:
            log_file = Path("note_para_sweep.log")

        self.log_file = log_file
        self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filemode="a",
        )
        self.logger = logging.getLogger(__name__)

    def log_operation(
        self,
        operation_type: str,
        source: Path,
        target: Path = None,
        success: bool = True,
        error: str = None,
    ):
        """记录文件操作"""
        timestamp = datetime.now().isoformat()

        if success:
            if target:
                message = f"{operation_type}: {source} -> {target}"
            else:
                message = f"{operation_type}: {source}"
            self.logger.info(message)
        else:
            message = f"FAILED {operation_type}: {source}"
            if target:
                message += f" -> {target}"
            if error:
                message += f" (Error: {error})"
            self.logger.error(message)


class FileOperator:
    """安全的文件操作执行器"""

    def __init__(self, dry_run: bool = True, log_file: Path = None):
        self.dry_run = dry_run
        self.logger = FileOperationLogger(log_file)
        self.operations_executed = []

    def move_file(self, source: Path, target: Path) -> Dict[str, Any]:
        """移动文件到目标位置

        Args:
            source: 源文件路径
            target: 目标文件路径

        Returns:
            操作结果字典
        """
        result = {
            "operation": "move_file",
            "source": str(source),
            "target": str(target),
            "success": False,
            "dry_run": self.dry_run,
            "error": None,
        }

        try:
            # 验证源文件存在
            if not source.exists():
                raise FileNotFoundError(f"源文件不存在: {source}")

            # 检查目标文件是否已存在
            if target.exists():
                raise FileExistsError(f"目标文件已存在: {target}")

            # 确保目标目录存在
            target.parent.mkdir(parents=True, exist_ok=True)

            if not self.dry_run:
                # 执行实际移动操作
                shutil.move(str(source), str(target))
                result["success"] = True
                self.logger.log_operation("MOVE", source, target, success=True)
            else:
                # 试运行模式
                result["success"] = True
                result["message"] = "试运行模式：未执行实际操作"

            self.operations_executed.append(result)
            return result

        except Exception as e:
            result["error"] = str(e)
            self.logger.log_operation(
                "MOVE", source, target, success=False, error=str(e)
            )
            return result

    def create_directory(self, directory_path: Path) -> Dict[str, Any]:
        """创建目录

        Args:
            directory_path: 要创建的目录路径

        Returns:
            操作结果字典
        """
        result = {
            "operation": "create_directory",
            "path": str(directory_path),
            "success": False,
            "dry_run": self.dry_run,
            "error": None,
        }

        try:
            if directory_path.exists():
                result["success"] = True
                result["message"] = "目录已存在"
                return result

            if not self.dry_run:
                directory_path.mkdir(parents=True, exist_ok=True)
                result["success"] = True
                self.logger.log_operation("CREATE_DIR", directory_path, success=True)
            else:
                result["success"] = True
                result["message"] = "试运行模式：未执行实际操作"

            self.operations_executed.append(result)
            return result

        except Exception as e:
            result["error"] = str(e)
            self.logger.log_operation(
                "CREATE_DIR", directory_path, success=False, error=str(e)
            )
            return result

    def execute_classification(
        self, source_file: Path, classification: Dict[str, Any], vault_path: Path
    ) -> Dict[str, Any]:
        """执行分类操作

        Args:
            source_file: 源笔记文件
            classification: AI分类结果
            vault_path: vault根目录

        Returns:
            执行结果
        """
        result = {
            "success": False,
            "operations": [],
            "error": None,
            "dry_run": self.dry_run,
        }

        try:
            # 解析目标路径
            target_path = vault_path / classification.get("target_path", "")

            # 如果需要创建目录
            create_dirs = classification.get("create_directories", [])
            for dir_path in create_dirs:
                full_dir_path = vault_path / dir_path
                dir_result = self.create_directory(full_dir_path)
                result["operations"].append(dir_result)

                if not dir_result["success"]:
                    result["error"] = f"创建目录失败: {dir_result['error']}"
                    return result

            # 移动文件
            move_result = self.move_file(source_file, target_path)
            result["operations"].append(move_result)

            if move_result["success"]:
                result["success"] = True
                result["final_path"] = str(target_path)
            else:
                result["error"] = f"移动文件失败: {move_result['error']}"

            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    def get_operations_summary(self) -> Dict[str, Any]:
        """获取操作摘要"""
        return {
            "total_operations": len(self.operations_executed),
            "successful_operations": len(
                [op for op in self.operations_executed if op["success"]]
            ),
            "failed_operations": len(
                [op for op in self.operations_executed if not op["success"]]
            ),
            "dry_run": self.dry_run,
            "operations": self.operations_executed,
        }
