"""
Validation module for CODECHECK certificates
https://codecheck.org.uk
"""
import yaml
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import requests

from validation_config import (
    MANDATORY_FIELDS,
    RECOMMENDED_FIELDS,
    OPTIONAL_FIELDS,
    PLACEHOLDER_PATTERNS,
    CERTIFICATE_FORMAT,
    ORCID_FORMAT,
    DOI_FORMAT,
    ISO_DATE_FORMAT,
    PAPER_FIELDS,
    AUTHOR_FIELDS,
    CODECHECKER_FIELDS,
    MANIFEST_ENTRY_FIELDS,
)


@dataclass
class ValidationIssue:
    """Represents a validation issue found during checking"""
    level: str  # 'error', 'warning', 'info'
    field: str
    message: str
    suggestion: Optional[str] = None

    def __str__(self):
        result = f"[{self.level.upper()}] {self.field}: {self.message}"
        if self.suggestion:
            result += f"\n  → Suggestion: {self.suggestion}"
        return result


class CodecheckValidator:
    """
    Validator for codecheck.yml files following the CODECHECK specification.

    Performs validation checks including:
    - YAML syntax validation
    - Required field completeness
    - Placeholder detection
    - Format validation (certificates, ORCIDs, DOIs, dates)
    - Manifest file existence
    """

    def __init__(self, config_path: str):
        """
        Initialize validator with path to codecheck.yml

        Parameters
        ----------
        config_path : str
            Path to the codecheck.yml file
        """
        self.config_path = Path(config_path)
        self.issues: List[ValidationIssue] = []
        self.config: Optional[Dict] = None

    def validate_yaml_syntax(self) -> bool:
        """
        Validate YAML syntax and load configuration.

        Returns
        -------
        bool
            True if YAML is valid and can be loaded, False otherwise
        """
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            if self.config is None:
                self.issues.append(ValidationIssue(
                    level='error',
                    field='syntax',
                    message="YAML file is empty or contains only null value",
                    suggestion="Add valid CODECHECK configuration to the file"
                ))
                return False
            return True
        except FileNotFoundError:
            self.issues.append(ValidationIssue(
                level='error',
                field='file',
                message=f"Configuration file not found: {self.config_path}",
                suggestion="Ensure codecheck.yml exists in the correct location"
            ))
            return False
        except yaml.YAMLError as e:
            self.issues.append(ValidationIssue(
                level='error',
                field='syntax',
                message=f"Invalid YAML syntax: {e}",
                suggestion="Check YAML formatting, indentation, and special characters"
            ))
            return False

    def validate_field_completeness(self) -> bool:
        """
        Check for presence of required and recommended fields.

        Returns
        -------
        bool
            True if all mandatory fields are present, False otherwise
        """
        if not self.config:
            return False

        has_errors = False

        # Check mandatory fields
        for field in MANDATORY_FIELDS:
            if not self._field_present(field):
                self.issues.append(ValidationIssue(
                    level='error',
                    field=field,
                    message=f"Mandatory field '{field}' is missing or empty",
                    suggestion=f"Add '{field}' field to codecheck.yml with appropriate value"
                ))
                has_errors = True

        # Check recommended fields
        for field in RECOMMENDED_FIELDS:
            if not self._field_present(field):
                self.issues.append(ValidationIssue(
                    level='warning',
                    field=field,
                    message=f"Recommended field '{field}' is missing",
                    suggestion=f"Consider adding '{field}' for a complete certificate"
                ))

        return not has_errors

    def _field_present(self, field: str) -> bool:
        """
        Check if a field exists and is not a placeholder.

        Parameters
        ----------
        field : str
            Field name to check

        Returns
        -------
        bool
            True if field is present and not a placeholder
        """
        value = self.config.get(field)
        if value is None or value == '':
            return False
        if isinstance(value, str) and self.is_placeholder(value):
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        if isinstance(value, dict) and len(value) == 0:
            return False
        return True

    def is_placeholder(self, value: Any) -> bool:
        """
        Detect if a value is a placeholder.

        Parameters
        ----------
        value : Any
            Value to check

        Returns
        -------
        bool
            True if value appears to be a placeholder
        """
        if not isinstance(value, str):
            return False
        value_lower = value.lower().strip()
        for pattern in PLACEHOLDER_PATTERNS['strings']:
            if pattern.lower() in value_lower:
                return True
        return False

    def validate_certificate_id(self) -> bool:
        """
        Validate certificate ID format and check for placeholders.

        Returns
        -------
        bool
            True if certificate is valid or not required, False if invalid
        """
        cert = self.config.get('certificate')
        if not cert:
            self.issues.append(ValidationIssue(
                level='warning',
                field='certificate',
                message="Certificate ID is not set",
                suggestion="Add certificate ID when assigned (format: YYYY-NNN, e.g., 2023-001)"
            ))
            return True  # Not mandatory, just a warning

        if not isinstance(cert, str):
            self.issues.append(ValidationIssue(
                level='error',
                field='certificate',
                message=f"Certificate ID must be a string, got {type(cert).__name__}",
                suggestion="Use format YYYY-NNN (e.g., 2023-001)"
            ))
            return False

        # Check placeholder patterns
        for pattern in PLACEHOLDER_PATTERNS['certificate_patterns']:
            if re.match(pattern, cert):
                self.issues.append(ValidationIssue(
                    level='warning',
                    field='certificate',
                    message=f"Certificate ID '{cert}' appears to be a placeholder",
                    suggestion="Replace with actual certificate ID (format: YYYY-NNN)"
                ))
                return False

        # Validate format
        if not re.match(CERTIFICATE_FORMAT, cert):
            self.issues.append(ValidationIssue(
                level='error',
                field='certificate',
                message=f"Certificate ID '{cert}' has invalid format",
                suggestion="Use format YYYY-NNN where YYYY is year and NNN is a 3-digit number (e.g., 2023-001)"
            ))
            return False

        return True

    def validate_report_doi(self) -> bool:
        """
        Validate report DOI/URL format.

        Returns
        -------
        bool
            True if report is valid, False otherwise
        """
        report = self.config.get('report')
        if not report:
            # Already caught by mandatory field check
            return False

        if not isinstance(report, str):
            self.issues.append(ValidationIssue(
                level='error',
                field='report',
                message=f"Report must be a string, got {type(report).__name__}",
                suggestion="Provide a DOI or URL for the report"
            ))
            return False

        # Check for placeholders
        for pattern in PLACEHOLDER_PATTERNS['doi_patterns']:
            if re.search(pattern, report, re.IGNORECASE):
                self.issues.append(ValidationIssue(
                    level='warning',
                    field='report',
                    message=f"Report DOI/URL appears to contain placeholder: {report}",
                    suggestion="Replace with actual Zenodo DOI or report URL"
                ))
                return False

        # Check if it's a valid URL or DOI
        if not (report.startswith('http://') or report.startswith('https://') or
                report.startswith('doi:') or re.match(DOI_FORMAT, report)):
            self.issues.append(ValidationIssue(
                level='warning',
                field='report',
                message=f"Report does not appear to be a valid URL or DOI: {report}",
                suggestion="Provide a complete URL (https://...) or DOI (10.xxxx/...)"
            ))
            return False

        return True

    def validate_orcids(self) -> bool:
        """
        Validate ORCID format for authors and codechecker.

        Returns
        -------
        bool
            True if all ORCIDs are valid or missing, False if invalid
        """
        has_errors = False

        # Validate codechecker ORCID
        codechecker = self.config.get('codechecker', {})
        if isinstance(codechecker, dict):
            orcid = codechecker.get('ORCID', '')
            if orcid and not re.match(ORCID_FORMAT, orcid):
                self.issues.append(ValidationIssue(
                    level='error',
                    field='codechecker.ORCID',
                    message=f"Codechecker ORCID '{orcid}' has invalid format",
                    suggestion="Use format: 0000-0000-0000-0000"
                ))
                has_errors = True

        # Validate author ORCIDs
        paper = self.config.get('paper', {})
        if isinstance(paper, dict):
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                for i, author in enumerate(authors):
                    if isinstance(author, dict):
                        orcid = author.get('ORCID', '')
                        if orcid and not re.match(ORCID_FORMAT, orcid):
                            self.issues.append(ValidationIssue(
                                level='error',
                                field=f'paper.authors[{i}].ORCID',
                                message=f"Author {i+1} ORCID '{orcid}' has invalid format",
                                suggestion="Use format: 0000-0000-0000-0000"
                            ))
                            has_errors = True

        return not has_errors

    def validate_check_time(self) -> bool:
        """
        Validate check_time format (ISO 8601).

        Returns
        -------
        bool
            True if check_time is valid or missing, False if invalid
        """
        check_time = self.config.get('check_time')
        if not check_time:
            # Warning already issued in field completeness check
            return True

        if not isinstance(check_time, str):
            self.issues.append(ValidationIssue(
                level='error',
                field='check_time',
                message=f"check_time must be a string, got {type(check_time).__name__}",
                suggestion="Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS"
            ))
            return False

        # Try to parse as ISO format
        try:
            datetime.fromisoformat(check_time)
            return True
        except ValueError:
            self.issues.append(ValidationIssue(
                level='error',
                field='check_time',
                message=f"check_time '{check_time}' is not in valid ISO 8601 format",
                suggestion="Use format: YYYY-MM-DDTHH:MM:SS (e.g., 2023-11-15T14:30:00)"
            ))
            return False

    def validate_paper_structure(self) -> bool:
        """
        Validate paper section structure.

        Returns
        -------
        bool
            True if paper structure is valid, False otherwise
        """
        paper = self.config.get('paper')
        if not paper:
            # Already caught by recommended field check
            return True

        if not isinstance(paper, dict):
            self.issues.append(ValidationIssue(
                level='error',
                field='paper',
                message=f"Paper must be a dictionary, got {type(paper).__name__}",
                suggestion="Structure paper as: {title: '...', authors: [...], reference: '...'}"
            ))
            return False

        has_errors = False

        # Check paper subfields
        for subfield in PAPER_FIELDS:
            if subfield not in paper or not paper[subfield]:
                self.issues.append(ValidationIssue(
                    level='warning',
                    field=f'paper.{subfield}',
                    message=f"Paper {subfield} is missing",
                    suggestion=f"Add paper.{subfield} for complete paper metadata"
                ))

        # Validate authors structure
        authors = paper.get('authors', [])
        if not isinstance(authors, list):
            self.issues.append(ValidationIssue(
                level='error',
                field='paper.authors',
                message=f"Authors must be a list, got {type(authors).__name__}",
                suggestion="Structure authors as list: [{name: '...', ORCID: '...'}, ...]"
            ))
            has_errors = True
        elif len(authors) == 0:
            self.issues.append(ValidationIssue(
                level='warning',
                field='paper.authors',
                message="Authors list is empty",
                suggestion="Add at least one author with name and ORCID"
            ))
        else:
            for i, author in enumerate(authors):
                if not isinstance(author, dict):
                    self.issues.append(ValidationIssue(
                        level='error',
                        field=f'paper.authors[{i}]',
                        message=f"Author {i+1} must be a dictionary",
                        suggestion="Use format: {name: '...', ORCID: '...'}"
                    ))
                    has_errors = True
                elif 'name' not in author or not author['name']:
                    self.issues.append(ValidationIssue(
                        level='error',
                        field=f'paper.authors[{i}].name',
                        message=f"Author {i+1} is missing name",
                        suggestion="Add name field for each author"
                    ))
                    has_errors = True

        return not has_errors

    def validate_codechecker_structure(self) -> bool:
        """
        Validate codechecker section structure.

        Returns
        -------
        bool
            True if codechecker structure is valid, False otherwise
        """
        codechecker = self.config.get('codechecker')
        if not codechecker:
            # Already caught by mandatory field check
            return False

        if not isinstance(codechecker, dict):
            self.issues.append(ValidationIssue(
                level='error',
                field='codechecker',
                message=f"Codechecker must be a dictionary, got {type(codechecker).__name__}",
                suggestion="Structure codechecker as: {name: '...', ORCID: '...'}"
            ))
            return False

        if 'name' not in codechecker or not codechecker['name']:
            self.issues.append(ValidationIssue(
                level='error',
                field='codechecker.name',
                message="Codechecker name is missing",
                suggestion="Add name field for codechecker"
            ))
            return False

        if 'ORCID' not in codechecker or not codechecker['ORCID']:
            self.issues.append(ValidationIssue(
                level='warning',
                field='codechecker.ORCID',
                message="Codechecker ORCID is missing",
                suggestion="Add ORCID field for codechecker"
            ))

        return True

    def validate_manifest_structure(self) -> bool:
        """
        Validate manifest section structure.

        Returns
        -------
        bool
            True if manifest structure is valid, False otherwise
        """
        manifest = self.config.get('manifest')
        if not manifest:
            # Already caught by mandatory field check
            return False

        if not isinstance(manifest, list):
            self.issues.append(ValidationIssue(
                level='error',
                field='manifest',
                message=f"Manifest must be a list, got {type(manifest).__name__}",
                suggestion="Structure manifest as list: [{file: '...', comment: '...'}, ...]"
            ))
            return False

        if len(manifest) == 0:
            self.issues.append(ValidationIssue(
                level='error',
                field='manifest',
                message="Manifest is empty",
                suggestion="Add at least one file entry to manifest"
            ))
            return False

        has_errors = False
        for i, entry in enumerate(manifest):
            if not isinstance(entry, dict):
                self.issues.append(ValidationIssue(
                    level='error',
                    field=f'manifest[{i}]',
                    message=f"Manifest entry {i+1} must be a dictionary",
                    suggestion="Use format: {file: '...', comment: '...'}"
                ))
                has_errors = True
            elif 'file' not in entry or not entry['file']:
                self.issues.append(ValidationIssue(
                    level='error',
                    field=f'manifest[{i}].file',
                    message=f"Manifest entry {i+1} is missing 'file' field",
                    suggestion="Each manifest entry must have a 'file' field"
                ))
                has_errors = True

        return not has_errors

    def validate_manifest_files(self, base_dir: Optional[Path] = None) -> bool:
        """
        Validate that manifest files exist in the outputs directory.

        Parameters
        ----------
        base_dir : Path, optional
            Base directory containing codecheck/ subdirectory.
            Defaults to parent of config file.

        Returns
        -------
        bool
            True if all files exist, False if any are missing
        """
        if base_dir is None:
            base_dir = self.config_path.parent

        manifest = self.config.get('manifest', [])
        if not manifest:
            # Already caught by mandatory field check
            return False

        missing_files = []
        outputs_dir = base_dir / 'codecheck' / 'outputs'

        if not outputs_dir.exists():
            self.issues.append(ValidationIssue(
                level='error',
                field='manifest',
                message=f"Outputs directory does not exist: {outputs_dir}",
                suggestion="Create codecheck/outputs/ directory and copy manifest files there"
            ))
            return False

        for entry in manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            if not file_path:
                continue

            full_path = outputs_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            self.issues.append(ValidationIssue(
                level='error',
                field='manifest',
                message=f"Missing {len(missing_files)} file(s) in outputs/: {', '.join(missing_files[:5])}{'...' if len(missing_files) > 5 else ''}",
                suggestion="Copy all manifest files to codecheck/outputs/ directory"
            ))
            return False

        return True

    def validate_register_issue(self, timeout: int = 10) -> bool:
        """
        Validate that a GitHub issue exists for this certificate in the CODECHECK register.

        Checks the codecheckers/register repository for an issue matching the certificate ID.
        Raises an error if no issue is found, and warns if the issue is closed or unassigned.

        Parameters
        ----------
        timeout : int, optional
            Request timeout in seconds. Defaults to 10.

        Returns
        -------
        bool
            True if issue exists and is open with assignee, False otherwise
        """
        cert = self.config.get('certificate')
        if not cert:
            # Certificate not set, skip this check
            return True

        if not isinstance(cert, str):
            # Invalid certificate format, already caught by other validation
            return True

        # Check if certificate is a placeholder
        for pattern in PLACEHOLDER_PATTERNS['certificate_patterns']:
            if re.match(pattern, cert):
                # Placeholder certificate, skip register check
                return True

        # Validate certificate format
        if not re.match(CERTIFICATE_FORMAT, cert):
            # Invalid format, already caught by validate_certificate_id
            return True

        try:
            # Search for issues with the certificate ID in the title
            # Using GitHub API v3 (REST API)
            url = "https://api.github.com/repos/codecheckers/register/issues"
            params = {
                'state': 'all',  # Include both open and closed issues
                'per_page': 100  # Get up to 100 results
            }

            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            issues = response.json()

            # Find issue with certificate ID in title
            matching_issue = None
            for issue in issues:
                # Check if certificate ID appears in the issue title
                if cert in issue.get('title', ''):
                    matching_issue = issue
                    break

            if not matching_issue:
                # No matching issue found - this is an error
                self.issues.append(ValidationIssue(
                    level='error',
                    field='certificate',
                    message=f"No issue found in codecheckers/register for certificate {cert}",
                    suggestion=f"Create an issue at https://github.com/codecheckers/register/issues with certificate {cert} in the title"
                ))
                return False

            # Check if issue is closed
            if matching_issue.get('state') == 'closed':
                self.issues.append(ValidationIssue(
                    level='warning',
                    field='certificate',
                    message=f"Register issue for certificate {cert} is closed (issue #{matching_issue.get('number')})",
                    suggestion=f"Consider reopening the issue if the certificate is still being processed: {matching_issue.get('html_url')}"
                ))

            # Check if issue is unassigned
            if not matching_issue.get('assignees') or len(matching_issue.get('assignees', [])) == 0:
                self.issues.append(ValidationIssue(
                    level='warning',
                    field='certificate',
                    message=f"Register issue for certificate {cert} is unassigned (issue #{matching_issue.get('number')})",
                    suggestion=f"Consider assigning the issue to a codechecker: {matching_issue.get('html_url')}"
                ))

            # Issue exists
            return True

        except requests.exceptions.Timeout:
            self.issues.append(ValidationIssue(
                level='warning',
                field='certificate',
                message=f"Timeout while checking register for certificate {cert}",
                suggestion="Check your internet connection and try again"
            ))
            return True  # Don't fail validation on timeout
        except requests.exceptions.RequestException as e:
            self.issues.append(ValidationIssue(
                level='warning',
                field='certificate',
                message=f"Could not check register for certificate {cert}: {str(e)}",
                suggestion="Verify network connection or check GitHub API status"
            ))
            return True  # Don't fail validation on network errors
        except Exception as e:
            self.issues.append(ValidationIssue(
                level='warning',
                field='certificate',
                message=f"Unexpected error checking register: {str(e)}",
                suggestion="Please report this issue"
            ))
            return True  # Don't fail validation on unexpected errors

    def validate_all(self,
                     check_manifest: bool = True,
                     check_register: bool = True,
                     strict: bool = False) -> Tuple[bool, List[ValidationIssue]]:
        """
        Run all validation checks.

        Parameters
        ----------
        check_manifest : bool, optional
            Whether to check if manifest files exist. Defaults to True.
        check_register : bool, optional
            Whether to check for GitHub register issue. Defaults to True.
        strict : bool, optional
            If True, warnings are treated as failures. Defaults to False.

        Returns
        -------
        tuple
            (passed: bool, issues: List[ValidationIssue])
        """
        self.issues = []

        # 1. Syntax check (must pass to continue)
        if not self.validate_yaml_syntax():
            return False, self.issues

        # 2. Field completeness
        self.validate_field_completeness()

        # 3. Structure validations
        self.validate_manifest_structure()
        self.validate_codechecker_structure()
        self.validate_paper_structure()

        # 4. Format validations
        self.validate_certificate_id()
        self.validate_report_doi()
        self.validate_orcids()
        self.validate_check_time()

        # 5. Manifest file existence
        if check_manifest:
            self.validate_manifest_files()

        # 6. Register issue check
        if check_register:
            self.validate_register_issue()

        # Determine pass/fail
        has_errors = any(i.level == 'error' for i in self.issues)
        has_warnings = any(i.level == 'warning' for i in self.issues)

        passed = not has_errors if not strict else not (has_errors or has_warnings)
        return passed, self.issues

    def format_report(self, markdown: bool = True) -> str:
        """
        Format validation issues as a report.

        Parameters
        ----------
        markdown : bool, optional
            If True, format as Markdown. Otherwise plain text. Defaults to True.

        Returns
        -------
        str
            Formatted validation report
        """
        if not self.issues:
            return "✓ All validations passed!" if not markdown else "## ✓ All validations passed!"

        errors = [i for i in self.issues if i.level == 'error']
        warnings = [i for i in self.issues if i.level == 'warning']
        infos = [i for i in self.issues if i.level == 'info']

        if markdown:
            return self._format_markdown(errors, warnings, infos)
        else:
            return self._format_text(errors, warnings, infos)

    def _format_markdown(self, errors, warnings, infos) -> str:
        """Format report as Markdown"""
        report = []

        if errors:
            report.append(f"## ❌ Errors ({len(errors)})\n")
            for issue in errors:
                report.append(f"- **{issue.field}**: {issue.message}")
                if issue.suggestion:
                    report.append(f"  - *Suggestion*: {issue.suggestion}")

        if warnings:
            report.append(f"\n## ⚠️  Warnings ({len(warnings)})\n")
            for issue in warnings:
                report.append(f"- **{issue.field}**: {issue.message}")
                if issue.suggestion:
                    report.append(f"  - *Suggestion*: {issue.suggestion}")

        if infos:
            report.append(f"\n## ℹ️  Information ({len(infos)})\n")
            for issue in infos:
                report.append(f"- **{issue.field}**: {issue.message}")
                if issue.suggestion:
                    report.append(f"  - *Suggestion*: {issue.suggestion}")

        return "\n".join(report)

    def _format_text(self, errors, warnings, infos) -> str:
        """Format report as plain text"""
        report = []

        if errors:
            report.append(f"ERRORS ({len(errors)}):")
            for issue in errors:
                report.append(f"  [{issue.field}] {issue.message}")
                if issue.suggestion:
                    report.append(f"    → {issue.suggestion}")

        if warnings:
            report.append(f"\nWARNINGS ({len(warnings)}):")
            for issue in warnings:
                report.append(f"  [{issue.field}] {issue.message}")
                if issue.suggestion:
                    report.append(f"    → {issue.suggestion}")

        if infos:
            report.append(f"\nINFORMATION ({len(infos)}):")
            for issue in infos:
                report.append(f"  [{issue.field}] {issue.message}")
                if issue.suggestion:
                    report.append(f"    → {issue.suggestion}")

        return "\n".join(report)
