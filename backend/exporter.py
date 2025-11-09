import io
import logging
import os
import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from docx import Document
from fpdf import FPDF
from fpdf.errors import FPDFException
from markdown import markdown

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)


class Exporter:
    """内容导出工具，负责多格式转换与PDF字体管理。"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pdf_font_path = self._detect_font_path()
        self.reportlab_font_name = None
        self._reportlab_font_ready = False

    def _detect_font_path(self) -> Optional[str]:
        """尝试查找可用的Unicode字体，用于PDF导出。"""
        env_font = os.getenv("PDF_FONT_PATH")
        if env_font and Path(env_font).exists():
            logger.info(f"使用PDF字体: {env_font}")
            return env_font

        candidate_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/ArialUnicode.ttf",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "C:/Windows/Fonts/arialuni.ttf",
        ]

        for path in candidate_paths:
            if Path(path).exists():
                logger.info(f"检测到可用PDF字体: {path}")
                return path

        logger.warning("未能找到可用的Unicode字体，PDF导出可能不支持非ASCII字符")
        return None

    def markdown_to_plain(self, content: str) -> str:
        """将Markdown转换为纯文本，保留段落间空行。"""
        html = markdown(content or "")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n")
        lines = [line.rstrip() for line in text.splitlines()]
        plain = "\n".join(lines)
        plain = plain.strip()
        plain = re.sub(r"\n{2,}", "\n", plain)
        return plain

    def export_markdown(self, content: str) -> io.BytesIO:
        buffer = io.BytesIO()
        buffer.write((content or "").encode("utf-8"))
        buffer.seek(0)
        return buffer

    def export_text(self, content: str) -> io.BytesIO:
        plain = self.markdown_to_plain(content or "")
        buffer = io.BytesIO()
        buffer.write(plain.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def export_docx(self, content: str) -> io.BytesIO:
        plain = self.markdown_to_plain(content or "")
        document = Document()

        if not plain:
            document.add_paragraph("")
        else:
            for line in plain.splitlines():
                document.add_paragraph(line if line.strip() else "")

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)
        return buffer

    def _wrap_long_sequences(self, text: str, limit: int = 20) -> str:
        """插入空格拆分超长的无空白字符序列，避免PDF渲染报错。"""
        if not text:
            return text
        result = []
        run = 0
        for ch in text:
            if ch.isspace():
                run = 0
                result.append(ch)
            else:
                if run >= limit:
                    result.append("\n")
                    run = 0
                result.append(ch)
                run += 1
        return "".join(result)

    def _safe_pdf_line(self, line: str) -> str:
        """Sanitize a single line for PDF rendering."""
        sanitized = line.replace("\t", "    ")
        return self._wrap_long_sequences(sanitized, limit=80)

    def export_pdf(self, content: str) -> io.BytesIO:
        plain = self.markdown_to_plain(content or "")

        if REPORTLAB_AVAILABLE:
            try:
                return self._render_pdf_with_reportlab(plain)
            except Exception as exc:
                logger.error(f"ReportLab生成PDF失败，回退至FPDF: {exc}")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        if self.pdf_font_path and self.pdf_font_path.lower().endswith((".ttf", ".otf")):
            try:
                pdf.add_font("Custom", "", self.pdf_font_path, uni=True)
                pdf.set_font("Custom", size=12)
            except Exception as exc:
                logger.error(f"加载PDF字体失败({self.pdf_font_path}): {exc}")
                pdf.set_font("Helvetica", size=12)
        else:
            pdf.set_font("Helvetica", size=12)

        if not plain:
            self._write_pdf_line(pdf, "")
        else:
            for line in plain.splitlines():
                text = line if line.strip() else ""
                safe_text = self._safe_pdf_line(text)
                self._write_pdf_line(pdf, safe_text)

        pdf_bytes = pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin1")
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        return buffer

    def _render_pdf_with_reportlab(self, plain: str) -> io.BytesIO:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        font_name = self._ensure_reportlab_font()
        line_height = 14
        x_margin = 40
        top = A4[1] - 50
        bottom = 40

        text_obj = c.beginText(x_margin, top)
        text_obj.setFont(font_name, 12)

        lines = plain.splitlines() or [""]
        for line in lines:
            if text_obj.getY() <= bottom:
                c.drawText(text_obj)
                c.showPage()
                text_obj = c.beginText(x_margin, top)
                text_obj.setFont(font_name, 12)
            text_obj.textLine(line)

        c.drawText(text_obj)
        c.save()
        buffer.seek(0)
        return buffer

    def _ensure_reportlab_font(self) -> str:
        if not REPORTLAB_AVAILABLE:
            return "Helvetica"
        if self._reportlab_font_ready and self.reportlab_font_name:
            return self.reportlab_font_name

        font_path = self.pdf_font_path
        font_name = "CustomRL"
        try:
            if font_path and Path(font_path).exists():
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                self.reportlab_font_name = font_name
                self._reportlab_font_ready = True
                return font_name
        except Exception as exc:
            logger.error(f"注册ReportLab字体失败，使用默认字体: {exc}")

        self.reportlab_font_name = "Helvetica"
        self._reportlab_font_ready = True
        return "Helvetica"

    def _write_pdf_line(self, pdf: FPDF, text: str) -> None:
        """按字体宽度写入单行文本，自动换行。"""
        max_width = pdf.w - pdf.l_margin - pdf.r_margin
        segments = list(self._chunk_by_width(pdf, text, max_width)) or [""]
        for chunk in segments:
            pdf.cell(0, 8, chunk or " ", ln=1)

    def _chunk_by_width(self, pdf: FPDF, text: str, max_width: float):
        """根据真实字符宽度拆分文本块。"""
        buffer = ""
        for ch in text:
            if ch == "\n":
                if buffer:
                    yield buffer
                    buffer = ""
                yield ""
                continue
            tentative = buffer + ch
            if pdf.get_string_width(tentative) <= max_width:
                buffer = tentative
            else:
                if buffer:
                    yield buffer
                buffer = ch
        if buffer:
            yield buffer
