"""
Integration tests for the complete codecheck workflow
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml
import sys

# Add .codecheck to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / '.codecheck'))
from codecheck import Codecheck


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory"""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with codecheck structure"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / 'codecheck').mkdir()
    (temp_dir / 'codecheck' / 'outputs').mkdir()

    # Create a minimal valid codecheck.yml
    config = {
        'version': 'https://codecheck.org.uk/spec/config/1.0/',
        'certificate': '2023-001',
        'report': 'https://doi.org/10.5281/zenodo.1234567',
        'paper': {
            'title': 'Test Paper',
            'authors': [
                {'name': 'Jane Doe', 'ORCID': '0000-0002-1825-0097'}
            ],
            'reference': 'https://doi.org/10.1234/example'
        },
        'repository': 'https://github.com/example/repo',
        'check_time': '2023-11-15T14:30:00',
        'summary': 'Test summary',
        'codechecker': {
            'name': 'Test Checker',
            'ORCID': '0000-0003-1419-2405'
        },
        'manifest': [
            {'file': 'test.txt', 'comment': 'Test file'}
        ]
    }

    # Write config
    with open(temp_dir / 'codecheck.yml', 'w') as f:
        yaml.dump(config, f)

    # Create manifest file in outputs
    (temp_dir / 'codecheck' / 'outputs' / 'test.txt').write_text('test content')

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_codecheck_initialization_valid(fixtures_dir):
    """Test Codecheck object initialization with valid config"""
    check = Codecheck(
        manifest_file=str(fixtures_dir / 'valid_codecheck.yml'),
        validate=False
    )
    assert check.conf is not None
    assert 'manifest' in check.conf
    assert check.manifest_processor is not None


def test_codecheck_initialization_with_validation(fixtures_dir):
    """Test Codecheck initialization with validation enabled"""
    check = Codecheck(
        manifest_file=str(fixtures_dir / 'valid_codecheck.yml'),
        validate=True,
        strict=False
    )
    assert check.conf is not None


def test_codecheck_initialization_strict_mode_fails(fixtures_dir):
    """Test that strict mode raises error on invalid config"""
    with pytest.raises(ValueError) as exc_info:
        Codecheck(
            manifest_file=str(fixtures_dir / 'missing_fields.yml'),
            validate=True,
            strict=True
        )
    assert 'Validation failed' in str(exc_info.value)


def test_validate_method(fixtures_dir):
    """Test the validate() method"""
    check = Codecheck(
        manifest_file=str(fixtures_dir / 'valid_codecheck.yml'),
        validate=False
    )

    passed, issues = check.validate(check_manifest=False, check_register=False, strict=False)
    errors = [i for i in issues if i.level == 'error']
    assert len(errors) == 0


def test_validation_report_method(fixtures_dir):
    """Test the validation_report() method"""
    check = Codecheck(
        manifest_file=str(fixtures_dir / 'placeholder_values.yml'),
        validate=False
    )

    check.validate(check_manifest=False, check_register=False, strict=False)
    report = check.validation_report(markdown=False)

    assert isinstance(report, str)
    assert len(report) > 0


def test_validate_manifest_files_method(temp_workspace):
    """Test the validate_manifest_files() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    all_exist, missing = check.validate_manifest_files()
    assert all_exist == True
    assert len(missing) == 0


def test_manifest_summary_method(temp_workspace):
    """Test the manifest_summary() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    summary = check.manifest_summary()
    # Should return a Markdown object
    assert summary is not None


def test_copy_manifest_files_method(temp_workspace):
    """Test the copy_manifest_files() method"""
    # Create source file
    (temp_workspace / 'source_file.txt').write_text('source content')

    # Update manifest to point to source file
    config_path = temp_workspace / 'codecheck.yml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config['manifest'] = [{'file': 'source_file.txt'}]

    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    check = Codecheck(
        manifest_file=str(config_path),
        validate=False
    )

    result = check.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=False
    )

    # Should return Markdown report
    assert result is not None
    assert (temp_workspace / 'codecheck' / 'outputs' / 'source_file.txt').exists()


def test_title_method(temp_workspace):
    """Test the title() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    title = check.title()
    # Should return Markdown object
    assert title is not None


def test_summary_table_method(temp_workspace):
    """Test the summary_table() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    table = check.summary_table()
    # Should return Markdown object
    assert table is not None


def test_files_method(temp_workspace):
    """Test the files() method"""
    import os
    old_cwd = os.getcwd()
    try:
        # Change to codecheck directory as the notebook would
        os.chdir(temp_workspace / 'codecheck')

        check = Codecheck(
            manifest_file=str(temp_workspace / 'codecheck.yml'),
            validate=False
        )

        files_table = check.files()
        # Should return Markdown object
        assert files_table is not None
    finally:
        os.chdir(old_cwd)


def test_summary_method(temp_workspace):
    """Test the summary() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    summary = check.summary()
    # Should return Markdown object
    assert summary is not None


def test_citation_method(temp_workspace):
    """Test the citation() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    citation = check.citation()
    # Should return Markdown object
    assert citation is not None


def test_about_codecheck_method(temp_workspace):
    """Test the about_codecheck() method"""
    check = Codecheck(
        manifest_file=str(temp_workspace / 'codecheck.yml'),
        validate=False
    )

    about = check.about_codecheck()
    # Should return Markdown object
    assert about is not None


def test_backward_compatibility(fixtures_dir):
    """Test that existing code without validation still works"""
    # Old usage pattern without validation parameters
    check = Codecheck(manifest_file=str(fixtures_dir / 'valid_codecheck.yml'))
    assert check.conf is not None

    # All original methods should still work
    assert check.title() is not None
    assert check.summary() is not None
    assert check.about_codecheck() is not None
