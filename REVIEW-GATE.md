# Review gate

This branch must not be merged until all of the following hold on the current head commit:

1. The implementation is checked into the reviewed tree; no runtime feature may depend on a self-modifying workflow or one-shot generator.
2. The complete test workflow succeeds.
3. Every inline review thread is resolved by a code change or shown obsolete by the current diff.
4. A fresh `@codex review` on the current head completes with no findings.
5. Any new finding restarts the fix, test, and review cycle.

This file records the repository policy requested after the premature merges of PRs #2 and #3.
