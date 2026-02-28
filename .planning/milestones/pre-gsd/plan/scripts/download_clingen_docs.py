#!/usr/bin/env python3
"""
Download and convert specific ClinGen documents to markdown
"""

import os
import requests
from pathlib import Path
import pdfplumber
import PyPDF2
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Document URLs to download
DOCUMENTS = [
    {
        "url": "https://www.clinicalgenome.org/site/assets/files/9851/gene-disease_validity_standard_operating_procedures-_version_11_docx.pdf",
        "filename": "gene_disease_validity_sop_v11.pdf",
        "type": "pdf",
        "title": "Gene-Disease Validity Standard Operating Procedures Version 11",
    },
    {
        "url": "https://www.gimjournal.org/article/S1098-3600(22)00746-8/fulltext",
        "filename": "gimjournal_article.html",
        "type": "html",
        "title": "GIM Journal Article on Gene-Disease Associations",
    },
    {
        "url": "https://docs.google.com/document/d/1GpGWCRsQydeqZvR3ypnDSi2MPs8qwR7G/edit",
        "filename": "google_doc.html",
        "type": "google_doc",
        "title": "Google Document (requires export)",
    },
    {
        "url": "https://www.clinicalgenome.org/site/assets/files/8895/clingen_disease_naming_guidance_v1-1.pdf",
        "filename": "clingen_disease_naming_guidance.pdf",
        "type": "pdf",
        "title": "ClinGen Disease Naming Guidance",
    },
    {
        "url": "https://www.clinicalgenome.org/site/assets/files/5743/evidencesummary-v5_1-january2025.pdf",
        "filename": "evidence_summary_v5_1.pdf",
        "type": "pdf",
        "title": "Evidence Summary Template v5.1",
    },
]


class DocumentDownloader:
    def __init__(self, output_dir="clingen_documents"):
        self.output_dir = Path(output_dir)
        self.downloads_dir = Path("downloads")  # Raw downloads go here
        self.pdf_dir = self.downloads_dir / "pdfs"
        self.markdown_dir = self.output_dir / "markdown"

        # Create directories
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

        # Create session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def download_file(self, url, filename, file_type):
        """Download a file from URL"""
        try:
            logger.info(f"Downloading: {url}")

            # Handle Google Docs specially
            if file_type == "google_doc":
                # Convert to export URL
                doc_id = url.split("/d/")[1].split("/")[0]
                export_url = (
                    f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
                )
                logger.info(f"Converting Google Doc to PDF export URL: {export_url}")
                url = export_url
                filename = filename.replace(".html", ".pdf")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Determine save path
            if filename.endswith(".pdf"):
                filepath = self.pdf_dir / filename
            else:
                filepath = self.downloads_dir / filename

            # Save file
            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info(f"Saved: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF file"""
        try:
            text_content = []

            # Try pdfplumber first (better for complex layouts)
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text:
                            text_content.append(f"## Page {page_num}\n\n{text}")

                if text_content:
                    return "\n\n---\n\n".join(text_content)
            except Exception as e:
                logger.warning(f"pdfplumber failed for {pdf_path}: {e}")

            # Fallback to PyPDF2
            try:
                with open(pdf_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        text = page.extract_text()
                        if text:
                            text_content.append(f"## Page {page_num}\n\n{text}")

                return "\n\n---\n\n".join(text_content)
            except Exception as e:
                logger.warning(f"PyPDF2 failed for {pdf_path}: {e}")

        except Exception as e:
            logger.error(f"Could not extract text from {pdf_path}: {e}")

        return ""

    def extract_html_text(self, html_path):
        """Extract text from HTML file"""
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            logger.error(f"Error extracting HTML from {html_path}: {e}")
            return ""

    def convert_to_markdown(self, filepath, title, doc_type):
        """Convert document to markdown"""
        try:
            logger.info(f"Converting to markdown: {filepath}")

            if filepath.suffix.lower() == ".pdf":
                content = self.extract_pdf_text(filepath)
            elif filepath.suffix.lower() in [".html", ".htm"]:
                content = self.extract_html_text(filepath)
            else:
                logger.warning(f"Unsupported file type: {filepath}")
                return None

            if not content:
                logger.warning(f"No content extracted from {filepath}")
                return None

            # Create markdown content
            markdown_content = f"# {title}\n\n"
            markdown_content += f"**Source:** {doc_type}\n"
            markdown_content += f"**File:** {filepath.name}\n\n"
            markdown_content += "---\n\n"
            markdown_content += content

            # Save markdown
            markdown_filename = filepath.stem + ".md"
            markdown_path = self.markdown_dir / markdown_filename

            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"Saved markdown: {markdown_path}")
            return markdown_path

        except Exception as e:
            logger.error(f"Error converting {filepath} to markdown: {e}")
            return None

    def process_documents(self):
        """Download and convert all documents"""
        logger.info("Starting document download and conversion...")

        results = []

        for doc in DOCUMENTS:
            logger.info(f"\nProcessing: {doc['title']}")

            # Download file
            filepath = self.download_file(doc["url"], doc["filename"], doc["type"])
            if not filepath:
                continue

            # Convert to markdown
            markdown_path = self.convert_to_markdown(filepath, doc["title"], doc["url"])
            if markdown_path:
                results.append(
                    {
                        "title": doc["title"],
                        "original_file": filepath,
                        "markdown_file": markdown_path,
                    }
                )

        # Create index
        self.create_index(results)

        logger.info(f"\nCompleted! Processed {len(results)} documents")
        logger.info(f"PDFs saved to: {self.pdf_dir}")
        logger.info(f"Markdown files saved to: {self.markdown_dir}")

    def create_index(self, results):
        """Create an index of all converted documents"""
        index_content = "# ClinGen Training Materials Index\n\n"
        index_content += f"Total documents processed: {len(results)}\n\n"

        for result in results:
            rel_path = os.path.relpath(result["markdown_file"], self.output_dir)
            index_content += f"## {result['title']}\n"
            index_content += (
                f"- **Markdown:** [{result['markdown_file'].name}]({rel_path})\n"
            )
            index_content += f"- **Original:** {result['original_file'].name}\n\n"

        index_path = self.output_dir / "INDEX.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

        logger.info(f"Created index: {index_path}")


def main():
    downloader = DocumentDownloader()
    downloader.process_documents()


if __name__ == "__main__":
    main()
