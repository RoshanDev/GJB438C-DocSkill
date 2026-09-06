# Iterative review process

A corrective pull request remains unmerged while any current-head CI check fails, any inline review thread remains unresolved, or the latest Codex review reports a finding. Each finding requires a direct source change, a regression test, a new CI run, and a fresh Codex review on the new head. Only a clean latest-head review permits merging.
