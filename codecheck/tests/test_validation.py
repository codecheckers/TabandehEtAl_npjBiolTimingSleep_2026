"""
Tests for validation module
"""
import pytest
from pathlib import Path
import sys

# Add .codecheck to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / '.codecheck'))
from validation import CodecheckValidator, ValidationIssue


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory"""
    return Path(__file__).parent / 'fixtures'


def test_validate_yaml_syntax_valid(fixtures_dir):
    """Test validation of valid YAML file"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    assert validator.validate_yaml_syntax() == True
    assert len(validator.issues) == 0
    assert validator.config is not None


def test_validate_yaml_syntax_invalid(fixtures_dir):
    """Test detection of invalid YAML syntax"""
    validator = CodecheckValidator(fixtures_dir / 'invalid_syntax.yml')
    assert validator.validate_yaml_syntax() == False
    assert len(validator.issues) > 0
    assert any(i.level == 'error' for i in validator.issues)
    assert any('syntax' in i.field.lower() for i in validator.issues)


def test_validate_yaml_file_not_found():
    """Test handling of missing configuration file"""
    validator = CodecheckValidator('nonexistent.yml')
    assert validator.validate_yaml_syntax() == False
    assert len(validator.issues) > 0
    assert validator.issues[0].level == 'error'
    assert 'not found' in validator.issues[0].message.lower()


def test_placeholder_detection():
    """Test detection of placeholder values"""
    validator = CodecheckValidator('dummy.yml')  # Path doesn't matter for this test

    # Test various placeholder patterns
    assert validator.is_placeholder("FIXME") == True
    assert validator.is_placeholder("TODO: add title") == True
    assert validator.is_placeholder("This is a template") == True
    assert validator.is_placeholder("example value") == True
    assert validator.is_placeholder("XXXXX") == True

    # Test non-placeholder values
    assert validator.is_placeholder("Real Title") == False
    assert validator.is_placeholder("Actual Value") == False
    assert validator.is_placeholder("") == False


def test_certificate_format_valid(fixtures_dir):
    """Test validation of valid certificate format"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_certificate_id() == True
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) == 0


def test_certificate_format_placeholder(fixtures_dir):
    """Test detection of placeholder certificate ID"""
    validator = CodecheckValidator(fixtures_dir / 'placeholder_values.yml')
    validator.validate_yaml_syntax()
    validator.validate_certificate_id()

    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('placeholder' in i.message.lower() for i in cert_issues)


def test_certificate_format_invalid(fixtures_dir):
    """Test detection of invalid certificate format"""
    validator = CodecheckValidator(fixtures_dir / 'invalid_formats.yml')
    validator.validate_yaml_syntax()
    validator.validate_certificate_id()

    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('invalid format' in i.message.lower() for i in cert_issues)


def test_missing_mandatory_fields(fixtures_dir):
    """Test detection of missing mandatory fields"""
    validator = CodecheckValidator(fixtures_dir / 'missing_fields.yml')
    validator.validate_yaml_syntax()
    validator.validate_field_completeness()

    errors = [i for i in validator.issues if i.level == 'error']
    assert len(errors) > 0

    # Check that mandatory fields are flagged
    error_fields = [i.field for i in errors]
    assert 'manifest' in error_fields
    assert 'codechecker' in error_fields
    assert 'report' in error_fields


def test_field_completeness_valid(fixtures_dir):
    """Test that valid file passes completeness check"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_field_completeness() == True


def test_orcid_format_validation_valid(fixtures_dir):
    """Test validation of valid ORCID format"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_orcids() == True
    orcid_issues = [i for i in validator.issues if 'ORCID' in i.field]
    assert len(orcid_issues) == 0


def test_orcid_format_validation_invalid(fixtures_dir):
    """Test detection of invalid ORCID format"""
    validator = CodecheckValidator(fixtures_dir / 'invalid_formats.yml')
    validator.validate_yaml_syntax()
    validator.validate_orcids()

    orcid_issues = [i for i in validator.issues if 'ORCID' in i.field]
    assert len(orcid_issues) > 0
    assert all(i.level == 'error' for i in orcid_issues)


def test_check_time_format_valid(fixtures_dir):
    """Test validation of valid check_time format"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_check_time() == True


