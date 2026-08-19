"""Paper parsing module supporting PDF and LaTeX inputs."""

from .paper_model import ParsedPaper, PaperFigure, PaperSection, PaperTable

def __getattr__(name: str):
    if name == "PDFParser":
        from .pdf_parser import PDFParser as _PDFParser

        return _PDFParser
    if name == "LaTeXParser":
        from .latex_parser import LaTeXParser as _LaTeXParser

        return _LaTeXParser
    if name == "ProjectZipParser":
        from .project_zip_parser import ProjectZipParser as _ProjectZipParser

        return _ProjectZipParser
    raise AttributeError(name)

__all__ = [
    "PDFParser",
    "LaTeXParser",
    "ProjectZipParser",
    "ParsedPaper",
    "PaperFigure",
    "PaperSection",
    "PaperTable",
]
