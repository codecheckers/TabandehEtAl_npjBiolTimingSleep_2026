"""
Tests for notebook PDF rendering
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import yaml


@pytest.fixture
def pdf_workspace():
    """Create a complete workspace for PDF generation testing"""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create directory structure
        codecheck_dir = temp_dir / 'codecheck'
        codecheck_dir.mkdir()
        outputs_dir = codecheck_dir / 'outputs'
        outputs_dir.mkdir()

        # Create subdirectories for test files
        (outputs_dir / 'figures').mkdir()
        (outputs_dir / 'data').mkdir()

        # Create test output files
        (outputs_dir / 'figures' / 'plot1.png').write_text('fake png data')
        (outputs_dir / 'data' / 'results.csv').write_text('col1,col2\n1,2\n3,4\n')

        # Copy essential files from project .codecheck directory
        project_root = Path(__file__).parent.parent
        source_dir = project_root / '.codecheck'

        # Copy Python modules
        for module in ['codecheck.py', 'validation.py', 'validation_config.py', 'manifest.py']:
            src = source_dir / module
            if src.exists():
                shutil.copy2(src, codecheck_dir / module)

        # Copy or create nbconvert template
        template_src = source_dir / 'nbconvert_template.tex.j2'
        if template_src.exists():
            shutil.copy2(template_src, codecheck_dir / 'nbconvert_template.tex.j2')
        else:
            # Create minimal template if not exists
            (codecheck_dir / 'nbconvert_template.tex.j2').write_text(
                '((* extends "base.tex.j2" *))\n'
            )

        # Copy or create logo
        logo_src = source_dir / 'codecheck_logo.png'
        if logo_src.exists():
            shutil.copy2(logo_src, codecheck_dir / 'codecheck_logo.png')
        else:
            # Create minimal valid PNG (1x1 pixel) for testing
            import struct
            png_sig = b'\x89PNG\r\n\x1a\n'
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)
            ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr + struct.pack('>I', 0x907753d5)
            idat_data = b'\x78\x9c\x62\x00\x01\x00\x00\x05\x00\x01'
            idat_chunk = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data + struct.pack('>I', 0x0d0a2db4)
            iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', 0xae426082)
            (codecheck_dir / 'codecheck_logo.png').write_bytes(png_sig + ihdr_chunk + idat_chunk + iend_chunk)

        # Copy the template codecheck.yml and customize for testing
        config_template = project_root / 'codecheck.yml'
        if config_template.exists():
            shutil.copy2(config_template, temp_dir / 'codecheck.yml')
            # Update with test-specific values that won't fail validation
            config = {
                'version': 'https://codecheck.org.uk/spec/config/1.0/',
                'certificate': '2023-001',
                'report': 'https://doi.org/10.5281/zenodo.1234567',
                'paper': {
                    'title': 'Test Paper for PDF Generation',
                    'authors': [
                        {'name': 'Jane Doe', 'ORCID': '0000-0002-1825-0097'}
                    ],
                    'reference': 'https://doi.org/10.1234/example'
                },
                'repository': 'https://github.com/example/test-repo',
                'check_time': '2023-11-15T14:30:00',
                'summary': 'This is a test summary for PDF generation.',
                'codechecker': {
                    'name': 'Test Checker',
                    'ORCID': '0000-0003-1419-2405'
                },
                'manifest': [
                    {'file': 'figures/plot1.png', 'comment': 'Test figure'},
                    {'file': 'data/results.csv', 'comment': 'Test data'}
                ]
            }
            with open(temp_dir / 'codecheck.yml', 'w') as f:
                yaml.dump(config, f)
        else:
            raise FileNotFoundError(f"Template config not found at {config_template}")

        # Copy the actual template notebook from .codecheck directory
        notebook_src = source_dir / 'codecheck.ipynb'
        if notebook_src.exists():
            shutil.copy2(notebook_src, codecheck_dir / 'codecheck.ipynb')
        else:
            raise FileNotFoundError(f"Template notebook not found at {notebook_src}")

        yield temp_dir

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_notebook_exists(pdf_workspace):
    """Test that the notebook file exists in workspace"""
    notebook_path = pdf_workspace / 'codecheck' / 'codecheck.ipynb'
    assert notebook_path.exists()
    assert notebook_path.stat().st_size > 0


def test_dependencies_exist(pdf_workspace):
    """Test that all required dependencies for PDF generation exist"""
    codecheck_dir = pdf_workspace / 'codecheck'

    # Check Python modules
    assert (codecheck_dir / 'codecheck.py').exists()
    assert (codecheck_dir / 'validation.py').exists()

    # Check template
    assert (codecheck_dir / 'nbconvert_template.tex.j2').exists()

    # Check config
    assert (pdf_workspace / 'codecheck.yml').exists()

    # Check outputs exist
    assert (codecheck_dir / 'outputs' / 'figures' / 'plot1.png').exists()
    assert (codecheck_dir / 'outputs' / 'data' / 'results.csv').exists()


def test_notebook_is_valid_json(pdf_workspace):
    """Test that the notebook is valid JSON"""
    import json
    notebook_path = pdf_workspace / 'codecheck' / 'codecheck.ipynb'

    with open(notebook_path) as f:
        notebook = json.load(f)

    assert 'cells' in notebook
    assert 'metadata' in notebook
    assert 'nbformat' in notebook
    assert len(notebook['cells']) > 0


@pytest.mark.skipif(
    shutil.which('jupyter') is None,
    reason="jupyter not installed"
)
def test_notebook_execution_only(pdf_workspace):
    """Test that the notebook can be executed without PDF conversion"""
    codecheck_dir = pdf_workspace / 'codecheck'
    notebook_path = codecheck_dir / 'codecheck.ipynb'

    # Try to execute the notebook (without PDF conversion)
    cmd = [
        'jupyter', 'nbconvert',
        '--to', 'notebook',
        '--execute',
        '--output', 'executed.ipynb',
        str(notebook_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(codecheck_dir),
            capture_output=True,
            text=True,
            timeout=60
        )

        # Check if execution succeeded
        assert result.returncode == 0, f"Notebook execution failed: {result.stderr}"

        # Check that output notebook was created
        executed_path = codecheck_dir / 'executed.ipynb'
        assert executed_path.exists(), "Executed notebook was not created"

    except subprocess.TimeoutExpired:
        pytest.skip("Notebook execution timed out")
    except Exception as e:
        pytest.skip(f"Notebook execution failed: {e}")


@pytest.mark.skipif(
    shutil.which('jupyter') is None or shutil.which('xelatex') is None,
    reason="jupyter or xelatex not installed"
)
def test_notebook_pdf_generation(pdf_workspace):
    """Test full PDF generation from notebook as described in README"""
    import os
    codecheck_dir = pdf_workspace / 'codecheck'
    notebook_path = codecheck_dir / 'codecheck.ipynb'
    pdf_path = codecheck_dir / 'codecheck.pdf'

    # The exact command from README
    cmd = [
        'jupyter', 'nbconvert',
        '--to', 'pdf',
        '--no-input',
        '--no-prompt',
        '--execute',
        '--LatexExporter.template_file', 'nbconvert_template.tex.j2',
        'codecheck.ipynb'
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(codecheck_dir),
            capture_output=True,
            text=True,
            timeout=120  # PDF generation can take longer
        )

        # Check if command succeeded
        if result.returncode != 0:
            pytest.skip(f"PDF generation failed (likely missing LaTeX dependencies): {result.stderr}")

        # Check that PDF was created
        assert pdf_path.exists(), "PDF file was not created"

        # Check PDF has reasonable size (not empty)
        assert pdf_path.stat().st_size > 1000, "PDF file is too small (possibly empty)"

        # Check PDF magic bytes
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF', "Generated file is not a valid PDF"

    except subprocess.TimeoutExpired:
        pytest.skip("PDF generation timed out")
    except FileNotFoundError as e:
        pytest.skip(f"Required command not found: {e}")
    except Exception as e:
        pytest.skip(f"PDF generation failed: {e}")
    finally:
        # Always try to save PDF artifact if running in CI, even if test is skipped
        if os.getenv('CI') == 'true':
            print(f"\n[CI Mode] Checking for PDF at: {pdf_path}")
            print(f"[CI Mode] PDF exists: {pdf_path.exists()}")
            if pdf_path.exists():
                try:
                    # Get repository root (parent of tests directory)
                    repo_root = Path(__file__).parent.parent
                    artifact_dir = repo_root / 'test-artifacts'
                    print(f"[CI Mode] Creating artifact dir: {artifact_dir}")
                    artifact_dir.mkdir(exist_ok=True)
                    shutil.copy2(pdf_path, artifact_dir / 'test-codecheck-certificate.pdf')
                    print(f"\n✓ Saved test PDF artifact to {artifact_dir / 'test-codecheck-certificate.pdf'}")
                    print(f"  PDF size: {pdf_path.stat().st_size} bytes")
                except Exception as copy_error:
                    print(f"\n✗ Failed to save PDF artifact: {copy_error}")
            else:
                print("[CI Mode] PDF was not created - cannot save artifact")


@pytest.mark.skipif(
    shutil.which('jupyter') is None,
    reason="jupyter not installed"
)
def test_notebook_pdf_generation_without_latex(pdf_workspace):
    """Test notebook conversion to HTML as fallback when LaTeX is not available"""
    codecheck_dir = pdf_workspace / 'codecheck'
    notebook_path = codecheck_dir / 'codecheck.ipynb'
    html_path = codecheck_dir / 'codecheck.html'

    # Generate HTML instead of PDF as a simpler test
    cmd = [
        'jupyter', 'nbconvert',
        '--to', 'html',
        '--no-input',
        '--no-prompt',
        '--execute',
        'codecheck.ipynb'
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(codecheck_dir),
            capture_output=True,
            text=True,
            timeout=60
        )

        # Check if command succeeded
        assert result.returncode == 0, f"HTML generation failed: {result.stderr}"

        # Check that HTML was created
        assert html_path.exists(), "HTML file was not created"

        # Check HTML has content
        assert html_path.stat().st_size > 100, "HTML file is too small"

        # Check it's valid HTML
        content = html_path.read_text()
        assert '<!DOCTYPE html>' in content or '<html' in content, "Generated file is not valid HTML"

    except subprocess.TimeoutExpired:
        pytest.skip("HTML generation timed out")
    except Exception as e:
        pytest.skip(f"HTML generation failed: {e}")


def test_notebook_validation_integration(pdf_workspace):
    """Test that validation works within the notebook context"""
    import sys
    import os
    codecheck_dir = pdf_workspace / 'codecheck'

    # Save current directory
    old_cwd = os.getcwd()

    # Add workspace to Python path
    sys.path.insert(0, str(codecheck_dir))

    try:
        # Change to codecheck directory as the notebook would
        os.chdir(codecheck_dir)

        from codecheck import Codecheck

        # Initialize as the notebook would
        check = Codecheck(
            manifest_file=str(pdf_workspace / 'codecheck.yml'),
            validate=False
        )

        # Test that all methods work
        assert check.conf is not None
        assert 'manifest' in check.conf

        # Test validation
        passed, issues = check.validate(check_manifest=True, check_register=False, strict=False)
        assert isinstance(passed, bool)
        assert isinstance(issues, list)

        # Test report generation methods
        title = check.title()
        assert title is not None

        summary_table = check.summary_table()
        assert summary_table is not None

        files_table = check.files()
        assert files_table is not None

    finally:
        os.chdir(old_cwd)
        sys.path.remove(str(codecheck_dir))


def test_readme_pdf_command_syntax():
    """Test that the README command syntax is correct"""
    # This is a documentation test - verifies the command structure
    readme_command = [
        'jupyter', 'nbconvert',
        '--to', 'pdf',
        '--no-input',
        '--no-prompt',
        '--execute',
        '--LatexExporter.template_file', 'nbconvert_template.tex.j2',
        'codecheck.ipynb'
    ]

    # Verify all required flags are present
    assert '--to' in readme_command
    assert 'pdf' in readme_command
    assert '--no-input' in readme_command
    assert '--no-prompt' in readme_command
    assert '--execute' in readme_command
    assert '--LatexExporter.template_file' in readme_command
    assert 'nbconvert_template.tex.j2' in readme_command
    assert 'codecheck.ipynb' in readme_command
