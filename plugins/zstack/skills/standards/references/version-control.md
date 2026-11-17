# Version control

The project's AGENTS.md or CLAUDE.md decides these conventions. Use the rules below when it names none.

## Branches

Start a branch from the latest `release` branch when the repository has one, and from the default branch when it does not.

Name the branch `{name}/{type}-{description}`, all lowercase, such as `zhangsan/feature-add-rate-limit`.

- `name` is the developer's identifier.
- `type` is `feature`, `fix`, `hotfix` for an urgent fix to production, `refactor`, or `chore`. When none of them fits, use the commit type.
- `description` joins its words with `-`.

## Commit messages

Write commit messages in English, in the format of [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

- The scope names the affected module, package, service, command, or config domain. Keep it short and stable.
- The subject says what the commit did. A reader must understand the main change without the diff, so do not write a general subject such as `update`, `fix bug`, or `change code`.
- Write a body when the reason for the change, its effect on behavior or compatibility, a migration step, a config change, or a risk is not obvious.
- When a commit covers several unrelated intents, split it.
- A breaking change gets `!` after the type and a `BREAKING CHANGE` footer that tells callers what to do.

```text
feat(api)!: change the response structure of the account query

The balance field changes from balance to available_balance.

BREAKING CHANGE: the response no longer has the balance field. Callers must read available_balance.
```

## Merging

Merge with a merge commit by default, which keeps the full history.

Squash when the commits on the branch served only the development process and are not worth keeping one by one for audit or rollback. That covers temporary fixes, repeated adjustments, commits such as `fix review comments`, `update`, or `wip`, and several commits that make up one change that cannot be split.
