"""Point webhooks on the retired HD Ticket Comment doctype at core Comment.

Upstream moved ticket comments from HD Ticket Comment to core Comment, so a
webhook on HD Ticket Comment never fires again. This keeps EPIUSECX's outbound
comment webhook (and any like it) working: it listens on Comment instead, only
for comments on an HD Ticket, and sends the same keys as before.
"""

import frappe

OLD_DOCTYPE = "HD Ticket Comment"
NEW_DOCTYPE = "Comment"
TICKET_COMMENTS = 'doc.reference_doctype == "HD Ticket" and doc.comment_type == "Comment"'

# HD Ticket Comment field -> the Comment field that holds the same thing
FIELD_MAP = {"reference_ticket": "reference_name", "commented_by": "comment_email"}
# the old condition for "has an author", which Comment guarantees through comment_email
REDUNDANT_CONDITIONS = {"doc.commented_by != None", "doc.commented_by is not None", "doc.commented_by"}


def execute():
    for name in frappe.get_all("Webhook", filters={"webhook_doctype": OLD_DOCTYPE}, pluck="name"):
        condition, webhook_json = frappe.db.get_value("Webhook", name, ["condition", "webhook_json"])
        # the doctype is set-once on the form, so it is moved with a direct write
        frappe.db.set_value(
            "Webhook",
            name,
            {
                "webhook_doctype": NEW_DOCTYPE,
                "condition": translate_condition(condition),
                "webhook_json": translate_template(webhook_json or "") or None,
            },
            update_modified=False,
        )
        for row in frappe.get_all("Webhook Data", filters={"parent": name}, fields=["name", "fieldname"]):
            if row.fieldname in FIELD_MAP:  # the key stays what the receiver expects
                frappe.db.set_value("Webhook Data", row.name, "fieldname", FIELD_MAP[row.fieldname], update_modified=False)
        # saving validates the result and clears the cached webhook list
        frappe.get_doc("Webhook", name).save(ignore_permissions=True)
    frappe.db.commit()


def translate_condition(condition: str | None) -> str:
    condition = (condition or "").strip()
    if condition in REDUNDANT_CONDITIONS:
        condition = ""
    condition = translate_template(condition)
    if not condition:
        return TICKET_COMMENTS
    return f"({condition}) and {TICKET_COMMENTS}"


def translate_template(text: str) -> str:
    for old, new in FIELD_MAP.items():
        text = text.replace(f"doc.{old}", f"doc.{new}")
    return text
