---
name: standards
description: "Code standards for Go, database schemas and queries, HTTP APIs, error wrapping, logs, branches, and commit messages. Use before you write, change, or review Go code, a table or a query, an API request or response, a wrapped error, or a log line, and before you create a branch or a commit."
---

# Standards

These are the conventions that a linter cannot fully check. Before you write or review code, or create a branch or a commit, read the reference for each area the work touches. A project's own rule wins over a rule here.

| The work touches | Read |
| --- | --- |
| Go code, or a new Go dependency | [Go code](references/go/code.md) |
| A table, a column, an index, or a query | [Database](references/database.md) |
| A GORM model, a repository, or a transaction in Go | [Go database](references/go/database.md) |
| An API request or response, its validation, or an error that a client sees | [API](references/api.md) |
| A request or response struct in Go | [Go API](references/go/api.md) |
| An error that the code wraps or returns, or a log line | [Errors and logs](references/errors-and-logs.md) |
| A branch, a commit message, or a merge | [Version control](references/version-control.md) |

One task can match several rows. Read each one. If no row covers an area, no standard exists for it, so do not invent one.

## Rule for all code

Keep the public surface small. A symbol stays private to its package until a caller outside the package needs it.

## Lint

Run both commands on your change when you finish it and before a build, and fix every issue that the run reports.

```bash
golangci-lint fmt <the Go files you changed>
golangci-lint run --new-from-merge-base=<base branch> ./...
```

Give `fmt` the files you changed. Without a path, it reformats every Go file in the repository. `--new-from-merge-base` reports the issues in everything the branch changed, committed or not, and leaves old code out. A bare `golangci-lint run` reports nothing about committed work when the config sets `new-from-rev: HEAD`.

The config that `golangci-lint config path` finds decides what the linter checks. When it finds none, name [the reference config](assets/golangci.yml) in your reply as an option, and add it only when the user accepts. Never overwrite a config that exists. The reference config enforces the mechanical rules that the Go code reference lists, so the reference states them once and gives no examples.
