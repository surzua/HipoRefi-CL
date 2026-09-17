"""Módulo de lectura y extracción de texto de cartolas y documentos PDF hipotecarios."""

import io
from pathlib import Path
from typing import Union, BinaryIO, List
import pypdf


class PDFReaderError(Exception):
    """Error base para fallas en la lectura de documentos PDF."""
    pass


class PDFEncryptedError(PDFReaderError):
    """El documento PDF está protegido por contraseña."""
    pass


class PDFReader:
    """Extractor de texto para cartolas y comprobantes de dividendos hipotecarios."""

    @classmethod
    def extract_text(cls, source: Union[str, Path, bytes, BinaryIO]) -> str:
        """
        Extrae todo el texto legible de un archivo PDF o stream binario.

        Args:
            source: Ruta del archivo (str, Path), bytes en memoria o stream binario.

        Returns:
            Texto extraído y normalizado.
        """
        try:
            if isinstance(source, (str, Path)):
                file_path = Path(source)
                if not file_path.exists():
                    raise FileNotFoundError(f"No se encontró el archivo PDF: {file_path}")
                reader = pypdf.PdfReader(str(file_path))
            elif isinstance(source, bytes):
                reader = pypdf.PdfReader(io.BytesIO(source))
            else:
                reader = pypdf.PdfReader(source)

            if reader.is_encrypted:
                try:
                    # Intento con contraseña vacía (muy común en cartolas bancarias públicas)
                    decrypted = reader.decrypt("")
                    if not decrypted:
                        raise PDFEncryptedError("El archivo PDF está protegido con contraseña.")
                except Exception as exc:
                    raise PDFEncryptedError("El archivo PDF está protegido con contraseña.") from exc

            extracted_pages: List[str] = []
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text)

            full_text = "\n".join(extracted_pages)
            return cls._normalize_whitespace(full_text)

        except (PDFReaderError, FileNotFoundError):
            raise
        except Exception as e:
            raise PDFReaderError(f"Error inesperado procesando el PDF: {e}") from e

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Limpia caracteres de control y normaliza espacios en blanco."""
        cleaned_lines = []
        for line in text.splitlines():
            stripped = " ".join(line.split())
            if stripped:
                cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines)

    @staticmethod
    def create_synthetic_pdf(lines: List[str]) -> bytes:
        """
        Genera un PDF sintético válido en memoria a partir de una lista de líneas de texto.
        Útil para testing automatizado y fixtures sin dependencias binarias externas.
        """
        stream_content = "BT /F1 12 Tf 40 750 Td 16 TL\n"
        for line in lines:
            safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_content += f"({safe_line}) Tj T*\n"
        stream_content += "ET\n"
        stream_bytes = stream_content.encode("latin1", errors="replace")

        parts: List[bytes] = [b"%PDF-1.4\n"]
        offsets: List[int] = []

        def add_obj(obj_bytes: bytes) -> None:
            offsets.append(sum(len(p) for p in parts))
            parts.append(obj_bytes)

        add_obj(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        add_obj(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        add_obj(
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        )
        add_obj(
            f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        )
        add_obj(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        xref_pos = sum(len(p) for p in parts)
        xref = "xref\n0 6\n0000000000 65535 f \n"
        for off in offsets:
            xref += f"{off:010d} 00000 n \n"
        trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
        parts.append((xref + trailer).encode("latin1"))

        return b"".join(parts)
