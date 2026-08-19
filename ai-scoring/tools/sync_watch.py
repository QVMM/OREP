#!/usr/bin/env python3
"""
OpenPencil ↔ V9 实时同步监听工具

用法:
    python sync_watch.py --op-dir ./designs --v9-dir ./app/services/ppt/components
"""
import argparse
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from op_to_v9 import OpToV9Converter
from v9_to_op import V9ToOpConverter


class OpFileHandler(FileSystemEventHandler):
    """监听 .op 文件变化"""

    def __init__(self, v9_output_dir: Path, theme: str = "deep-blue-tech"):
        self.v9_output_dir = v9_output_dir
        self.theme = theme
        self.file_hashes: Dict[str, str] = {}

    def _get_file_hash(self, filepath: Path) -> str:
        """计算文件哈希"""
        return hashlib.md5(filepath.read_bytes()).hexdigest()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".op"):
            filepath = Path(event.src_path)

            # 检查文件是否真的变化了
            current_hash = self._get_file_hash(filepath)
            if self.file_hashes.get(str(filepath)) == current_hash:
                return

            self.file_hashes[str(filepath)] = current_hash

            print(f"\n检测到 .op 文件变化: {filepath.name}")
            self._convert_to_v9(filepath)

    def _convert_to_v9(self, op_path: Path):
        """将 .op 文件转换为 V9 组件"""
        try:
            with open(op_path, "r", encoding="utf-8") as f:
                op_data = json.load(f)

            converter = OpToV9Converter(op_data)

            # 生成组件名称
            component_id = op_path.stem.lower().replace(" ", "_")
            output_path = self.v9_output_dir / f"{component_id}.py"

            # 生成组件代码
            component_code = converter.generate_component_class(component_id)

            # 写入文件
            output_path.write_text(component_code, encoding="utf-8")
            print(f"✓ V9 组件已更新: {output_path}")

        except Exception as e:
            print(f"✗ 转换失败: {e}")


class V9FileHandler(FileSystemEventHandler):
    """监听 V9 组件文件变化"""

    def __init__(self, op_output_dir: Path, theme: str = "deep-blue-tech"):
        self.op_output_dir = op_output_dir
        self.theme = theme
        self.file_hashes: Dict[str, str] = {}

    def _get_file_hash(self, filepath: Path) -> str:
        """计算文件哈希"""
        return hashlib.md5(filepath.read_bytes()).hexdigest()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            filepath = Path(event.src_path)

            # 跳过 __init__.py 和 base.py
            if filepath.name in ["__init__.py", "base.py"]:
                return

            # 检查文件是否真的变化了
            current_hash = self._get_file_hash(filepath)
            if self.file_hashes.get(str(filepath)) == current_hash:
                return

            self.file_hashes[str(filepath)] = current_hash

            print(f"\n检测到 V9 组件变化: {filepath.name}")
            self._convert_to_op(filepath)

    def _convert_to_op(self, v9_path: Path):
        """将 V9 组件转换为 .op 文件（仅用于预览）"""
        try:
            component_name = v9_path.stem
            converter = V9ToOpConverter(self.theme)

            # 生成 .op 数据
            op_data = converter.convert_component(component_name)

            # 输出路径
            output_path = self.op_output_dir / f"{component_name}.op"

            # 写入文件
            json_str = json.dumps(op_data, indent=2, ensure_ascii=False)
            output_path.write_text(json_str, encoding="utf-8")
            print(f"✓ 预览 .op 文件已更新: {output_path}")

        except Exception as e:
            print(f"✗ 转换失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="OpenPencil ↔ V9 实时同步监听工具"
    )
    parser.add_argument("--op-dir", default="./designs",
                       help=".op 文件目录")
    parser.add_argument("--v9-dir", default="./app/services/ppt/components",
                       help="V9 组件目录")
    parser.add_argument("--preview-dir", default="./preview",
                       help="预览 .op 文件输出目录")
    parser.add_argument("--theme", default="deep-blue-tech",
                       choices=["deep-blue-tech", "black-gold", "fresh-green", "sky-blue-tech"],
                       help="默认主题")
    parser.add_argument("--direction", choices=["op-to-v9", "v9-to-op", "both"],
                       default="both", help="同步方向")

    args = parser.parse_args()

    op_dir = Path(args.op_dir)
    v9_dir = Path(args.v9_dir)
    preview_dir = Path(args.preview_dir)

    # 确保目录存在
    op_dir.mkdir(parents=True, exist_ok=True)
    v9_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OpenPencil ↔ V9 实时同步监听")
    print("=" * 60)
    print(f"监听方向: {args.direction}")
    print(f"主题: {args.theme}")
    print(f".op 目录: {op_dir.absolute()}")
    print(f"V9 目录: {v9_dir.absolute()}")
    print(f"预览目录: {preview_dir.absolute()}")
    print("=" * 60)
    print("按 Ctrl+C 停止监听...\n")

    observer = Observer()

    if args.direction in ["op-to-v9", "both"]:
        op_handler = OpFileHandler(v9_dir, args.theme)
        observer.schedule(op_handler, str(op_dir), recursive=False)
        print(f"✓ 监听 .op 文件变化 → 生成 V9 组件")

    if args.direction in ["v9-to-op", "both"]:
        v9_handler = V9FileHandler(preview_dir, args.theme)
        observer.schedule(v9_handler, str(v9_dir), recursive=False)
        print(f"✓ 监听 V9 组件变化 → 生成预览 .op")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止监听...")
        observer.stop()

    observer.join()
    print("同步监听已结束")


if __name__ == "__main__":
    main()
