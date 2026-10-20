"""Comment permission and lifecycle rules for HD Ticket.

Ticket comments are internal agent notes. Customers can read their own
tickets, so without these they would reach the comments on them too.
"""

import json

import frappe
from frappe import _

from helpdesk.utils import (
    get_reply_classification,
    is_admin,
    is_agent,
    publish_event,
)

MAX_PINNED_COMMENTS = 5


def before_insert(doc, method: str | None = None):
    """The insert path ignores permissions, so the write gate has to live here."""
    if doc.reference_doctype != "HD Ticket" or doc.comment_type != "Comment":
        return
    if not is_agent():
        frappe.throw(
            _("You are not permitted to add a comment"), frappe.PermissionError
        )


def validate(doc, method: str | None = None):
    """Caps pinned comments per ticket so the pinned bar stays readable."""
    if doc.reference_doctype != "HD Ticket" or not doc.is_pinned:
        return
    if not doc.has_value_changed("is_pinned"):
        return
    pinned = frappe.db.count(
        "Comment",
        {
            "reference_doctype": "HD Ticket",
            "reference_name": doc.reference_name,
            "is_pinned": 1,
            "name": ["!=", doc.name],
        },
    )
    if pinned >= MAX_PINNED_COMMENTS:
        frappe.throw(
            _("A ticket can have at most {0} pinned comments").format(
                MAX_PINNED_COMMENTS
            )
        )


def after_insert(doc, method: str | None = None):
    """EPIUSECX: keep the ticket list live and its unread / last-reply state right
    when a comment is added (this used to live in HD Ticket Comment)."""
    if doc.reference_doctype != "HD Ticket" or doc.comment_type != "Comment":
        return
    ticket = doc.reference_name
    # Broadcast to the global room so the ticket list page can refresh.
    publish_event("helpdesk:ticket-list-update", data={"ticket_id": ticket})
    # Touch the ticket's modified timestamp and reset the seen list so agents are
    # notified of new activity, keeping the acting user as seen like doc.save() does.
    frappe.db.set_value("HD Ticket", ticket, "_seen", json.dumps([frappe.session.user]))
    # Last-reply columns reflect comments as well as emails; classify on the commenter
    # so any code path that creates a comment is covered.
    response_field = (
        "last_agent_response"
        if get_reply_classification(doc.comment_email or doc.owner) == "agent"
        else "last_customer_response"
    )
    frappe.db.set_value("HD Ticket", ticket, response_field, frappe.utils.now_datetime())


def on_trash(doc, method: str | None = None):
    """Core only clears notifications by document, not by source."""
    if doc.reference_doctype != "HD Ticket":
        return
    frappe.db.delete(
        "Notification Log", {"source_doctype": "Comment", "source_name": doc.name}
    )
    if doc.comment_type == "Comment":
        # EPIUSECX: refresh the ticket list and notify agents of the deletion.
        publish_event("helpdesk:ticket-list-update", data={"ticket_id": doc.reference_name})
        frappe.db.set_value(
            "HD Ticket", doc.reference_name, "_seen", json.dumps([frappe.session.user])
        )


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
    user = user or frappe.session.user
    # only read: write/delete stay a role question, or no one but Administrator could moderate
    if ptype != "read":
        return True
    if doc.reference_doctype != "HD Ticket":
        return True
    if doc.comment_type in (
        "Assigned",
        "Assignment Completed",
    ) and "Customer" in frappe.get_roles(user):
        return False
    return can_see_ticket_comments(doc.reference_name, user)


def can_see_ticket_comments(ticket: str, user: str | None = None) -> bool:
    """Agents only, and only on a ticket they are allowed to read themselves."""
    user = user or frappe.session.user
    if is_admin(user):
        return True
    if not is_agent(user):
        return False
    return bool(frappe.has_permission("HD Ticket", "read", doc=ticket, user=user))
