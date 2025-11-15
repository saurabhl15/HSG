## Volunteer Filtering Logic (Task 2)

This note documents the logic added in `followup/code.gs` to satisfy Task&nbsp;2. It explains how volunteer identifiers are normalized, how newcomer rows are filtered, and how to validate the behaviour.

### Normalization Strategy
- **Emails:** Lowercased and trimmed. Comparisons run on the full address and the local-part (portion before `@`) to support sheets that omit domains.
- **Names:** Lowercased, punctuation stripped to spaces, and whitespace collapsed. The script builds aliases from:
  - canonical full name (e.g. `jane doe`)
  - compact form without spaces (`janedoe`)
  - first name (`jane`)
  - first name + last initial (`jane d` and `janed`)
- **Fallbacks:** If a newcomer row lists only a single token (e.g. `JANE`), the filter accepts any volunteer whose normalized first name matches. This is a last resort when the sheet lacks richer identifiers.

### Matching Order
1. **Exact email match** between the row and the volunteer.
2. **Email local-part match** when the sheet recorded only the username portion.
3. **Alias intersection** – any shared token from the alias sets above.
4. **Single-token fallback** for first-name-only entries.
5. **First name + last initial** fallback (`jane d`).

Rows failing all checks are excluded from the volunteer’s view.

### Key Helpers
- `getAssignedNewcomersForVolunteer(volunteer)` – loads sheet records, normalizes identifiers, and returns the subset assigned to `volunteer`.
- `listNewcomersForCurrentVolunteer()` – wraps `ensureAuthorizedVolunteer()` and applies the same filtering for the signed-in user.
- `runVolunteerFilteringSample()` – provides a sample dataset with mixed identifier formats; run it from the Apps Script editor to inspect log output.

### Sample Verification
Running `runVolunteerFilteringSample()` yields the record IDs that match `Jane Doe / leader@example.com`:

```
// Apps Script execution log
{
  "volunteer": {"email":"leader@example.com","name":"Jane Doe"},
  "filteredRecordIds": [1, 2, 3],
  "totalCandidates": 4,
  "matchedCount": 3
}
```

This demonstrates coverage for:
- Exact email match (`Record Id` 1)
- Name with abbreviated surname (`Record Id` 2)
- Uppercased first-name-only entry (`Record Id` 3)
- Non-matching volunteer (`Record Id` 4) remains excluded

Add new scenarios here as additional edge cases are identified (e.g. hyphenated names, alternate staff domains).

