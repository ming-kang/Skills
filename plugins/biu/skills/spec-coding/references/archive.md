# Archive Phase

Load this file when you enter Phase 5 — all Tasks in `.spec/COMPASS.md` are marked `[x]` or `[-]`, and the user has confirmed they are ready to archive.

**Goal**: Preserve this development cycle's artifacts so the next cycle starts clean.

---

## Actions

1. Announce to the user that all Tasks are complete.

2. Determine the archive folder name:
   - Format: `YYYY-MM-DD-NN` where `NN` is a two-digit sequence starting at `01`.
   - Check `.spec/archived/` for existing folders with today's date and increment `NN` accordingly.
   - Example: `.spec/archived/2026-04-13-01/`.

3. Move all current working artifacts into the archive folder, preserving internal structure:
   ```
   .spec/archived/YYYY-MM-DD-NN/
   ├── COMPASS.md
   ├── analysis/
   └── tasks/
   ```

4. The `.spec/` root is now empty (except `archived/`), ready for the next development cycle.

5. Confirm to the user:
   - What was archived and where.
   - That `.spec/` is clean and ready for the next cycle.
   - Suggest committing any production code changes from this cycle to version control if not already done.

**Output**: A clean `.spec/` workspace. Past cycle preserved.
