# zstack in Claude Code

zstack skills use their own names for tools, subagent fields, models, and paths. In Claude Code, read this file once per session, then map each name in a skill with the tables below. `<zstack>` means the folder that holds `skills/` and `docs/`. If a subagent field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| zstack | Claude Code |
| --- | --- |
| `Task` | `Agent` |
| `AskQuestion` | `AskUserQuestion`. In `-p` mode it is absent, so ask in plain text. |
| Open a todolist | Use the session's task-list tool, `TaskCreate` with `TaskUpdate`, or `TodoWrite`. Otherwise keep the list in your reply and update it at each phase. |
| Run another zstack skill (`/name` or "the **name** skill") | `Read` `<zstack>/skills/<name>/SKILL.md` and follow it. The `Skill` tool refuses most zstack skills. When you tell the user to type it, write `/zstack:<name>`. |
| `Grep`, `Glob` | `Bash` with `rg` when the session has no `Grep` or `Glob`. |
| The `create-skill` skill | A skill-authoring skill that the session lists, such as `skill-creator`. If the session lists none, follow the rest of the step without it and say so. |

## Subagent fields

| zstack | Claude Code |
| --- | --- |
| `subagent_type: generalPurpose` | `subagent_type: "general-purpose"` |
| `zen-agent`, `comment-sicko` | `zstack:zen-agent`, `zstack:comment-sicko` |
| `readonly: true` | `subagent_type: "Explore"`. It keeps `Bash`, so the brief also says "do not edit files", and you check `git status` afterward. |
| `readonly: false` | `general-purpose`. It keeps the session's MCP servers. |
| `environment: "cloud"` | `isolation: "worktree"`. Name the branch or commit the worker checks out. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first. |
| `run_in_background: true` | Omit. Subagents run in the background by default and notify you when they finish. |
| `resume` | Spawn a new agent and paste the earlier result into its brief. |
| `file_attachments` | List the paths in the brief. |

## Models

| zstack | Claude Code |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, such as `claude-opus-5-5-xhigh` | `model: "opus"` and `effort: "xhigh"`. `model` takes only `opus`, `sonnet`, `haiku`, `fable`. Drop `-fast`. |
| A `gemini-*` or other non-Claude slug | Omit `model` so the agent runs on the session model, and say so. |
| `auto` or `inherit-parent` | Omit `model`. |
| The `zstack-models.md` rule | `~/.claude/rules/zstack-models.md`. Claude Code loads it into every new session, so its role lines are already in context. If they are not, read the file. If the file or the role's line is missing, use the skill's default slug. |
| A role value `<model> <effort>`, such as `opus high` | `model: "opus"` and `effort: "high"`. |

## Paths

| zstack | Claude Code |
| --- | --- |
| The `agent-transcripts/` directory that the system prompt names | `~/.claude/projects/<slug>/`, where each session is one `<session>.jsonl` file. The slug is the workspace path with each `/` and `.` changed to `-`, so `/Users/you/proj` is `-Users-you-proj`. The newest `.jsonl` directly in that folder is the current session. Its `<session>/subagents/` folder holds subagent transcripts. Read only this workspace's folder. |

## Features Claude Code lacks

Claude Code has no cloud agents or built-in PR tool. When a step needs one, put one line in your reply, `Skipped in Claude Code: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| zstack | Claude Code |
| --- | --- |
| Cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | Use the forge CLI, as the step says. That is not a skip, so write no line. |
