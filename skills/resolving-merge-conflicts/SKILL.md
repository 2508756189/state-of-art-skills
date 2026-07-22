---
name: resolving-merge-conflicts
description: "Use when you need to resolve an in-progress git merge/rebase conflict."
license: MIT
---

## Source And Curation

Source: https://github.com/mattpocock/skills/tree/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/resolving-merge-conflicts

This market entry keeps the upstream conflict-analysis workflow but preserves user control over aborting, staging, and committing.

1. **See the current state** of the merge/rebase. Check git history, and the conflicting files.

2. **Find the primary sources** for each conflict. Understand deeply why each change was made, and what the original intent was. Read the commit messages, check the PRs, check original issues/tickets.

3. **Resolve each hunk.** Preserve both intents where possible. Where incompatible, pick the one matching the merge's stated goal and note the trade-off. Do **not** invent new behaviour. Do not run `--abort` unless the user explicitly asks to abandon the operation.

4. Discover the project's **automated checks** and run them — typically typecheck, then tests, then format. Fix anything the merge broke.

5. **Finish the merge/rebase.** Stage only the resolved files and follow the repository's normal completion flow. Create a commit only when the user or the active merge/rebase workflow requires it. If rebasing, continue only while the operation remains in scope.
