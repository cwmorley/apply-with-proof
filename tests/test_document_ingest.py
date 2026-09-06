import io
import unittest
import zipfile

from document_ingest import extract_document_text


class DocumentIngestTests(unittest.TestCase):
    def test_plain_text_document(self):
        result = extract_document_text("narrative.md", b"I built a launch system.")
        self.assertEqual(result["format"], "md")
        self.assertIn("launch system", result["text"])

    def test_docx_document(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Built a product system.</w:t></w:r></w:p></w:body></w:document>'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", xml)
        result = extract_document_text("resume.docx", buffer.getvalue())
        self.assertIn("Built a product system", result["text"])


if __name__ == "__main__":
    unittest.main()
