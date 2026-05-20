---
name: fix-github-issues
description: Use when asked to work on open GitHub issues for this project - pulls latest, reads issues, implements a fix with TDD, and submits a PR
---

# Fix GitHub Issues

## Overview

Pull latest, read open issues, implement a fix, submit a PR. One issue per run.

## gh CLI

`gh` may not be on PATH in tool subprocess environments. Use the full path:

```powershell
$GH = "C:\Program Files\GitHub CLI\gh.exe"
& $GH issue list --repo thopper21/TNFamily
& $GH issue view <number> --repo thopper21/TNFamily
& $GH pr create --repo thopper21/TNFamily --title "..." --body "..."
```

**Never fall back to WebFetch for GitHub data.** Use `gh` exclusively.

## Workflow

```dot
digraph fix_issues {
    "git pull origin main" [shape=box];
    "List open issues (gh issue list)" [shape=box];
    "Any open issues?" [shape=diamond];
    "Report: no open issues" [shape=box];
    "Pick one issue" [shape=box];
    "Read full issue (gh issue view)" [shape=box];
    "Scope clear?" [shape=diamond];
    "Ask clarifying questions" [shape=box];
    "Create feature branch" [shape=box];
    "Implement fix (TDD)" [shape=box];
    "Run tests (python -m pytest)" [shape=box];
    "Tests pass?" [shape=diamond];
    "Fix failures" [shape=box];
    "Submit PR (gh pr create)" [shape=box];

    "git pull origin main" -> "List open issues (gh issue list)";
    "List open issues (gh issue list)" -> "Any open issues?";
    "Any open issues?" -> "Report: no open issues" [label="no"];
    "Any open issues?" -> "Pick one issue" [label="yes"];
    "Pick one issue" -> "Read full issue (gh issue view)";
    "Read full issue (gh issue view)" -> "Scope clear?";
    "Scope clear?" -> "Ask clarifying questions" [label="no"];
    "Ask clarifying questions" -> "Create feature branch";
    "Scope clear?" -> "Create feature branch" [label="yes"];
    "Create feature branch" -> "Implement fix (TDD)";
    "Implement fix (TDD)" -> "Run tests (python -m pytest)";
    "Run tests (python -m pytest)" -> "Tests pass?";
    "Tests pass?" -> "Fix failures" [label="no"];
    "Fix failures" -> "Run tests (python -m pytest)";
    "Tests pass?" -> "Submit PR (gh pr create)" [label="yes"];
}
```

## Picking an Issue

Pick the issue that is:
- Most clearly scoped (fewest unknowns)
- Not dependent on another open issue
- Or whichever the user specifies

If the issue description is ambiguous, **ask before starting work**.

## PR Body

Always reference the issue so GitHub auto-closes it on merge:

```
gh pr create --title "fix: ..." --body "$(cat <<'EOF'
## Summary
- <what changed>

## Test Plan
- [ ] All tests pass (python -m pytest)
- [ ] Manually verified in browser

Closes #<issue-number>
EOF
)"
```

## Required Skills

- **superpowers:test-driven-development** — write tests first for every change
- **superpowers:brainstorming** — if scope needs design discussion before implementation

## Project Notes

- Tests: `python -m pytest` (in-memory SQLite, no setup needed)
- Single test: `python -m pytest tests/test_grocery.py::test_name -v`
- Update `README.md` if the change adds a new blueprint, model, or route pattern
