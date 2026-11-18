---
name: standards
description: "Development standards for code, database schemas and queries, HTTP APIs, error handling, logs, branches, and commit messages. Use before you write, change, or review code, a table or a query, an API request or response, error handling, or a log line, and before you create a branch or a commit."
---

# Standards

These are the conventions that a linter cannot fully check. Before you write or review code, or create a branch or a commit, read every reference that applies to the work. A project's own rule wins over a rule here.

## References

These apply in any programming language.

- [Database](references/database.md)
- [Errors and logs](references/errors-and-logs.md)
- [Version control](references/version-control.md)

Each language has its own folder. For any work in a language, list its folder and read every file that applies. Always read its `code.md`, which also names the formatter and the linter of the language. Run them on your change when you finish it and before a build, and fix every issue that the run reports.

- Go: `references/go/`

If no reference covers something, no standard exists for it, so do not invent one.

## Rule for all code

Keep the public surface small. A symbol stays private to its package or module until a caller outside it needs the symbol.
