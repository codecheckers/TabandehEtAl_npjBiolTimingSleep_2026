"""
Tests for manifest processing module
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# Add .codecheck to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / '.codecheck'))
from manifest import ManifestProcessor


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory"""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing file operations"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / 'codecheck' / 'outputs').mkdir(parents=True)
    (temp_dir / 'figures').mkdir()
    (temp_dir / 'data').mkdir()

    # Create some test files
    (temp_dir / 'figures' / 'plot1.png').write_text('fake image data')
    (temp_dir / 'data' / 'results.csv').write_text('col1,col2\n1,2\n3,4')

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_manifest_processor_initialization():
    """Test ManifestProcessor initialization"""
    manifest = [
        {'file': 'test.txt', 'comment': 'Test file'}
    ]
    processor = ManifestProcessor(manifest, Path('/tmp'))

    assert processor.manifest == manifest
    assert processor.base_dir == Path('/tmp')
    assert processor.outputs_dir == Path('/tmp/codecheck/outputs')


def test_validate_files_exist_all_present(temp_workspace):
    """Test validation when all files exist"""
    manifest = [
        {'file': 'figures/plot1.png'},
        {'file': 'data/results.csv'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_exist, missing = processor.validate_files_exist(source_dir=temp_workspace)
    assert all_exist == True
    assert len(missing) == 0


def test_validate_files_exist_some_missing(temp_workspace):
    """Test validation when some files are missing"""
    manifest = [
        {'file': 'figures/plot1.png'},
        {'file': 'data/results.csv'},
        {'file': 'nonexistent.txt'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_exist, missing = processor.validate_files_exist(source_dir=temp_workspace)
    assert all_exist == False
    assert 'nonexistent.txt' in missing
    assert len(missing) == 1


def test_validate_output_files_exist(temp_workspace):
    """Test validation of files in outputs directory"""
    # Copy files to outputs
    shutil.copy2(
        temp_workspace / 'figures' / 'plot1.png',
        temp_workspace / 'codecheck' / 'outputs' / 'plot1.png'
    )

    manifest = [
        {'file': 'plot1.png'},
        {'file': 'missing.txt'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_exist, missing = processor.validate_output_files_exist()
    assert all_exist == False
    assert 'missing.txt' in missing


def test_get_file_sizes_from_outputs(temp_workspace):
    """Test getting file sizes from outputs directory"""
    # Copy files to outputs
    (temp_workspace / 'codecheck' / 'outputs' / 'figures').mkdir()
    shutil.copy2(
        temp_workspace / 'figures' / 'plot1.png',
        temp_workspace / 'codecheck' / 'outputs' / 'figures' / 'plot1.png'
    )

    manifest = [
        {'file': 'figures/plot1.png'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    sizes = processor.get_file_sizes(use_outputs=True)
    assert 'figures/plot1.png' in sizes
    assert sizes['figures/plot1.png'] > 0


def test_get_file_sizes_from_source(temp_workspace):
    """Test getting file sizes from source directory"""
    manifest = [
        {'file': 'figures/plot1.png'},
        {'file': 'data/results.csv'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    sizes = processor.get_file_sizes(use_outputs=False)
    assert 'figures/plot1.png' in sizes
    assert 'data/results.csv' in sizes
    assert all(size > 0 for size in sizes.values())


def test_copy_manifest_files_keep_full_path(temp_workspace):
    """Test copying files while maintaining directory structure"""
    manifest = [
        {'file': 'figures/plot1.png', 'comment': 'Test figure'},
        {'file': 'data/results.csv', 'comment': 'Test data'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    copied = processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=True,
        overwrite=True
    )

    assert len(copied) == 2
    assert (temp_workspace / 'codecheck' / 'outputs' / 'figures' / 'plot1.png').exists()
    assert (temp_workspace / 'codecheck' / 'outputs' / 'data' / 'results.csv').exists()


def test_copy_manifest_files_flatten(temp_workspace):
    """Test copying files with flattened structure"""
    manifest = [
        {'file': 'figures/plot1.png'},
        {'file': 'data/results.csv'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    copied = processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=False,
        overwrite=True
    )

    assert len(copied) == 2
    assert (temp_workspace / 'codecheck' / 'outputs' / 'plot1.png').exists()
    assert (temp_workspace / 'codecheck' / 'outputs' / 'results.csv').exists()


def test_copy_manifest_files_no_overwrite(temp_workspace):
    """Test that existing files are not overwritten when overwrite=False"""
    manifest = [
        {'file': 'figures/plot1.png'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    # First copy
    processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=True,
        overwrite=True
    )

    # Modify the copied file
    output_file = temp_workspace / 'codecheck' / 'outputs' / 'figures' / 'plot1.png'
    original_content = output_file.read_text()
    output_file.write_text('modified content')

    # Try to copy again with overwrite=False
    processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=True,
        overwrite=False
    )

    # File should still have modified content
    assert output_file.read_text() == 'modified content'


def test_copy_manifest_files_dry_run(temp_workspace):
    """Test dry run mode doesn't actually copy files"""
    manifest = [
        {'file': 'figures/plot1.png'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    copied = processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=True,
        dry_run=True
    )

    # Should return info but not copy
    assert len(copied) == 1
    assert not (temp_workspace / 'codecheck' / 'outputs' / 'figures' / 'plot1.png').exists()


def test_get_manifest_summary(temp_workspace):
    """Test getting manifest summary statistics"""
    manifest = [
        {'file': 'figures/plot1.png', 'comment': 'Test figure'},
        {'file': 'data/results.csv'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    # Copy files to outputs first
    processor.copy_manifest_files(
        source_dir=temp_workspace,
        keep_full_path=True
    )

    summary = processor.get_manifest_summary()

    assert summary['total_files'] == 2
    assert summary['total_size'] > 0
    assert summary['total_size_mb'] >= 0
    assert '.png' in summary['file_types']
    assert '.csv' in summary['file_types']
    assert summary['has_comments'] == 1  # Only one file has a comment


def test_validate_paths_safe(temp_workspace):
    """Test validation of safe file paths"""
    manifest = [
        {'file': 'figures/plot1.png'},
        {'file': 'data/results.csv'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_safe, unsafe = processor.validate_paths()
    assert all_safe == True
    assert len(unsafe) == 0


def test_validate_paths_path_traversal(temp_workspace):
    """Test detection of path traversal attempts"""
    manifest = [
        {'file': '../../../etc/passwd'},
        {'file': 'data/../../../secret.txt'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_safe, unsafe = processor.validate_paths()
    assert all_safe == False
    assert len(unsafe) > 0


def test_validate_paths_absolute_path(temp_workspace):
    """Test detection of absolute paths"""
    manifest = [
        {'file': '/etc/passwd'}
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    all_safe, unsafe = processor.validate_paths()
    assert all_safe == False
    assert '/etc/passwd' in unsafe


def test_compare_sizes(temp_workspace):
    """Test comparison of declared vs actual file sizes"""
    manifest = [
        {'file': 'figures/plot1.png', 'size': 100},  # Wrong size
        {'file': 'data/results.csv', 'size': 1000}   # Wrong size
    ]
    processor = ManifestProcessor(manifest, temp_workspace)

    # Copy files to outputs
    processor.copy_manifest_files(source_dir=temp_workspace, keep_full_path=True)

    mismatches = processor.compare_sizes()

    # Both files should have size mismatches
    assert len(mismatches) == 2
    for mismatch in mismatches:
        assert 'file' in mismatch
        assert 'declared' in mismatch
        assert 'actual' in mismatch
        assert 'difference' in mismatch


def test_copy_manifest_files_creates_directories(temp_workspace):
    """Test that copying creates necessary subdirectories"""
    manifest = [
        {'file': 'deep/nested/dir/file.txt'}
    ]

    # Create source file
    source_dir = temp_workspace / 'source'
    source_dir.mkdir()
    (source_dir / 'deep' / 'nested' / 'dir').mkdir(parents=True)
    (source_dir / 'deep' / 'nested' / 'dir' / 'file.txt').write_text('test')

    processor = ManifestProcessor(manifest, temp_workspace)

    copied = processor.copy_manifest_files(
        source_dir=source_dir,
        keep_full_path=True
    )

    assert len(copied) == 1
    assert (temp_workspace / 'codecheck' / 'outputs' / 'deep' / 'nested' / 'dir' / 'file.txt').exists()
