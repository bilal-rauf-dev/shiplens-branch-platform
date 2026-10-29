# Urdu interface glossary

The interface uses polite آپ language and Western digits (0–9). Keep placeholders,
HTML tags and Markdown syntax unchanged when translating. The source catalogue is
`locale/ur/LC_MESSAGES/django.po`; compile it with `python manage.py compilemessages`.
Django's Urdu catalogue supplies standard validation. `apps/core/messages.py`
adds extraction markers for missing framework errors and password guidance; the
project catalogue overrides those messages without changing Django's validators.

| English | Urdu | Usage |
|---|---|---|
| branch | شاخ | Plural: شاخیں. Codes such as BR-KHI-01 stay unchanged. |
| collection | وصولی | One offline donation record; plural: وصولیاں. |
| transfer | منتقلی | Money sent to the main account; plural: منتقلیاں. |
| weekly report | ہفتہ وار رپورٹ | Plural: ہفتہ وار رپورٹیں. |
| approve | منظور کریں | Approved: منظور شدہ. |
| return | واپس کریں | Return a report to its branch for correction. |
| lock | مقفل کریں | Locked: مقفل; a financial record becomes read-only. |
| member | رکن | Plural: ارکان. |
| volunteer | رضاکار | Volunteer role: رضاکارانہ کردار. |
| application | درخواست | Plural: درخواستیں; accepted: قبول شدہ. |
| dashboard | ڈیش بورڈ | Head-office dashboard: مرکزی دفتر کا ڈیش بورڈ. |
| unsent | غیر ارسال شدہ | Includes earlier periods where the screen says all time. |
| snapshot | محفوظ عکس | Frozen report data, distinct from its revision number. |
| hash | ہیش | Technical verification value; keep the value unchanged. |
| slug | یو آر ایل کا مختصر نام | Keep actual URL slugs in Latin characters. |

Finance amounts share the `money` template filter: `Rs 12,345.50` in English and
`12,345.50 روپے` in Urdu. Wrap the output in `<bdi>`. CSV amounts remain plain
numbers. Urdu dates use `j F Y`, for example `30 اکتوبر 2026`.

A fluent owner review is especially useful for the technical terms محفوظ عکس
(snapshot), ہیش (hash), and یو آر ایل کا مختصر نام (slug). The financial lock term
مقفل distinguishes a permanent read-only state from closing a branch.
