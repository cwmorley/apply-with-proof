"""Small, local document and web-page ingestion helpers.

The server returns extracted text only. It does not retain uploaded bytes or
fetched pages after the request completes.
"""

from __future__ import annotations

import base64
import html
import ipaddress
import io
import re
import socket
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from typing import Any
from xml.etree import ElementTree


MAX_DOCUMENT_BYTES = 12 * 1024 * 1024
MAX_PAGE_BYTES = 4 * 1024 * 1024


class _PageTextParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "section", "article"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "section", "article"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = html.unescape(data).strip()
        if not text:
            return
        if self.in_title:
            self.title += f" {text}"
        self.parts.append(text)

    def result(self) -> tuple[str, str]:
        text = re.sub(r"[ \t]+", " ", " ".join(self.parts))
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        return self.title.strip(), text


def _safe_url(url: str) -> str:
    parsed = urllib.parse.urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Job URL must start with http:// or https://")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise ValueError("Local and metadata hostnames are not allowed")
    try:
        address = ipaddress.ip_address(hostname)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise ValueError("Private, loopback, and reserved IP addresses are not allowed")
    except ValueError as exc:
        if str(exc).startswith("Private,") or str(exc).startswith("Local"):
            raise
    return url.strip()


def fetch_job_url(url: str) -> dict[str, Any]:
    """Fetch a public page and return title, text, and honest extraction notes."""
    safe_url = _safe_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={"User-Agent": "CareerEvidenceCompiler/0.1 (local personal-use tool)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            content_type = response.headers.get_content_type()
            raw = response.read(MAX_PAGE_BYTES + 1)
            final_url = response.geturl()
    except Exception as exc:
        raise ValueError(f"Could not fetch that URL: {exc}") from exc
    if len(raw) > MAX_PAGE_BYTES:
        raise ValueError("The page is larger than the 4 MB local extraction limit")
    if content_type == "text/html" or raw.lstrip().startswith(b"<"):
        parser = _PageTextParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
        title, text = parser.result()
    else:
        title = ""
        text = raw.decode("utf-8", errors="replace")
    warnings = []
    if len(text) < 300:
        warnings.append("Very little text was extracted. The page may require JavaScript or may block automated fetches; paste the job text manually if needed.")
    if not text:
        warnings.append("No readable text was extracted.")
    return {"url": final_url, "title": title, "text": text, "warnings": warnings, "content_type": content_type}


def _docx_text(raw: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.iter():
        if paragraph.tag.endswith("}p"):
            chunks = [node.text or "" for node in paragraph.iter() if node.tag.endswith("}t")]
            if chunks:
                paragraphs.append("".join(chunks))
    return "\n".join(paragraphs).strip()


def _pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF extraction needs the bundled pypdf package") from exc
    reader = PdfReader(io.BytesIO(raw))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_document_text(filename: str, raw: bytes) -> dict[str, Any]:
    """Extract text from a user-selected resume or narrative document."""
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("The document is larger than the 12 MB local extraction limit")
    suffix = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if suffix in {"txt", "md", "markdown", "rtf"}:
        text = raw.decode("utf-8", errors="replace")
    elif suffix == "docx":
        text = _docx_text(raw)
    elif suffix == "pdf":
        text = _pdf_text(raw)
    else:
        raise ValueError("Supported document types are PDF, DOCX, TXT, Markdown, and RTF")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("No readable text was found in that document")
    return {"filename": filename, "text": text, "characters": len(text), "format": suffix}


def extract_base64_document(filename: str, encoded: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Uploaded document data was not valid base64") from exc
    return extract_document_text(filename, raw)