def test_check_time_format_invalid(fixtures_dir):
    """Test detection of invalid check_time format"""
    validator = CodecheckValidator(fixtures_dir / 'invalid_formats.yml')
    validator.validate_yaml_syntax()
    validator.validate_check_time()

    time_issues = [i for i in validator.issues if i.field == 'check_time']
    assert len(time_issues) > 0
    assert any('ISO' in i.message for i in time_issues)


def test_paper_structure_validation(fixtures_dir):
    """Test validation of paper structure"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_paper_structure() == True


def test_codechecker_structure_validation(fixtures_dir):
    """Test validation of codechecker structure"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_codechecker_structure() == True


def test_manifest_structure_validation(fixtures_dir):
    """Test validation of manifest structure"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_manifest_structure() == True


def test_validate_all_valid_file(fixtures_dir):
    """Test complete validation of valid file"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    passed, issues = validator.validate_all(check_manifest=False, check_register=False, strict=False)

    # Should pass with possible warnings but no errors
    errors = [i for i in issues if i.level == 'error']
    assert len(errors) == 0


def test_validate_all_invalid_file(fixtures_dir):
    """Test complete validation of invalid file"""
    validator = CodecheckValidator(fixtures_dir / 'missing_fields.yml')
    passed, issues = validator.validate_all(check_manifest=False, check_register=False, strict=False)

    # Should fail due to errors
    assert passed == False
    errors = [i for i in issues if i.level == 'error']
    assert len(errors) > 0


def test_validate_all_strict_mode(fixtures_dir):
    """Test strict mode treats warnings as failures"""
    validator = CodecheckValidator(fixtures_dir / 'placeholder_values.yml')
    passed, issues = validator.validate_all(check_manifest=False, check_register=False, strict=True)

    # Should fail in strict mode due to placeholders (warnings)
    assert passed == False
    warnings = [i for i in issues if i.level == 'warning']
    assert len(warnings) > 0


def test_format_report_markdown(fixtures_dir):
    """Test Markdown report formatting"""
    validator = CodecheckValidator(fixtures_dir / 'missing_fields.yml')
    validator.validate_all(check_manifest=False, strict=False)

    report = validator.format_report(markdown=True)
    assert '##' in report  # Markdown headers
    assert '❌' in report or 'Error' in report
    assert len(report) > 0


def test_format_report_text(fixtures_dir):
    """Test plain text report formatting"""
    validator = CodecheckValidator(fixtures_dir / 'missing_fields.yml')
    validator.validate_all(check_manifest=False, strict=False)

    report = validator.format_report(markdown=False)
    assert 'ERROR' in report
    assert len(report) > 0


def test_format_report_no_issues(fixtures_dir):
    """Test report when no issues found"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_all(check_manifest=False, strict=False)
    # Clear any warnings that might exist
    validator.issues = []

    report = validator.format_report(markdown=True)
    assert 'passed' in report.lower() or '✓' in report


def test_validation_issue_str():
    """Test ValidationIssue string representation"""
    issue = ValidationIssue(
        level='error',
        field='test_field',
        message='Test message',
        suggestion='Test suggestion'
    )

    str_repr = str(issue)
    assert 'ERROR' in str_repr
    assert 'test_field' in str_repr
    assert 'Test message' in str_repr
    assert 'Test suggestion' in str_repr


def test_report_doi_validation(fixtures_dir):
    """Test validation of report DOI/URL"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    validator.validate_yaml_syntax()
    assert validator.validate_report_doi() == True


def test_report_doi_placeholder(fixtures_dir):
    """Test detection of placeholder DOI"""
    validator = CodecheckValidator(fixtures_dir / 'placeholder_values.yml')
    validator.validate_yaml_syntax()
    validator.validate_report_doi()

    report_issues = [i for i in validator.issues if i.field == 'report']
    assert len(report_issues) > 0
    assert any('placeholder' in i.message.lower() for i in report_issues)
