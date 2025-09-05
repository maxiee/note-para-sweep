"""文件操作模块 - 安全的文件和目录操作"""

import shutil
import logging
import json
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
        self.suggestion_history = []  # 建议历史记录

    def _is_safe_path(self, path: Path) -> bool:
        """检查路径安全性，防止路径遍历攻击

        Args:
            path: 要检查的路径

        Returns:
            路径是否安全
        """
        try:
            # 解析路径并检查是否包含危险模式
            resolved_path = path.resolve()
            path_str = str(resolved_path)

            # 检查危险模式
            dangerous_patterns = [
                "../",
                "..\\",
                "~",
                "/etc",
                "/var",
                "/usr",
                "/bin",
                "/sbin",
            ]
            for pattern in dangerous_patterns:
                if pattern in path_str:
                    return False

            # 确保路径不为空且是合理的
            if len(path_str.strip()) == 0 or path_str.strip() in ["/", "\\"]:
                return False

            return True
        except Exception:
            return False

    def record_suggestion_history(
        self,
        original_suggestion: Dict[str, Any],
        final_suggestion: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        user_decision: str = "pending",
    ):
        """记录建议的讨论和修改历史

        Args:
            original_suggestion: 原始建议
            final_suggestion: 最终建议（如果有修改）
            conversation_history: 对话历史
            user_decision: 用户决定 (accepted/rejected/pending)
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "original_suggestion": original_suggestion,
            "final_suggestion": final_suggestion or original_suggestion,
            "conversation_history": conversation_history or [],
            "user_decision": user_decision,
            "suggestion_id": len(self.suggestion_history) + 1,
        }

        self.suggestion_history.append(record)

        # 可选：保存到文件
        self._save_suggestion_history()

    def _save_suggestion_history(self):
        """保存建议历史到文件"""
        history_file = Path("suggestion_history.json")
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.suggestion_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.log_operation(
                "SAVE_HISTORY", history_file, success=False, error=str(e)
            )

    def get_suggestion_history(self) -> List[Dict[str, Any]]:
        """获取建议历史记录"""
        return self.suggestion_history.copy()

    def load_suggestion_history(self):
        """从文件加载建议历史"""
        history_file = Path("suggestion_history.json")
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    self.suggestion_history = json.load(f)
            except Exception as e:
                self.logger.log_operation(
                    "LOAD_HISTORY", history_file, success=False, error=str(e)
                )

    def move_file(self, source: Path, target: Path) -> Dict[str, Any]:
        """移动文件到目标位置（带原子性保障）

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
            # 输入验证
            if not isinstance(source, Path):
                source = Path(source)
            if not isinstance(target, Path):
                target = Path(target)

            # 检查路径安全性
            if not self._is_safe_path(source) or not self._is_safe_path(target):
                raise ValueError("不安全的文件路径")

            # 验证源文件存在
            if not source.exists():
                raise FileNotFoundError(f"源文件不存在: {source}")

            if not source.is_file():
                raise ValueError(f"源路径不是文件: {source}")

            # 检查目标文件是否已存在
            if target.exists():
                raise FileExistsError(f"目标文件已存在: {target}")

            # 确保目标目录存在
            target.parent.mkdir(parents=True, exist_ok=True)

            if not self.dry_run:
                # 原子性操作：先复制，再删除
                backup_created = False
                try:
                    # 复制文件
                    shutil.copy2(str(source), str(target))
                    backup_created = True

                    # 验证复制成功
                    if (
                        not target.exists()
                        or target.stat().st_size != source.stat().st_size
                    ):
                        raise Exception("文件复制验证失败")

                    # 删除原文件
                    source.unlink()
                    result["success"] = True
                    self.logger.log_operation("MOVE", source, target, success=True)

                except Exception as e:
                    # 回滚操作
                    if backup_created and target.exists():
                        try:
                            target.unlink()
                        except:
                            pass
                    raise e
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
