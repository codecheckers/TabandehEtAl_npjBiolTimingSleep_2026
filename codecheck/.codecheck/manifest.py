"""
Manifest processing module for CODECHECK certificates
https://codecheck.org.uk
"""
from pathlib import Path
import shutil
from typing import List, Dict, Tuple, Optional


class ManifestProcessor:
    """
    Processor for handling manifest files in CODECHECK certificates.

    Handles file validation, copying, and size tracking for manifest entries.
    """

    def __init__(self, manifest: List[Dict], base_dir: Path):
        """
        Initialize manifest processor.

        Parameters
        ----------
        manifest : list of dict
            Manifest entries from codecheck.yml
        base_dir : Path
            Base directory (typically repository root)
        """
        self.manifest = manifest
        self.base_dir = Path(base_dir)
        self.outputs_dir = self.base_dir / 'codecheck' / 'outputs'

    def validate_files_exist(self, source_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Check if all manifest files exist in the source directory.

        Parameters
        ----------
        source_dir : Path, optional
            Directory to check for files. Defaults to base_dir.

        Returns
        -------
        tuple
            (all_exist: bool, missing_files: List[str])
        """
        if source_dir is None:
            source_dir = self.base_dir

        missing = []
        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            if not file_path:
                continue

            full_path = Path(source_dir) / file_path
            if not full_path.exists():
                missing.append(file_path)

        return len(missing) == 0, missing

    def validate_output_files_exist(self) -> Tuple[bool, List[str]]:
        """
        Check if all manifest files exist in the outputs directory.

        Returns
        -------
        tuple
            (all_exist: bool, missing_files: List[str])
        """
        if not self.outputs_dir.exists():
            return False, [entry.get('file', '') for entry in self.manifest if entry.get('file')]

        missing = []
        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            if not file_path:
                continue

            full_path = self.outputs_dir / file_path
            if not full_path.exists():
                missing.append(file_path)

        return len(missing) == 0, missing

    def get_file_sizes(self, use_outputs: bool = True) -> Dict[str, int]:
        """
        Get actual file sizes for all manifest files.

        Parameters
        ----------
        use_outputs : bool, optional
            If True, check files in outputs/ directory.
            If False, check in base directory. Defaults to True.

        Returns
        -------
        dict
            Mapping of file paths to sizes in bytes
        """
        sizes = {}
        base = self.outputs_dir if use_outputs else self.base_dir

        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            if not file_path:
                continue

            full_path = base / file_path
            if full_path.exists():
                sizes[file_path] = full_path.stat().st_size

        return sizes

    def compare_sizes(self) -> List[Dict]:
        """
        Compare declared sizes in manifest with actual file sizes.

        Returns
        -------
        list of dict
            Entries with size mismatches: [{file, declared, actual, difference}, ...]
        """
        mismatches = []
        actual_sizes = self.get_file_sizes(use_outputs=True)

        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            declared_size = entry.get('size')

            if not file_path or declared_size is None:
                continue

            actual_size = actual_sizes.get(file_path)
            if actual_size is not None and actual_size != declared_size:
                mismatches.append({
                    'file': file_path,
                    'declared': declared_size,
                    'actual': actual_size,
                    'difference': actual_size - declared_size
                })

        return mismatches

    def copy_manifest_files(self,
                           source_dir: Optional[Path] = None,
                           keep_full_path: bool = True,
                           overwrite: bool = True,
                           dry_run: bool = False) -> List[Dict]:
        """
        Copy manifest files to outputs directory.

        Parameters
        ----------
        source_dir : Path, optional
            Source directory containing files. Defaults to base_dir.
        keep_full_path : bool, optional
            If True, maintain directory structure in outputs.
            If False, flatten all files to outputs root. Defaults to True.
        overwrite : bool, optional
            If True, overwrite existing files. Defaults to True.
        dry_run : bool, optional
            If True, don't actually copy files. Defaults to False.

        Returns
        -------
        list of dict
            Information about copied files: [{file, source, destination, size}, ...]
        """
        if source_dir is None:
            source_dir = self.base_dir

        source_dir = Path(source_dir)
        copied = []

        # Create outputs directory if it doesn't exist
        if not dry_run and not self.outputs_dir.exists():
            self.outputs_dir.mkdir(parents=True, exist_ok=True)

        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file')
            if not file_path:
                continue

            src = source_dir / file_path

            if not src.exists():
                # Skip missing files (should be caught by validation)
                continue

            # Determine destination path
            if keep_full_path:
                dst = self.outputs_dir / file_path
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
            else:
                dst = self.outputs_dir / Path(file_path).name

            # Check if we should overwrite
            if dst.exists() and not overwrite:
                continue

            # Copy the file
            if not dry_run:
                shutil.copy2(src, dst)

            copied.append({
                'file': file_path,
                'source': str(src),
                'destination': str(dst),
                'size': src.stat().st_size,
                'comment': entry.get('comment', '')
            })

        return copied

    def get_manifest_summary(self) -> Dict:
        """
        Get summary statistics about the manifest.

        Returns
        -------
        dict
            Summary with file counts, total size, etc.
        """
        total_files = len(self.manifest)
        sizes = self.get_file_sizes(use_outputs=True)
        total_size = sum(sizes.values())

        # Count file types
        extensions = {}
        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file', '')
            ext = Path(file_path).suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_types': extensions,
            'has_comments': sum(1 for e in self.manifest if e.get('comment'))
        }

    def validate_paths(self) -> Tuple[bool, List[str]]:
        """
        Validate that all file paths are safe (no path traversal).

        Returns
        -------
        tuple
            (all_safe: bool, unsafe_paths: List[str])
        """
        unsafe = []
        for entry in self.manifest:
            if not isinstance(entry, dict):
                continue
            file_path = entry.get('file', '')

            # Check for path traversal attempts
            if '..' in file_path or file_path.startswith('/'):
                unsafe.append(file_path)
                continue

            # Ensure normalized path doesn't escape
            normalized = (self.outputs_dir / file_path).resolve()
            try:
                normalized.relative_to(self.outputs_dir.resolve())
            except ValueError:
                # Path escapes outputs directory
                unsafe.append(file_path)

        return len(unsafe) == 0, unsafe
