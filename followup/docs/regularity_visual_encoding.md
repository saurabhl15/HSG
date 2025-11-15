# Regularity Visual Encoding (Task 6)

Task 6 extends the data API so front-end agents can render the newcomer `Regularity` field without parsing raw strings.

## Output Structure

Every newcomer payload now includes a `regularityVisual` object:

```
{
  "tokens": ["Y", "Y", "N"],
  "attendanceBooleans": [true, true, false],
  "totalWeeks": 3,
  "presentCount": 2,
  "absentCount": 1
}
```

- `tokens` mirrors the normalized `Regularity` string (oldest → newest).
- `attendanceBooleans` aligns index-for-index (`true` = present/green, `false` = absent/red).
- `totalWeeks` equals `tokens.length`.
- `presentCount` / `absentCount` support quick legend and summary UI elements.

If the `Regularity` column is empty or cannot be normalized, all arrays are empty and counts are zero.

## Rendering Guidance

1. Iterate over `attendanceBooleans`.
2. Render a “present” box for `true` (e.g., green) and an “absent” box for `false` (e.g., red).
3. Use `tokens[index]` when you need the literal `Y`/`N`.
4. Display summary counts (e.g., “2 of 3 weeks attended”) using `presentCount` and `totalWeeks`.

Any updates submitted through the API return the refreshed `regularityVisual` object, so the UI can update streak visuals immediately after saving.***

