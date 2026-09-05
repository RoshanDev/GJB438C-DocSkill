# Codex review findings

The corrective pull request is not eligible for merge until a fresh Codex review on its latest head reports no findings.

The implementation must directly address:

- direct runtime materialisation instead of branch-mutating workflows;
- generator indentation and literal-regex replacement failures;
- suite baseline availability derived only from successfully audited documents;
- staging of DOCX and both reports before publishing a release output set;
- regression tests covering each failure mode.

Any new review finding reopens this checklist and blocks merge.
