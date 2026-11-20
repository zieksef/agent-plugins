# stock

Stock market workflows for Claude Code and Codex.

## Install

Claude Code:

```bash
claude plugin marketplace add zieksef/agent-plugins
claude plugin install stock@zieksef
```

Codex:

```bash
codex plugin marketplace add zieksef/agent-plugins
codex plugin add stock@zieksef
```

## Premarket

Run it before the US market opens, with one or more tickers.

- In Claude Code, type `/stock:premarket` and then the tickers, such as `/stock:premarket RKLB ASTS`.
- In Codex, type `$`, pick `stock:premarket`, and then type the tickers.

It writes the brief to `~/stock-bear/premarket/` and opens the HTML page.
