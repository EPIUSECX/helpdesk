import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.patches import repoint_comment_webhooks
from helpdesk.patches.repoint_comment_webhooks import TICKET_COMMENTS, translate_condition


class TestCommentWebhookRepoint(FrappeTestCase):
    def setUp(self):
        if frappe.db.exists("Webhook", "Test Comment Webhook"):
            frappe.delete_doc("Webhook", "Test Comment Webhook", force=True)

    def make_old_webhook(self):
        """A webhook in the shape EPIUSECX sites have: on the legacy HD Ticket Comment doctype."""
        webhook = frappe.new_doc("Webhook")
        webhook.update(
            {
                "__newname": "Test Comment Webhook",
                "webhook_doctype": "HD Ticket Comment",
                "webhook_docevent": "after_insert",
                "request_url": "https://example.com/webhook",
                "request_method": "POST",
                "request_structure": "Form URL-Encoded",
                "condition": "doc.commented_by != None",
            }
        )
        webhook.append("webhook_data", {"fieldname": "name", "key": "name"})
        webhook.append("webhook_data", {"fieldname": "reference_ticket", "key": "reference_ticket"})
        webhook.insert(ignore_permissions=True)
        return webhook.name

    def test_the_known_condition_becomes_a_ticket_comment_condition(self):
        self.assertEqual(translate_condition("doc.commented_by != None"), TICKET_COMMENTS)
        self.assertEqual(translate_condition(""), TICKET_COMMENTS)

    def test_a_custom_condition_is_translated_and_kept(self):
        self.assertEqual(
            translate_condition('doc.reference_ticket == "0001"'),
            f'(doc.reference_name == "0001") and {TICKET_COMMENTS}',
        )

    def test_patch_repoints_the_webhook_and_keeps_the_keys(self):
        name = self.make_old_webhook()
        repoint_comment_webhooks.execute()
        webhook = frappe.get_doc("Webhook", name)
        self.assertEqual(webhook.webhook_doctype, "Comment")
        self.assertEqual(webhook.condition, TICKET_COMMENTS)
        rows = {row.key: row.fieldname for row in webhook.webhook_data}
        self.assertEqual(rows, {"name": "name", "reference_ticket": "reference_name"})

    def test_patch_is_idempotent(self):
        name = self.make_old_webhook()
        repoint_comment_webhooks.execute()
        first = frappe.get_doc("Webhook", name).as_dict()
        repoint_comment_webhooks.execute()
        self.assertEqual(frappe.get_doc("Webhook", name).condition, first.condition)
