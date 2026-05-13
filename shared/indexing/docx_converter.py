"""Office document to PDF conversion using LibreOffice headless."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def _find_libreoffice() -> str | None:
    """Find LibreOffice executable path across platforms."""
    for cmd in ["libreoffice", "soffice"]:
        if shutil.which(cmd):
            return cmd

    if sys.platform == "win32":
        windows_paths = [
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        ]
        for path in windows_paths:
            if path.exists():
                return str(path)

    if sys.platform == "darwin":
        mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if mac_path.exists():
            return str(mac_path)

    return None


def convert_office_to_pdf(content: bytes, suffix: str = ".docx") -> bytes | None:
    """
    Convert an Office document to PDF using LibreOffice headless.

    Supports DOCX, XLSX, and other formats LibreOffice can handle.
    LibreOffice auto-detects the input format based on the file extension.
    """
    libreoffice_cmd = _find_libreoffice()
    if not libreoffice_cmd:
        logger.error(
            "libreoffice_not_found",
            message="LibreOffice not found in PATH or standard locations",
        )
        return None

    logger.info("using_libreoffice", path=libreoffice_cmd, input_suffix=suffix)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / f"input{suffix}"
        input_path.write_bytes(content)

        try:
            result = subprocess.run(
                [
                    libreoffice_cmd,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmpdir_path),
                    str(input_path),
                ],
                capture_output=True,
                timeout=120,
            )

            if result.returncode != 0:
                logger.error(
                    "libreoffice_conversion_failed",
                    stderr=result.stderr.decode()[:500],
                    returncode=result.returncode,
                )
                return None

            pdf_path = tmpdir_path / "input.pdf"
            if not pdf_path.exists():
                logger.error("libreoffice_pdf_not_created")
                return None

            pdf_content = pdf_path.read_bytes()
            logger.info(
                "office_to_pdf_conversion_complete",
                input_suffix=suffix,
                input_size=len(content),
                output_size=len(pdf_content),
            )
            return pdf_content

        except subprocess.TimeoutExpired:
            logger.error("libreoffice_conversion_timeout")
            return None
        except FileNotFoundError:
            logger.error("libreoffice_not_installed")
            return None
        except Exception as e:
            logger.error("libreoffice_conversion_error", error=str(e))
            return None
