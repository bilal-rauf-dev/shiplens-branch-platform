# Offline collections and transfers

Collections store cash, cheque or bank-deposit receipts only. There are no online
payment fields. `create_collection` locks and scopes the Active branch, validates
the date using the Karachi business clock and configured lock days, and checks
amount precision, limits, receipt format and same-branch member selection.
References use the existing transactional branch counter; a failed audit write
rolls back both the entry and counter. Database constraints protect receipt
uniqueness, methods, positive collection amounts, adjustment links and complete
void information. Adjustment columns are reserved for a later task; no adjustment
form or service exists.

The Transfer table is created alongside Collection so its foreign key is real
from the first migration. Transfer services and database guards are implemented.
The partial unsent index follows BR-071 exactly: transfer is null and voided_at is
null. `week_is_closed` delegates to the report selector and blocks weeks with a
Submitted, Resubmitted, Approved or Locked report; see [weekly reports](weekly-reports.md).

## Lock, edits and voids

The lock instant is creation time plus the current configured lock days, not the
user-entered collection date. `state` is derived in order: Voided, Sent, Locked,
Open. There is no stored state column or unlock action. `assert_editable` checks
void, transfer, exact lock instant and week closure; services and the direct-model
save guard share it. References and branch ownership are not editable form fields.

Edit and void services lock the branch before the collection. A state refusal is
audited inside that transaction and raised only after it commits, so returning
HTTP 409 does not erase `collection.edit_denied`. Valid edits and voids commit
with their audit events. Totals exclude voided rows; locked entries remain real
money and remain unsent until transferred. Financial reads are scoped for Branch
Leads and global for Finance Reviewer/Super Admin; only assigned Branch Leads
can write. Date/method/state filters, 25-row pagination, lock countdowns and the
shared history panel are server-rendered. Success uses POST-redirect-GET.

## Correcting a mistake

An assigned Branch Lead can **Edit** a collection, including its amount, or
**Void** it with a reason while it is still editable. The default window ends
exactly seven days after entry creation, using `collection_lock_days`; it is not
seven days after the collection date. A void, transfer or closed reporting week
blocks changes even earlier. Edits must also satisfy the normal date, amount and
receipt rules. Voiding retains the record and its receipt number, so that number
cannot be reused in the same branch.

At and after the lock instant, nobody can edit, void or unlock the collection,
including Finance Reviewer and Super Admin. Returning a report does not restart
the seven-day window. A locked, unsent collection can still be transferred, but
the transfer sends its whole recorded amount and does not correct it.

- **Under-recorded amount:** the locked receipt cannot be increased. The create
  form and service still allow an ordinary positive collection for genuinely
  unrecorded money with its own valid, branch-unique receipt number. The branch
  must be Active, the real collection date must fall between today minus the
  configured lock days and today, and its reporting week must be open. A source
  note can identify the earlier reference. This creates a separate ordinary
  record; it is not a linked adjustment and does not revise the locked receipt
  or an approved report snapshot. If those normal entry rules cannot be met,
  the shortfall remains a discrepancy; the app has no correction action for it.
- **Over-recorded amount:** the locked receipt cannot be reduced or voided.
  Ordinary collection forms and services reject zero and negative amounts, so
  there is no in-app reversal or compensating negative entry. Flag the
  discrepancy to Finance for reconciliation outside the app.

To flag either mistake, the Branch Lead opens **Reports**, chooses an assigned
branch's **Draft** or **Returned** report, and records the original reference,
receipt number, recorded amount, actual amount and difference in **Issues**
(up to 2,000 characters). Complete the required Activities and Volunteer hours
fields, then choose **Save narrative**; Finance can read it in the report detail.
Normal submission/resubmission puts the report in Finance's
review queue when the week is eligible. A Locked report's narrative cannot be
changed. Issues is a report field, not an automatic notification; contact Finance
offline for immediate attention or when no editable report is available. See
[weekly reports](weekly-reports.md) for the review lifecycle.

**BR-067 adjustment entries are the planned correction mechanism.** The
`entry_type` and `adjusts_collection_id` columns and database checks already reserve
non-zero signed adjustments linked to a collection. No adjustment service, form
or route exists; the planned reason requirement and rule that adjustments are
dated today are not implemented.
Schema support alone does not make adjustments available to staff. The current
guards are in `apps/finance/services.py:assert_editable`, `validated_values` and
`create_collection`; narrative changes use
`apps/finance/report_services.py:save_narrative`.

## Sending to the main account

Choose Unsent on the collection list, select whole entries, then review them in
the transfer form. Selection and totals are computed on the server; there is no
JavaScript or posted total. Entries must be from one assigned branch, non-voided
and not sent. Transfer dates range from the latest collection date through today.
The bank reference identifies an offline deposit, not a payment gateway.

The service locks the branch then collections in primary-key order, allocates
TRF references using a locked counter, stores the Decimal sum and marks each row
sent. Transfer creation, collection links and all audit events commit together.
A locked-but-unsent entry may still be sent. Stale selections return 409.
PostgreSQL triggers reject changes to sent financial fields and all transfer
updates/deletes; reverse migration SQL removes both guards. Transfer list and
detail retain the same BL scope and global FR/SA read-only access.

## Branch closure and scope

Unsent collections block closing a branch, with their count and Decimal total in
PKR. This is an all-time check and includes locked receipts. Sending or voiding
removes an entry from that blocker. Branch close and finance writes take the
branch lock first, so a collection cannot slip into a branch during its closure.
Submitted, Resubmitted and Returned weekly reports also block closure.

Scope tests cover foreign collections, transfers and selection options, global
Finance Reviewer reads, rejected finance writes, and HR/Content Editor denials.
The close workflow is tested through HTTP: 409 while money is unsent, then a
successful redirect after it is transferred. Adjustment entry remains unimplemented.
[Exports](exports.md) and [weekly reports](weekly-reports.md) have their own guides.
