import frappe


def execute():
    frappe.reload_doc("helpdesk", "doctype", "hd_ticket")
    # Backfill priority_order from HD Ticket Priority.integer_value
    # so the compound sort (priority_order asc, modified desc) works
    # for tickets created before this field existed.
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket` t
        LEFT JOIN `tabHD Ticket Priority` p ON t.priority = p.name
        SET t.priority_order = COALESCE(p.integer_value, 0)
        """
    )
    frappe.db.commit()
