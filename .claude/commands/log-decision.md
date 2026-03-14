---
allowed-tools: Bash, Read, Edit
---

Add a new entry to `decisions.md`. Follow these steps exactly.

## Step 1 — Show available sections

```bash
grep -n "^## " decisions.md
```

Tell the user the available sections, then ask them to provide the following 7 fields:

1. **Title** — short phrase (e.g. "Use pyarrow for Parquet writes")
2. **Section** — which `## Section` heading to add it under
3. **Status** — one of: `decided` | `tried-worked` | `tried-failed` | `reversed`
4. **Context** — why this came up (1–3 sentences)
5. **What we did** — the approach taken
6. **Outcome** — what happened / results observed
7. **Decision** — what to do going forward

## Step 2 — Get the current date

```bash
date +%Y-%m-%d
```

## Step 3 — Find the insertion point

```bash
grep -n "^## <Section>" decisions.md
```

Replace `<Section>` with the section name the user chose.

## Step 4 — Insert the entry

Use the Edit tool to insert the new entry at the **top of the section** — immediately after the blank line following the `## Section` heading, before any existing entries.

Format:

```
### YYYY-MM-DD — <Title>
**Status**: <status>
**Context**: <context>
**What we did**: <what-we-did>
**Outcome**: <outcome>
**Decision**: <decision>

```

(Leave one blank line after the entry.)

## Step 5 — If status is `tried-failed`, also update the "What Not to Do" table

If the status is `tried-failed`, add a row to the table under `## What Not to Do`:

```
| <Short approach name> | <One-sentence reason ruled out> |
```

Insert it as the **last row** of the table (before the closing blank line).

## Step 6 — Confirm

Read back the inserted entry to the user and confirm it was added correctly.
