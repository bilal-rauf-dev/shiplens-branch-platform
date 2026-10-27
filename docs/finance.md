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
