# zstack in Codex

zstack skills use their own names for tools, subagent fields, models, and paths. In Codex, read this file once per session, then map each name in a skill with the tables below. `<zstack>` means the folder that holds `skills/` and `docs/`. If a subagent field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| zstack | Codex |
| --- | --- |
| `Task` | `spawn_agent` with `fork_turns: "none"`. Put the brief in `message`. The default, `fork_turns: "all"`, copies this whole conversation into the subagent, and a zstack brief stands alone. |
| `AskQuestion` | The session's question tool, such as `request_user_input`, when it offers one. Otherwise ask in plain text and wait for the reply. |
| Open a todolist | Use the plan tool if the session offers it. Otherwise keep the list in your reply and update it at each phase. |
| Run another zstack skill (`/name` or "the **name** skill") | Read `<zstack>/skills/<name>/SKILL.md` and follow it. Every skill here turns implicit invocation off, so Codex never loads one for you. When you tell the user to run it, tell them to type `$` and pick `<name>`. A plugin install lists it as `zstack:<name>`. |
| `Grep`, `Glob` | A shell command with `rg`. |
| The `create-skill` skill | The bundled `skill-creator` skill. |
| `/loop` | Codex has no `/loop` command. To wait inside this turn, use the `sleep` tool when the session offers it. For a check that recurs after the turn ends, use a scheduled task or an automation when the session offers one. Otherwise skip the step with the line in Features Codex lacks. |

## Subagent fields

| zstack | Codex |
| --- | --- |
| `subagent_type: generalPurpose` | Omit `agent_type`. |
| `zen-agent`, `comment-sicko` | Omit `agent_type`. This plugin does not register them as Codex agents, so start the brief with "Read `<zstack>/agents/<name>.md` in full and act as that agent." |
| `readonly: true` | No field makes a subagent read-only. The brief says "do not edit files", and you check `git status` afterward. |
| `readonly: false` | Omit. |
| `environment: "cloud"` | Create a worktree with `git worktree add` for each subagent that writes, on the branch or commit it starts from. Name the path in the brief and tell the subagent to work only there. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Create the subagent's worktree from `<b>`. |
| `run_in_background: true` | Omit. Spawn every subagent that a step names in one turn, then wait for all the results. |
| `resume` | `followup_task` to the same subagent while it is open. Otherwise spawn a new subagent and paste the earlier result into its brief. |
| `file_attachments` | List the paths in the brief. |

## Models

| zstack | Codex |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, a `gemini-*` slug, or any other slug that is not an OpenAI model | Omit `model` so the subagent runs on the session model, and say so. Keep the effort the slug names: set `reasoning_effort` to `low`, `medium`, `high`, `xhigh`, or `max`, if the session model supports that level. Drop `-fast`. |
| `auto` or `inherit-parent` | Omit `model`. |
| The `zstack-models.md` rule, `~/.claude/rules/zstack-models.md` | Codex does not load this file. Use each skill's default slug and map it with the first row. |
| A step that needs a model from another vendor, such as the arena cross-judge | Codex runs no other vendor's model. Follow the skill's own fallback for a rejected slug, and say so. |

## Paths

| zstack | Codex |
| --- | --- |
| `.claude/skills/`, `~/.claude/skills/` | `.agents/skills/`, `~/.agents/skills/` |
| `~/.claude/plugins/` | `~/.codex/plugins/` |
| The `agent-transcripts/` directory that the system prompt names, and `~/.claude/projects/<slug>/` | `~/.codex/sessions/<year>/<month>/<day>/rollout-<timestamp>-<id>.jsonl`. Codex files sessions by date, not by workspace. The first line of each file is a `session_meta` record, and its `payload.cwd` is the workspace. Read only the files whose `cwd` is this workspace or a folder inside it. |
| The first JSONL line's `message.content[0].text` holds the opening user prompt | Not in Codex. A user message is a `response_item` record whose `payload.role` is `user`, and its text is in `payload.content[].text`. Records before the opening prompt can hold injected context, such as the AGENTS.md instructions, so check every user record in the file. A subagent's session is a separate file, and its `session_meta` has a `payload.parent_thread_id` that equals the parent's `payload.id`. |

## Features Codex lacks

Codex has no cloud agents or built-in PR tool. When a step needs one, put one line in your reply, `Skipped in Codex: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| zstack | Codex |
| --- | --- |
| Cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | Use the forge CLI, as the step says. That is not a skip, so write no line. |
