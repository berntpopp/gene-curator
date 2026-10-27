# ClinGen Training Materials

This directory contains tools and resources for downloading and converting ClinGen (Clinical Genome Resource) training materials to accessible markdown format.

## Current Status

✅ **Successfully Downloaded and Converted**
- 5 ClinGen training documents converted to readable markdown format
- All documents cleaned and formatted for easy reading
- PDFs and HTML source files preserved in organized structure

## Directory Structure

```
scripts/
├── README.md                          # This file
├── download_clingen_docs.py           # Document downloader script
├── requirements.txt                   # Python dependencies
├── downloads/                         # Raw downloaded files
│   ├── pdfs/                         # Original PDF documents
│   │   ├── gene_disease_validity_sop_v11.pdf
│   │   ├── clingen_disease_naming_guidance.pdf
│   │   ├── evidence_summary_v5_1.pdf
│   │   └── google_doc.pdf
│   └── gimjournal_article.html       # Original HTML article
└── clingen_documents/                # Organized final outputs
    ├── INDEX.md                      # Index of all documents
    └── markdown/                     # Clean markdown versions
        ├── README.md                 # Markdown index
        ├── gene_disease_validity_sop_v11.md
        ├── clingen_disease_naming_guidance.md
        ├── evidence_summary_v5_1.md
        ├── gimjournal_article.md
        └── google_doc.md
```

## Successfully Converted Documents

### 1. Gene-Disease Validity Standard Operating Procedures v11
- **File**: `gene_disease_validity_sop_v11.md`
- **Source**: ClinGen official SOP document
- **Content**: Comprehensive procedures for gene-disease validity curation

### 2. ClinGen Disease Naming Guidance v1.1
- **File**: `clingen_disease_naming_guidance.md`
- **Source**: ClinGen naming standards document
- **Content**: Guidelines for dyadic naming conventions and disease nomenclature

### 3. Evidence Summary Template v5.1
- **File**: `evidence_summary_v5_1.md`
- **Source**: ClinGen evidence summary template
- **Content**: Standardized template for gene curation evidence summaries

### 4. GIM Journal Article
- **File**: `gimjournal_article.md`
- **Source**: Genetics in Medicine journal article
- **Content**: Gene-disease association methodology

### 5. Google Document
- **File**: `google_doc.md`
- **Source**: ClinGen Google document
- **Content**: Additional training materials

## Quick Start

### Prerequisites
- Python 3.8+
- Internet connection for downloading

### Setup and Run
```bash
# Install dependencies
pip install -r requirements.txt

# Download and convert documents
python download_clingen_docs.py
```

## Features

### 🔄 **Document Processing**
- **PDF Extraction**: Dual-engine approach using pdfplumber and PyPDF2
- **HTML Conversion**: Clean extraction from web pages
- **Text Enhancement**: Automatic formatting and cleanup
- **Markdown Output**: Human-readable format with proper structure

### 📁 **Organized Output**
- Raw files preserved in `downloads/` directory
- Clean markdown files in `clingen_documents/markdown/`
- Complete index and documentation
- Proper file organization and naming

### 🛡️ **Robust Processing**
- Error handling and fallback mechanisms
- Multiple PDF processing engines
- Clean text extraction and formatting
- Respectful web scraping practices

## Technical Details

### PDF Processing
Uses dual-engine approach for maximum compatibility:
1. **pdfplumber**: Primary engine for complex layouts
2. **PyPDF2**: Fallback for compatibility

### HTML Processing
- BeautifulSoup for robust HTML parsing
- Automatic cleanup of navigation and ads
- Clean text extraction with proper formatting

### Text Enhancement
- Removed page headers/footers and repeated content
- Fixed broken sentences across page boundaries
- Cleaned up excessive whitespace
- Proper bullet point formatting
- Improved section structure

## File Descriptions

### Core Scripts
- **`download_clingen_docs.py`**: Main downloader and converter script
- **`requirements.txt`**: Minimal Python dependencies (requests, beautifulsoup4, PyPDF2, pdfplumber)

### Output Files
- **`INDEX.md`**: Complete catalog of all converted documents
- **Individual `.md` files**: Clean, readable versions of each document
- **Raw files**: Original PDFs and HTML preserved for reference

## Usage Notes

- All documents are now successfully converted and ready for use
- Markdown files are cleaned and formatted for easy reading
- Original source files are preserved in the `downloads/` directory
- The conversion process handles text extraction issues and formatting problems

## Success Metrics

✅ **5/5 documents successfully downloaded**  
✅ **5/5 documents converted to readable markdown**  
✅ **All text formatting issues resolved**  
✅ **Clean directory structure organized**  
✅ **Complete documentation and indexing**

---

**Project Status**: ✅ Complete  
**Last Updated**: January 2025  
**Total Documents**: 5 ClinGen training materials