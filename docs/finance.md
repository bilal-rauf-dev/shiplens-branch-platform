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
from the first migration. Transfer operations and immutability arrive in P6 Step 3.
The partial unsent index follows BR-071 exactly: transfer is null and voided_at is
null. `week_is_closed` is the explicit P7 integration point and currently returns
False. No weekly-report behavior is implemented in P6.

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
The open-report check remains an explicit P7 integration comment.

Scope tests cover foreign collections, transfers and selection options, global
Finance Reviewer reads, rejected finance writes, and HR/Content Editor denials.
The close workflow is tested through HTTP: 409 while money is unsent, then a
successful redirect after it is transferred. No exports, adjustments or weekly
reports are implemented here.
