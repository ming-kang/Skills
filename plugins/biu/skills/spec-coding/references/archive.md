# Archive Phase

Load this file when you enter Phase 5 — all Tasks in `.spec/COMPASS.md` are marked `[x]` or `[-]`, and the user has confirmed they are ready to archive.

**Goal**: Preserve this development cycle's artifacts so the next cycle starts clean.

---

## Actions

1. **Verify all Tasks are terminal.** Scan `.spec/COMPASS.md` Task Overview. If any line still starts with `[ ]` (pending), `[~]` (in progress), or `[!]` (blocked), refuse to archive and report the non-terminal task(s) to the user. Only proceed when every Task line is `[x]` (complete) or `[-]` (skipped).

2. Announce to the user that all Tasks are complete.

3. Determine the archive folder name:
   - Format: `YYYY-MM-DD-NN` where `NN` is a two-digit sequence starting at `01`.
   - Check `.spec/archived/` for existing folders with today's date and increment `NN` accordingly.
   - Example: `.spec/archived/2026-04-13-01/`.

4. Move all current working artifacts into the archive folder, preserving internal structure:
   ```
   .spec/archived/YYYY-MM-DD-NN/
   ├── COMPASS.md
   ├── analysis/
   └── tasks/
   ```

5. The `.spec/` root is now empty (except `archived/`), ready for the next development cycle.

6. Confirm to the user:
   - What was archived and where.
   - That `.spec/` is clean and ready for the next cycle.
   - Suggest committing any production code changes from this cycle to version control if not already done.

**Output**: A clean `.spec/` workspace. Past cycle preserved.
