# Skills

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ming-kang/Skills)

Personal repository for reusable agent Skills.

## Install

```bash
npx skills add ming-kang/skills
```

## Current Skills

### Biu

Biu is a lightweight development-document workflow. It helps turn an unclear development goal into a SPEC, decompose that SPEC into implementation tasks, and archive the completed cycle.

| Skill | Use it when | Output |
|:-:|:-:|:-:|
| `biu-interview` | Clarify a development goal | `.biu/SPEC.md` |
| `biu-decompose` | Turn a ready SPEC into task handoffs | `.biu/tasks/TASK-*.md` |
| `biu-archive` | Summarize and archive a completed cycle | `.biu/archived/YYYY-MM-DD-NN/` |

Typical workflow:

```text
biu-interview -> biu-decompose -> implement -> biu-archive
```

## License

MIT
