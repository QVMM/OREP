"""Parser for vocational roadshow project material ZIP packages.

Unlike LaTeX ZIP archives, these packages are usually folders of Markdown,
CSV, logs, code snippets, screenshots, and SVG source assets.  The parser
normalizes them into the same ``ParsedPaper`` model consumed by the existing
PPT pipeline so the roadshow agent can reuse the proven downstream chain.
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.runtime import aoffload
from backend.orchestrator.roadshow_asset_registry import (
    RoadshowAssetRecord,
    asset_caption_from_rel,
    infer_roadshow_asset_type,
    normalize_roadshow_asset_rel,
    write_asset_registry,
)

from .base import PaperParser
from .paper_model import PaperFigure, PaperSection, ParsedPaper

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".md", ".txt"}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".java", ".sql", ".json", ".yaml", ".yml"}
LOG_EXTENSIONS = {".log"}
CSV_EXTENSIONS = {".csv"}
PNG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SVG_EXTENSIONS = {".svg"}

MAX_TEXT_CHARS = 12000
MAX_CODE_CHARS = 4200
MAX_LOG_CHARS = 2600
MAX_CSV_ROWS = 30


@dataclass(frozen=True)
class _ProjectZipFile:
    path: Path
    rel: str


def _probe_image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as img:
            return int(img.width), int(img.height)
    except Exception:
        return 0, 0


class ProjectZipParser(PaperParser):
    """Parse project-material ZIPs into a ``ParsedPaper`` representation."""

    last_parse_info: dict[str, object] = {}

    async def parse(self, file_path: Path, output_dir: Path) -> ParsedPaper:
        return await aoffload(self._parse_sync, file_path, output_dir)

    def parse_directory_sync(self, directory: Path, output_dir: Path) -> ParsedPaper:
        return self._parse_directory(directory, output_dir)

    def _parse_sync(self, file_path: Path, output_dir: Path) -> ParsedPaper:
        output_dir.mkdir(parents=True, exist_ok=True)
        if file_path.is_dir():
            return self._parse_directory(file_path, output_dir)
        extract_dir = output_dir / "project_zip_src"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as zf:
            self._extract_zip_safely(zf, extract_dir)
        return self._parse_directory(extract_dir, output_dir)

    def _parse_directory(self, root: Path, output_dir: Path) -> ParsedPaper:
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        files = self._list_files(root)
        manifest = self._load_manifest(files)
        title = self._title_from_manifest(manifest) or self._title_from_readme(files) or root.name

        sections: list[PaperSection] = []
        if manifest:
            sections.append(self._manifest_section(manifest))

        markdown_files = self._files_by_extension(files, TEXT_EXTENSIONS)
        for item in markdown_files:
            content = self._read_text(item.path)
            if not content:
                continue
            sections.append(
                PaperSection(
                    title=self._section_title_from_path(item.rel),
                    level=1,
                    content=self._limit_text(content, MAX_TEXT_CHARS),
                )
            )

        csv_files = self._files_by_extension(files, CSV_EXTENSIONS)
        if csv_files:
            sections.append(self._csv_section(csv_files))

        log_files = self._files_by_extension(files, LOG_EXTENSIONS)
        if log_files:
            sections.append(self._log_section(log_files))

        code_files = [
            item
            for item in self._files_by_extension(files, CODE_EXTENSIONS)
            if Path(item.rel).name.lower() != "manifest.json"
        ]
        if code_files:
            sections.append(self._code_section(code_files))

        png_files = self._files_by_extension(files, PNG_EXTENSIONS)
        svg_files = self._files_by_extension(files, SVG_EXTENSIONS)
        image_section = self._image_section(png_files, svg_files, images_dir, output_dir)
        if image_section:
            sections.append(image_section)

        abstract = self._abstract_from_manifest(manifest, files)
        ProjectZipParser.last_parse_info = {
            "path": "project_zip",
            "source_root": str(root),
            "title": title,
            "markdown_files": len(markdown_files),
            "csv_files": len(csv_files),
            "log_files": len(log_files),
            "code_files": len(code_files),
            "png_images": len(png_files),
            "svg_sources": len(svg_files),
        }
        self._write_project_manifest(output_dir, ProjectZipParser.last_parse_info)
        return ParsedPaper(
            title=title,
            authors=[],
            abstract=abstract,
            sections=sections,
            references=[],
            source_type="latex",
            figures_dir=images_dir,
        )

    def _list_files(self, root: Path) -> list[_ProjectZipFile]:
        records: list[_ProjectZipFile] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if "__MACOSX/" in rel or Path(rel).name.startswith("."):
                continue
            records.append(_ProjectZipFile(path=path, rel=rel))
        return records

    def _files_by_extension(
        self,
        files: list[_ProjectZipFile],
        extensions: set[str],
    ) -> list[_ProjectZipFile]:
        return [item for item in files if item.path.suffix.lower() in extensions]

    def _load_manifest(self, files: list[_ProjectZipFile]) -> dict[str, Any]:
        for item in files:
            if Path(item.rel).name.lower() != "manifest.json":
                continue
            try:
                data = json.loads(self._read_text(item.path))
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}
        return {}

    def _title_from_manifest(self, manifest: dict[str, Any]) -> str:
        project = manifest.get("project")
        if isinstance(project, dict):
            name = str(project.get("name") or "").strip()
            if name:
                return name
        for key in ("title", "name", "project_name"):
            value = str(manifest.get(key) or "").strip()
            if value:
                return value
        return ""

    def _title_from_readme(self, files: list[_ProjectZipFile]) -> str:
        for item in files:
            if Path(item.rel).name.lower() != "readme.md":
                continue
            for line in self._read_text(item.path).splitlines():
                clean = line.strip()
                if clean.startswith("#"):
                    return clean.lstrip("#").strip()
        return ""

    def _abstract_from_manifest(self, manifest: dict[str, Any], files: list[_ProjectZipFile]) -> str:
        categories = manifest.get("categories") if isinstance(manifest, dict) else None
        parts = ["项目资料包，包含说明文档、数据表、日志、代码和截图素材。"]
        if isinstance(categories, list) and categories:
            parts.append("资料类别：" + "、".join(str(item) for item in categories[:12]))
        disclaimer = manifest.get("disclaimer") if isinstance(manifest, dict) else None
        if disclaimer:
            parts.append("资料声明：" + str(disclaimer))
        parts.append(f"文件数量：{len(files)}")
        return "\n".join(parts)

    def _manifest_section(self, manifest: dict[str, Any]) -> PaperSection:
        lines = ["# Manifest 摘要", ""]
        project = manifest.get("project")
        if isinstance(project, dict):
            for key, value in project.items():
                lines.append(f"- {key}: {value}")
        categories = manifest.get("categories")
        if isinstance(categories, list):
            lines.append("")
            lines.append("## 资料类别")
            for item in categories:
                lines.append(f"- {item}")
        disclaimer = manifest.get("disclaimer")
        if disclaimer:
            lines.extend(["", "## 声明", str(disclaimer)])
        return PaperSection(title="Manifest", level=1, content="\n".join(lines))

    def _csv_section(self, files: list[_ProjectZipFile]) -> PaperSection:
        parts = ["# Data Tables", ""]
        for item in files:
            table = self._csv_to_markdown(item.path)
            if not table:
                continue
            parts.append(f"## {item.rel}")
            parts.append(table)
            parts.append("")
        return PaperSection(title="Data Tables", level=1, content="\n".join(parts))

    def _log_section(self, files: list[_ProjectZipFile]) -> PaperSection:
        parts = ["# Logs and Runtime Evidence", ""]
        for item in files:
            content = self._limit_text(self._read_text(item.path), MAX_LOG_CHARS)
            parts.append(f"## {item.rel}")
            parts.append("```log")
            parts.append(content)
            parts.append("```")
            parts.append("")
        return PaperSection(title="Logs and Runtime Evidence", level=1, content="\n".join(parts))

    def _code_section(self, files: list[_ProjectZipFile]) -> PaperSection:
        parts = ["# Code and Interface Evidence", ""]
        for item in files:
            content = self._limit_text(self._read_text(item.path), MAX_CODE_CHARS)
            lang = self._code_fence_language(item.path.suffix.lower())
            parts.append(f"## {item.rel}")
            parts.append(f"```{lang}")
            parts.append(content)
            parts.append("```")
            parts.append("")
        return PaperSection(title="Code and Interface Evidence", level=1, content="\n".join(parts))

    def _image_section(
        self,
        png_files: list[_ProjectZipFile],
        svg_files: list[_ProjectZipFile],
        images_dir: Path,
        output_dir: Path,
    ) -> PaperSection | None:
        if not png_files and not svg_files:
            return None
        figures: list[PaperFigure] = []
        registry: list[RoadshowAssetRecord] = []
        lines = ["# Image and SVG Assets", ""]
        if png_files:
            lines.append("## PNG Evidence Images")
            asset_dir = images_dir / "assets"
            usable_png_files = [
                item
                for item in png_files
                if "素材包图片预览" not in item.rel and "上传清单" not in item.rel
            ]
            for index, item in enumerate(usable_png_files, start=1):
                suffix = item.path.suffix.lower() if item.path.suffix.lower() in PNG_EXTENSIONS else ".png"
                asset_id = f"asset_{index:03d}"
                dest = self._copy_asset(item.path, asset_dir / f"{asset_id}{suffix}")
                w, h = _probe_image_size(dest)
                clean_rel = normalize_roadshow_asset_rel(item.rel)
                asset_type = infer_roadshow_asset_type(clean_rel)
                caption = self._caption_from_asset_path(clean_rel)
                rel_path = dest.relative_to(output_dir).as_posix()
                href = f"../sources/{rel_path}"
                registry.append(
                    RoadshowAssetRecord(
                        asset_id=asset_id,
                        asset_type=asset_type,
                        original_rel=clean_rel,
                        filename=dest.name,
                        path=rel_path,
                        href=href,
                        caption=caption,
                        natural_width=w,
                        natural_height=h,
                        token=f"[[ASSET:{asset_id}]]",
                    )
                )
                figures.append(
                    PaperFigure(
                        path=dest,
                        caption=caption,
                        available=True,
                        natural_width=w,
                        natural_height=h,
                        extraction_method="project_zip_png",
                        review_flags=[],
                    )
                )
                lines.append(
                    f"- [[ASSET:{asset_id}]] [[FIG:{dest.stem}]] {caption}；"
                    f"asset_type={asset_type}；source={clean_rel}；href={href}"
                )
            lines.append("")
            write_asset_registry(output_dir, registry)
        if svg_files:
            svg_dir = images_dir / "svg"
            svg_dir.mkdir(exist_ok=True)
            lines.append("## Editable SVG Sources")
            for item in svg_files:
                dest = self._copy_asset(item.path, svg_dir / item.path.name)
                lines.append(f"- {item.rel} -> {dest.name}；可作为页面重绘、结构理解或备用素材，不直接当作正式证据。")
        return PaperSection(
            title="Image and SVG Assets",
            level=1,
            content="\n".join(lines),
            figures=figures,
        )

    def _copy_asset(self, src: Path, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return dest

    def _csv_to_markdown(self, path: Path) -> str:
        text = self._read_text(path)
        if not text.strip():
            return ""
        rows = list(csv.reader(text.splitlines()))
        if not rows:
            return ""
        header = [cell.strip() for cell in rows[0]]
        body = rows[1 : MAX_CSV_ROWS + 1]
        if not header:
            return ""
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in body:
            padded = (row + [""] * len(header))[: len(header)]
            lines.append("| " + " | ".join(cell.strip().replace("|", "/") for cell in padded) + " |")
        if len(rows) - 1 > MAX_CSV_ROWS:
            lines.append(f"\n> CSV truncated: showing {MAX_CSV_ROWS} of {len(rows) - 1} rows.")
        return "\n".join(lines)

    def _read_text(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return path.read_text(encoding=encoding, errors="strict")
            except UnicodeDecodeError:
                continue
            except OSError:
                return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def _limit_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n\n[内容过长，已截断供 PPT 生成使用]"

    def _section_title_from_path(self, rel: str) -> str:
        name = Path(rel).stem.replace("_", " ").replace("-", " ").strip()
        return name or rel

    def _caption_from_asset_path(self, rel: str) -> str:
        return asset_caption_from_rel(rel)

    def _code_fence_language(self, suffix: str) -> str:
        return {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".sql": "sql",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }.get(suffix, "text")

    def _extract_zip_safely(self, archive: zipfile.ZipFile, extract_dir: Path) -> None:
        for info in archive.infolist():
            if info.is_dir():
                continue
            target = self._safe_extract_target(extract_dir, info.filename)
            if target is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    def _safe_extract_target(self, extract_dir: Path, raw_name: str) -> Path | None:
        raw_name = self._normalize_zip_member_name(raw_name)
        try:
            target = (extract_dir / raw_name).resolve()
        except OSError:
            return None
        try:
            target.relative_to(extract_dir.resolve())
        except ValueError:
            logger.warning("Skipping unsafe zip member: %s", raw_name)
            return None
        return target

    def _normalize_zip_member_name(self, raw_name: str) -> str:
        """Recover Chinese filenames when ZIP entries were decoded as CP437."""
        if not raw_name:
            return raw_name
        try:
            raw_bytes = raw_name.encode("cp437")
        except UnicodeEncodeError:
            raw_bytes = b""
        candidates = [raw_name]
        if raw_bytes:
            for encoding in ("utf-8", "gb18030"):
                try:
                    candidates.append(raw_bytes.decode(encoding))
                except UnicodeDecodeError:
                    continue
        for source_encoding in ("gb18030", "latin1", "cp1252"):
            try:
                candidates.append(raw_name.encode(source_encoding).decode("utf-8"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return min(candidates, key=self._mojibake_score)

    def _mojibake_score(self, value: str) -> int:
        mojibake_chars = (
            "µ╕⌐σ╖▒ÅτÄΣΦäöΘ┐┤₧"
            "鏀跨瓥瀵煎悜鎽樿鐜鐩戞祴澶у睆璁惧鑱斿姩鎺у埗"
            "鍛婅宸ュ崟闂幆绉诲姩绔伐浣滃彴鏁版嵁鍒嗘瀽涓績"
            "浼犳劅鑺傜偣杩戞櫙绠辨帴绾垮浘"
        )
        score = sum(3 for ch in value if ch in mojibake_chars)
        score += value.count("�") * 5
        score += sum(5 for ch in value if "\ue000" <= ch <= "\uf8ff")
        score -= sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
        return score

    def _write_project_manifest(self, output_dir: Path, info: dict[str, object]) -> None:
        try:
            (output_dir / "project_zip_parse_info.json").write_text(
                json.dumps(info, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
