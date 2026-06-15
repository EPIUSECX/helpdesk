"""
Patch: add_customer_ticket_fields_and_webhook

Installs the "agent creates ticket on behalf of customer" feature:

1. Four custom fields on HD Ticket:
     - custom_is_agent_created_for_customer  (Check)  — gate flag
     - custom_customer_first_name            (Data)
     - custom_customer_last_name             (Data)
     - custom_customer_phone                 (Data)   — stored normalised

2. One Server Script (Before Save) on HD Ticket:
     - Normalises customer phone to digits-only + SA country code
     - Auto-composes subject as "{FirstName} {LastName} - {TicketType}"
     - Prepends the chatbot-required description first line:
       <b>Contact Number:</b> +{phone}<br>

3. One Frappe Webhook (after_insert) on HD Ticket:
     - Fires only when custom_is_agent_created_for_customer == 1
     - POSTs the full JSON payload to the chatbot endpoint
     - Headers: User-Agent, Content-Type, Update-Type
     - Body: Jinja template with nested ticket + customer objects

The webhook URL must be set in the Webhook record's Request URL field
after running this patch (via Helpdesk > Integrations > Webhooks or
directly on the Webhook DocType in the Frappe desk).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    _create_custom_fields()
    _create_before_save_script()
    _create_chatbot_webhook()
    frappe.db.commit()


# ---------------------------------------------------------------------------
# 1. Custom fields
# ---------------------------------------------------------------------------

def _create_custom_fields():
    custom_fields = {
        "HD Ticket": [
            {
                "fieldname": "custom_is_agent_created_for_customer",
                "fieldtype": "Check",
                "label": "Agent Created for Customer",
                "insert_after": "via_customer_portal",
                "description": (
                    "Set by the agent wizard. When enabled, phone normalisation, "
                    "subject auto-generation, and the chatbot webhook are applied."
                ),
                "default": "0",
                "read_only": 0,
                "in_list_view": 0,
                "in_standard_filter": 0,
            },
            {
                "fieldname": "custom_customer_first_name",
                "fieldtype": "Data",
                "label": "Customer First Name",
                "insert_after": "custom_is_agent_created_for_customer",
                "depends_on": "eval:doc.custom_is_agent_created_for_customer",
            },
            {
                "fieldname": "custom_customer_last_name",
                "fieldtype": "Data",
                "label": "Customer Last Name",
                "insert_after": "custom_customer_first_name",
                "depends_on": "eval:doc.custom_is_agent_created_for_customer",
            },
            {
                "fieldname": "custom_customer_phone",
                "fieldtype": "Data",
                "label": "Customer Phone (Normalised)",
                "insert_after": "custom_customer_last_name",
                "depends_on": "eval:doc.custom_is_agent_created_for_customer",
                "description": (
                    "Digits only, country code included, no +/spaces. "
                    "Example: 27821234567. Set automatically on save."
                ),
            },
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)


# ---------------------------------------------------------------------------
# 2. Before Save Server Script — data normalisation only, no HTTP calls
# ---------------------------------------------------------------------------

_BEFORE_SAVE_SCRIPT = """\
# HD Ticket — before_save (Agent Customer flow)
# Fires only when custom_is_agent_created_for_customer is set.
# Uses only sandbox-safe builtins (no filter(), no f-strings).

if doc.custom_is_agent_created_for_customer:

    # 1. Phone normalisation — digits only, SA country code
    raw = (doc.custom_customer_phone or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("0"):
        digits = "27" + digits[1:]
    elif not digits.startswith("27"):
        digits = "27" + digits
    doc.custom_customer_phone = digits

    # 2. Auto-compose subject: "{FirstName} {LastName} - {TicketType}"
    first = (doc.custom_customer_first_name or "").strip()
    last = (doc.custom_customer_last_name or "").strip()
    name_parts = [p for p in [first, last] if p]
    full_name = " ".join(name_parts)
    ticket_type = (doc.ticket_type or "").strip()
    subject_parts = [p for p in [full_name, ticket_type] if p]
    if subject_parts:
        doc.subject = " - ".join(subject_parts)

    # 3. Prepend chatbot-required description block (idempotent)
    phone_line = "<b>Contact Number:</b> +" + digits + "<br>"
    name_line  = "<b>Customer Name:</b> " + full_name + "<br>"
    store_line = "<b>Store Branch:</b> " + (doc.agent_group or "") + "<br>"
    type_line  = "<b>Ticket Type:</b> " + (doc.ticket_type or "") + "<br>"
    prefix = phone_line + "\\n" + name_line + "\\n" + store_line + "\\n" + type_line + "\\n"
    existing = doc.description or ""
    if not existing.startswith("<b>Contact Number:</b>"):
        doc.description = prefix + existing
"""


def _create_before_save_script():
    script_name = "HD Ticket — Agent Customer: Before Save"
    if frappe.db.exists("Server Script", script_name):
        frappe.db.delete("Server Script", script_name)

    frappe.get_doc({
        "doctype": "Server Script",
        "name": script_name,
        "script_type": "DocType Event",
        "reference_doctype": "HD Ticket",
        "doctype_event": "Before Save",
        "disabled": 0,
        "script": _BEFORE_SAVE_SCRIPT,
    }).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# 3. Frappe Webhook — fires after_insert, delivers payload to chatbot
# ---------------------------------------------------------------------------

_WEBHOOK_JSON = """\
{
  "update_type": "ticket_created_for_customer",
  "token": "12345",
  "ticket": {
    "name": "{{ doc.name }}",
    "ticket_number": "{{ doc.name }}",
    "ticket_type": "{{ doc.ticket_type or '' }}",
    "status": "{{ doc.status or 'Open' }}",
    "subject": "{{ doc.subject or '' }}",
    "agent_group": "{{ doc.agent_group or '' }}",
    "description": {{ doc.description | tojson }}
  },
  "customer": {
    "phone_number": "{{ doc.custom_customer_phone or '' }}",
    "firstName": "{{ doc.custom_customer_first_name or '' }}",
    "lastName": "{{ doc.custom_customer_last_name or '' }}",
    "email": "{{ doc.raised_by or '' }}"
  }
}"""

_WEBHOOK_NAME = "HD Ticket — Chatbot: Customer Ticket Created"


def _create_chatbot_webhook():
    if frappe.db.exists("Webhook", _WEBHOOK_NAME):
        frappe.delete_doc("Webhook", _WEBHOOK_NAME, ignore_missing=True)

    webhook = frappe.get_doc({
        "doctype": "Webhook",
        "name": _WEBHOOK_NAME,
        "webhook_doctype": "HD Ticket",
        "webhook_docevent": "after_insert",
        "enabled": 1,
        "request_url": "https://unglue-repaying-structure.ngrok-free.dev/webhook",
        "request_method": "POST",
        "request_structure": "JSON",
        "condition": "doc.custom_is_agent_created_for_customer == 1",
        "webhook_json": _WEBHOOK_JSON,
        "webhook_headers": [
            {"key": "Content-Type",  "value": "application/json"},
            {"key": "User-Agent",    "value": "midas-ticket"},
            {"key": "Update-Type",   "value": "ticket_created_for_customer"},
        ],
    })
    webhook.insert(ignore_permissions=True)
