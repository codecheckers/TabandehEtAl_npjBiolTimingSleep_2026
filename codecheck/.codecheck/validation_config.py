"""
Configuration constants for codecheck.yml validation
"""

# Required fields according to CODECHECK spec
MANDATORY_FIELDS = ['manifest', 'codechecker', 'report', 'version', 'paper', 'repository', 'check_time', 'certificate', 'summary']

# Recommended fields for complete certificates (now empty - all promoted to mandatory)
RECOMMENDED_FIELDS = []

# Optional but recognized fields
OPTIONAL_FIELDS = ['source']

# Placeholder patterns that indicate incomplete configuration
PLACEHOLDER_PATTERNS = {
    'strings': ['FIXME', 'TODO', 'template', 'example', 'XXXXX', 'placeholder'],
    'certificate_patterns': [
        r'^YYYY-\d{3}$',      # Year placeholder
        r'^0000-\d{3}$',      # Zero year
        r'^9999-\d{3}$',      # Invalid year
    ],
    'doi_patterns': [
        r'XXXXX',
        r'placeholder',
        r'example',
        r'10\.5281/zenodo\.XXXXXX',  # Zenodo placeholder
    ]
}

# Expected formats for validation
CERTIFICATE_FORMAT = r'^\d{4}-\d{3}$'  # YYYY-NNN (e.g., 2023-001)
ORCID_FORMAT = r'^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$'  # Standard ORCID format
DOI_FORMAT = r'^10\.\d{4,}/[^\s]+$'  # Basic DOI format
ISO_DATE_FORMAT = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'  # ISO 8601 basic format

# Nested field paths for validation
PAPER_FIELDS = ['title', 'authors', 'reference']
AUTHOR_FIELDS = ['name', 'ORCID']
CODECHECKER_FIELDS = ['name', 'ORCID']
MANIFEST_ENTRY_FIELDS = ['file']  # 'comment' is optional
