---
paths:
  - "**"
---

# Commit Messages

When you make changes to the repo that warrant a commit, end your turn with a suggested commit message the user can copy. Do not run `git commit` yourself unless the user asks.

- Match the style of recent commits — check `git log` if you're unsure.
- Keep the subject line short and imperative. Add a brief body only when the "why" isn't obvious from the diff.
- If the changes are trivial (fixing a typo you just introduced, reverting a stray edit) or don't touch tracked files, skip the suggestion.
- Skip the suggestion if committing now would leave the repo broken — other files no longer compile, tests that exercised the changed surface fail, or references dangle. Name what's broken and what needs fixing before a commit makes sense.
