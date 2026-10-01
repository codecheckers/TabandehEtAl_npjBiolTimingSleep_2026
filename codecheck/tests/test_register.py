"""
Tests for GitHub register issue validation
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add .codecheck to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / '.codecheck'))
from validation import CodecheckValidator


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory"""
    return Path(__file__).parent / 'fixtures'


def test_validate_register_issue_no_certificate():
    """Test register check skips when certificate is not set"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': None}

    result = validator.validate_register_issue()
    assert result == True
    assert len([i for i in validator.issues if 'register' in i.message.lower()]) == 0


def test_validate_register_issue_placeholder_certificate():
    """Test register check skips placeholder certificates"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': 'YYYY-001'}

    result = validator.validate_register_issue()
    assert result == True
    assert len([i for i in validator.issues if 'register' in i.message.lower()]) == 0


def test_validate_register_issue_invalid_format():
    """Test register check skips invalid certificate format"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': 'invalid-format'}

    result = validator.validate_register_issue()
    assert result == True
    assert len([i for i in validator.issues if 'register' in i.message.lower()]) == 0


@patch('validation.requests.get')
def test_validate_register_issue_found_open_assigned(mock_get):
    """Test successful validation when issue is found, open, and assigned"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock successful API response with matching issue
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Test Paper',
            'number': 123,
            'state': 'open',
            'assignees': [{'login': 'testuser'}],
            'html_url': 'https://github.com/codecheckers/register/issues/123'
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True
    # Should have no errors or warnings
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) == 0


@patch('validation.requests.get')
def test_validate_register_issue_not_found(mock_get):
    """Test error when no matching issue is found"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-999'}

    # Mock API response with no matching issues
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Different Paper',
            'number': 123,
            'state': 'open',
            'assignees': [{'login': 'testuser'}]
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == False

    # Should have error about missing issue
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('No issue found' in i.message for i in cert_issues)
    assert any(i.level == 'error' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_closed(mock_get):
    """Test warning when issue is closed"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock API response with closed issue
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Test Paper',
            'number': 123,
            'state': 'closed',
            'assignees': [{'login': 'testuser'}],
            'html_url': 'https://github.com/codecheckers/register/issues/123'
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True  # Still returns True, just warns

    # Should have warning about closed issue
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('closed' in i.message.lower() for i in cert_issues)
    assert any(i.level == 'warning' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_unassigned(mock_get):
    """Test warning when issue is unassigned"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock API response with unassigned issue
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Test Paper',
            'number': 123,
            'state': 'open',
            'assignees': [],
            'html_url': 'https://github.com/codecheckers/register/issues/123'
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True  # Still returns True, just warns

    # Should have warning about unassigned issue
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('unassigned' in i.message.lower() for i in cert_issues)
    assert any(i.level == 'warning' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_closed_and_unassigned(mock_get):
    """Test multiple warnings when issue is both closed and unassigned"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock API response with closed and unassigned issue
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Test Paper',
            'number': 123,
            'state': 'closed',
            'assignees': [],
            'html_url': 'https://github.com/codecheckers/register/issues/123'
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True  # Still returns True, just warns

    # Should have two warnings
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) == 2
    assert any('closed' in i.message.lower() for i in cert_issues)
    assert any('unassigned' in i.message.lower() for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_timeout(mock_get):
    """Test handling of request timeout"""
    import requests
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock timeout exception
    mock_get.side_effect = requests.exceptions.Timeout()

    result = validator.validate_register_issue()
    assert result == True  # Don't fail on timeout

    # Should have warning about timeout
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('timeout' in i.message.lower() for i in cert_issues)
    assert all(i.level == 'warning' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_network_error(mock_get):
    """Test handling of network errors"""
    import requests
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock network error
    mock_get.side_effect = requests.exceptions.RequestException('Network error')

    result = validator.validate_register_issue()
    assert result == True  # Don't fail on network errors

    # Should have warning about network error
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert any('could not check' in i.message.lower() for i in cert_issues)
    assert all(i.level == 'warning' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_register_issue_api_error(mock_get):
    """Test handling of API HTTP errors"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock API error response
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception('API Error')
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True  # Don't fail on API errors

    # Should have warning about error
    cert_issues = [i for i in validator.issues if i.field == 'certificate']
    assert len(cert_issues) > 0
    assert all(i.level == 'warning' for i in cert_issues)


@patch('validation.requests.get')
def test_validate_all_includes_register_check(mock_get, fixtures_dir):
    """Test that validate_all includes register check by default"""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'CODECHECK 2023-001: Test Paper',
            'number': 123,
            'state': 'open',
            'assignees': [{'login': 'testuser'}]
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    passed, issues = validator.validate_all(check_manifest=False, check_register=True)

    # Verify that the API was called
    mock_get.assert_called_once()
    assert 'codecheckers/register' in mock_get.call_args[0][0]


@patch('validation.requests.get')
def test_validate_all_skip_register_check(mock_get, fixtures_dir):
    """Test that register check can be disabled"""
    validator = CodecheckValidator(fixtures_dir / 'valid_codecheck.yml')
    passed, issues = validator.validate_all(check_manifest=False, check_register=False)

    # Verify that the API was NOT called
    mock_get.assert_not_called()


@patch('validation.requests.get')
def test_validate_register_issue_partial_match(mock_get):
    """Test that certificate ID must be in title (exact match)"""
    validator = CodecheckValidator('dummy.yml')
    validator.config = {'certificate': '2023-001'}

    # Mock API response with partial match (should still match)
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            'title': 'Certificate 2023-001 for XYZ',
            'number': 123,
            'state': 'open',
            'assignees': [{'login': 'testuser'}],
            'html_url': 'https://github.com/codecheckers/register/issues/123'
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = validator.validate_register_issue()
    assert result == True

    # Should have no errors
    cert_issues = [i for i in validator.issues if i.field == 'certificate' and i.level == 'error']
    assert len(cert_issues) == 0
