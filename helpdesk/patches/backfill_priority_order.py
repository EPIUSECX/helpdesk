import frappe


def execute():
    """Backfill HD Ticket.priority_order from the priority's level so the compound sort
    (priority_order asc, modified desc) works for tickets created before the field existed.

    Runs after backfill_priority_level, which fills the level that this reads."""
    frappe.reload_doc("helpdesk", "doctype", "hd_ticket")
    frappe.db.sql(
        """
        UPDATE `tabHD Ticket` t
        LEFT JOIN `tabHD Ticket Priority` p ON t.priority = p.name
        SET t.priority_order = CASE p.level
            WHEN 'Urgent' THEN 1
            WHEN 'High' THEN 2
            WHEN 'Medium' THEN 3
            WHEN 'Low' THEN 4
            ELSE 0
        END
        """
    )
    frappe.db.commit()
