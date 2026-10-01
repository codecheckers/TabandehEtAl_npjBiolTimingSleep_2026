"""
Helper module to prepare a CODECHECK report
https://codecheck.org.uk
"""
from datetime import datetime
import os.path as op
from pathlib import Path
import yaml
from IPython.display import Markdown
import pandas as pd
import session_info2 as si

from validation import CodecheckValidator
from manifest import ManifestProcessor


def name_orcid(entry):
    """Helper function for Name + ORCID"""
    if 'ORCID' in entry:
        return f"{entry['name']} (ORCID: {entry['ORCID']})"
    else:
        return entry['name']

def multiple_name_orcid(entries):
    """Helper function for multiple people to return their Name + ORCID"""
    return f"{', '.join([name_orcid(a) for a in entries])}"

def multiple_name(entries):
    """Helper function for multiple people to return their Name + ORCID"""
    return f"{', '.join([a['name'] for a in entries])}"

def url_link(url):
    """Helper function to create Markdown links for the full URL with the protocol in front."""
    return f"[{url}]({url})"

def short_link(url):
    """Helper function to create Markdown links for the short URL without the protocol in front."""
    return f"[{url.split('://')[1]}]({url})"

class Codecheck:
    """
    Object that generates automatic Markdown/LaTeX output for inclusion in a jupyter notebook,
    based on a `codecheck.yml` file.
    """

    def __init__(self, manifest_file=op.join("..", "codecheck.yml"),
                 validate=False, strict=False):
        """
        Create new `Codecheck` object with optional validation.

        Parameters
        ----------
        manifest_file : str, optional
            The path/name of the `codecheck.yml` file. Defaults to `../codecheck.yml`.
        validate : bool, optional
            Whether to run validation on initialization. Defaults to False.
            Set to True to validate configuration before processing.
        strict : bool, optional
            If True, raises error on validation failure (when validate=True).
            If False, only warnings are issued. Defaults to False.
        """
        self.manifest_file = manifest_file
        self.validator = CodecheckValidator(manifest_file)
        self.manifest_processor = None

        # Optionally validate on initialization
        if validate:
            passed, issues = self.validator.validate_all(
                check_manifest=False,  # Don't check files until explicitly requested
                strict=strict
            )
            if not passed and strict:
                raise ValueError(
                    f"Validation failed for {manifest_file}:\n{self.validator.format_report(markdown=False)}"
                )

        with open(manifest_file) as f:
            self.conf = yaml.safe_load(f)

        # Initialize manifest processor if manifest exists
        if self.conf and 'manifest' in self.conf:
            base_dir = Path(manifest_file).parent
            self.manifest_processor = ManifestProcessor(
                self.conf['manifest'],
                base_dir
            )

    def get_formatted_summary(self):
        """Remove additional whitespaces and newline characters from the summary."""
        return self.conf['summary'].strip().replace("\n", " ")

    def title(self):
        """
        Markdown title with the certificate number, the doi of the report, and the CODECHECK
        logo. The logo is expected to be stored as `codecheck_logo.png` in the current
        directory.
        """
        return Markdown(
            f"""# CODECHECK certificate {self.conf['certificate']}
## {url_link(self.conf['report'])}
[![CODECHECK logo](codecheck_logo.svg)](https://codecheck.org.uk)"""
        )

    def summary_table(self):
        """
        Markdown table with the general information (title, authors, etc.) from the `codecheck.yml`
        file.
        """
        summary_header = """
Item | Value
:--- | :----
"""
        summary_rows = [
            f"Title | *{self.conf['paper']['title']}*",
            f"Author(s) | {multiple_name_orcid(self.conf['paper']['authors'])}",
            f"Reference | {url_link(self.conf['paper']['reference'])}",
            f"Repository | {url_link(self.conf['repository'])}",
            f"Codechecker(s) | {multiple_name_orcid(self.conf['codechecker'])}",
            f"Date of check | {datetime.fromisoformat(self.conf['check_time']).date()}",
            f"Summary | {self.get_formatted_summary()}",
        ]
        return Markdown(summary_header + "\n".join(summary_rows))

    def files(self, remove_dirname=True):
        """
        Markdown table with the name, comment and file size of all files in the manifest.
        Only shows the file name without the directory by default.
        
        Parameters
        ----------
        remove_dirname: bool
            Whether to remove the directory names from the file names in the `file` column.
            Defaults to `True`.
        """
        # Note that the &nbsp; below are used to work around the fact that pandoc seems to
        # calculate the column width for the LaTeX output based on the length of the headers
        files_header = """
File | Comment | Size (b)
:--------------------- | :----------------------------------- | -------:
"""
        files_rows = [
            (
                "`"
                + (op.basename(entry["file"]) if remove_dirname else entry["file"])
                + "` | "
                + entry.get("comment", "")
                + " | "
                + str(op.getsize(op.join("outputs", entry["file"])))
            )
            for entry in self.conf["manifest"]
        ]
        return Markdown(files_header + "\n".join(files_rows))

    def summary(self):
        """
        Markdown rendering of the `summary` field in `codecheck.yml`.
        """
        return Markdown(self.get_formatted_summary())

    def citation(self):
        """
        Markdown citation for this CODECHECK.
        """
        return Markdown(
            f"{multiple_name(self.conf['codechecker'])} "
            f"({datetime.fromisoformat(self.conf['check_time']).year}). "
            f"CODECHECK Certificate {self.conf['certificate']}. "
            f"Zenodo. {url_link(self.conf['report'])}"
        )

    def about_codecheck(self):
        """
        Markdown boilerplate text about what a CODECHECK is.
        """
        return Markdown(
            """
This certificate confirms that the codechecker could independently reproduce the results of a computational analysis given the data and code from a third party. A CODECHECK does not check whether the original computation analysis is correct. However, as all materials required for the reproduction are freely availableby following the links in this document, the reader can then study for themselves the code and data."""
        )
    
    def session_info(self):
        """
        Markdown formatted session info
        """
        return Markdown(f"""```bash
{si.session_info(os=True, cpu=True, gpu=True, dependencies=True)}
```
"""
)

    def csv_files(self, **kwds):
        """
        Markdown summary of all `.csv` files in the manifest. Prints the output of Panda's `describe` function (number of entries, mean, quantiles, etc.)
        for each column.
        
        Parameters
        ----------
        **kwds
            Additional arguments (e.g. index_col=False) that will be handed over to Panda's `read_csv` function.
        """
        full_markdown = []
        for entry in self.conf["manifest"]:
            fname = entry["file"]
            if not fname.endswith(".csv"):
                continue
            comment = entry.get("comment", None)
            df = pd.read_csv(op.join("outputs", fname), **kwds)
            markdown = f"""### `{fname}`
{('Author comment: *' + comment + '*') if comment else ' '}

**Column summary statistics:**

{df.describe().transpose().to_markdown(floatfmt=('.0f', '.0f', '.4f', '.4f', '.4f', '.4f', '.4f', '.4f', '.4f'))}
"""
            full_markdown.append(markdown)

        return Markdown("\n\n".join(full_markdown))

    def latex_figures(self, extensions=(".pdf", ".eps")):
        """
        LaTeX output (therefore only useful for the LaTeX/PDF version of the notebook) of all the figures in the
        manifest.
        
        Parameters
        ----------
        extensions : sequence
            A list/tuple of extensions (in lower case) that should be handled by this function.
            Defaults to `('.pdf', '.eps')`.
        """
        full_text = []
        # Figures (only PDF versions)
        for entry in self.conf["manifest"]:
            fname = entry["file"]
            if not op.splitext(fname)[1].lower() in extensions:
                continue
            comment = entry["comment"]
            heading = f"""### `{fname}`
{('Author comment: *' + comment + '*') if comment else ' '}"""
            full_text.extend(
                [
                    heading + r"![" + r"Author comment: " + comment + r"]" + r"(outputs/" + fname + r")",
                    "",
                ]
            )
        return Markdown("\n".join(full_text))

    def validate(self, check_manifest=True, check_register=True, strict=False):
        """
        Run validation checks on the codecheck.yml file.

        Parameters
        ----------
        check_manifest : bool, optional
            Whether to check if manifest files exist in outputs/. Defaults to True.
        check_register : bool, optional
            Whether to check for GitHub register issue. Defaults to True.
        strict : bool, optional
            If True, warnings are treated as failures. Defaults to False.

        Returns
        -------
        tuple
            (passed: bool, issues: List[ValidationIssue])
        """
        return self.validator.validate_all(
            check_manifest=check_manifest,
            check_register=check_register,
            strict=strict
        )

    def validation_report(self, markdown=True):
        """
        Display validation report.

        Parameters
        ----------
        markdown : bool, optional
            If True, return Markdown formatted report. Otherwise plain text.
            Defaults to True.

        Returns
        -------
        Markdown or str
            Formatted validation report
        """
        report = self.validator.format_report(markdown=markdown)
        if markdown:
            return Markdown(report)
        else:
            return report

    def validate_manifest_files(self):
        """
        Validate that all manifest files exist in outputs/ directory.

        Returns
        -------
        tuple
            (all_exist: bool, missing_files: List[str])
        """
        if not self.manifest_processor:
            return False, []
        return self.manifest_processor.validate_output_files_exist()

    def manifest_summary(self):
        """
        Get summary statistics about the manifest.

        Returns
        -------
        Markdown
            Formatted manifest summary with file counts, sizes, and types
        """
        if not self.manifest_processor:
            return Markdown("*No manifest found*")

        summary = self.manifest_processor.get_manifest_summary()

        markdown = f"""### Manifest Summary

- **Total files**: {summary['total_files']}
- **Total size**: {summary['total_size']:,} bytes ({summary['total_size_mb']} MB)
- **Files with comments**: {summary['has_comments']}

**File types:**
"""
        for ext, count in sorted(summary['file_types'].items()):
            ext_display = ext if ext else "(no extension)"
            markdown += f"- `{ext_display}`: {count} file(s)\n"

        return Markdown(markdown)

    def copy_manifest_files(self, source_dir=None, keep_full_path=True,
                          overwrite=True, dry_run=False):
        """
        Copy manifest files from source to outputs directory.

        Parameters
        ----------
        source_dir : str or Path, optional
            Source directory containing files. Defaults to parent of config file.
        keep_full_path : bool, optional
            If True, maintain directory structure. If False, flatten. Defaults to True.
        overwrite : bool, optional
            If True, overwrite existing files. Defaults to True.
        dry_run : bool, optional
            If True, don't actually copy files. Defaults to False.

        Returns
        -------
        Markdown
            Report of copied files
        """
        if not self.manifest_processor:
            return Markdown("*No manifest found*")

        if source_dir is None:
            source_dir = Path(self.manifest_file).parent

        copied = self.manifest_processor.copy_manifest_files(
            source_dir=source_dir,
            keep_full_path=keep_full_path,
            overwrite=overwrite,
            dry_run=dry_run
        )

        if not copied:
            return Markdown("*No files copied*")

        markdown = f"### Copied {len(copied)} file(s)\n\n"
        for entry in copied:
            size_kb = entry['size'] / 1024
            markdown += f"- `{entry['file']}` ({size_kb:.1f} KB)\n"

        return Markdown(markdown)
    
    def acknowledge_sponsors(self):
        """The sponsoring acknowledgement."""
        return Markdown("CODECHECK is financially supported by the Mozilla foundation.")
