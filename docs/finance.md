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
