#!/usr/bin/env bash
# biu/hooks/guard-dangerous.sh
# PreToolUse hook: blocks destructive Bash commands.
# Exit 0 allows, exit 2 + stderr blocks the tool call.

set -euo pipefail

# shellcheck source=lib/require-python.sh
. "${CLAUDE_PLUGIN_ROOT}/hooks/lib/require-python.sh"

# Capture hook JSON from stdin; the heredoc below will replace stdin for python.
HOOK_JSON="$(cat)"

# require-python.sh returns with BIU_PY set, or exits 0 if python missing.
BIU_HOOK_JSON="$HOOK_JSON" "$BIU_PY" <<'PYEOF'
import json, os, shlex, sys

raw = os.environ.get("BIU_HOOK_JSON", "")
if not raw:
    sys.exit(0)

try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input") or {}).get("command") or ""
if not cmd:
    sys.exit(0)

try:
    toks = shlex.split(cmd, posix=True)
except ValueError:
    # Unbalanced quotes — fall back to whitespace split so we still screen.
    toks = cmd.split()

if not toks:
    sys.exit(0)


def block(msg: str) -> None:
    sys.stderr.write(f"[biu guard] Blocked: {msg}\n")
    sys.stderr.write("[biu guard] If this is intentional, run the command manually in your shell.\n")
    sys.exit(2)


SENSITIVE = {"/", "~", "$HOME", ".", "./", ".git", ".git/", "node_modules", "node_modules/", ".spec", ".spec/"}


def is_sensitive(token: str) -> bool:
    t = token.rstrip("/")
    if t in {s.rstrip("/") for s in SENSITIVE}:
        return True
    # Root-equivalent absolute paths with no sub-path.
    if t in {"/", ""}:
        return True
    # $HOME / ~ with no sub-path.
    if t in {"~", "$HOME"}:
        return True
    return False


def find_cmd_heads(tokens):
    """Yield (index, head) for each command head in a pipeline/sequence."""
    yield 0, tokens[0]
    for i, tok in enumerate(tokens):
        if tok in {"|", "||", "&&", ";", "&"} and i + 1 < len(tokens):
            yield i + 1, tokens[i + 1]


for start, head in find_cmd_heads(toks):
    # Segment = this command up to the next separator.
    end = start
    while end < len(toks) and toks[end] not in {"|", "||", "&&", ";", "&"}:
        end += 1
    segment = toks[start:end]
    if not segment:
        continue
    name = segment[0]
    args = segment[1:]

    # --- Rule 1: rm with -r/-f targeting a sensitive top-level path ---
    if name == "rm":
        flags = [a for a in args if a.startswith("-") and not a.startswith("--")]
        has_r = any("r" in f.lower() for f in flags)
        has_f = any("f" in f.lower() for f in flags)
        if has_r and has_f:
            targets = [a for a in args if not a.startswith("-")]
            for t in targets:
                if is_sensitive(t):
                    block(
                        f"rm -rf targeting a sensitive top-level path ({t}) "
                        "without a concrete sub-path. Specify a deeper path "
                        "(e.g. '.spec/archived/2026-04-17-01/') if you really need to clean it."
                    )

    # --- Rule 2: bare `git reset --hard` with no ref ---
    if name == "git" and len(args) >= 2 and args[0] == "reset" and args[1] == "--hard":
        rest = args[2:]
        # Strip further flags; a ref is a non-flag positional.
        refs = [a for a in rest if not a.startswith("-")]
        if not refs:
            block(
                "'git reset --hard' without a ref will discard uncommitted work. "
                "Specify a ref explicitly (e.g. 'git reset --hard HEAD~1' or "
                "'git reset --hard origin/main')."
            )

    # --- Rule 3: `git push --force` / -f to main or master ---
    if name == "git" and args and args[0] == "push":
        push_args = args[1:]
        forced = any(a in {"-f", "--force"} or a.startswith("--force=") for a in push_args)
        if forced:
            # Check for main/master in any positional refspec.
            for a in push_args:
                if a.startswith("-"):
                    continue
                # refspec like `main`, `origin main`, `origin HEAD:main`, `:main`.
                parts = a.split(":")
                for p in parts:
                    if p in {"main", "master"}:
                        block(
                            "'git push --force' to a protected branch (main/master). "
                            "Force-push to a feature branch instead, or coordinate with "
                            "the team before rewriting protected history."
                        )

sys.exit(0)
PYEOF
