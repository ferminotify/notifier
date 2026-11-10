from src.logger import Logger
logger = Logger()

from src.db import store_notification, NotifierDB
from src.email import email_notification
from src.telegram import tg_notification

# email_sends.kind of each notification type
EMAIL_KIND = {"Daily Notification": "daily", "Last Minute Notification": "lastminute"}

def send_notification(sub: dict, events: list, type: str, DB: NotifierDB) -> bool:
	"""
	Send a notification to the user based on his notification preference.
	Email (bit 2) not to a dead mailbox (email_inactive_at), except the one email that checks it
	(DB.email_check_due, docs/email-caselle-morte.md); Telegram (bit 1) as always.
	
	Args:
		sub (dict): dictionary containing the user's data.
		events (list): list of events to notify.

	Returns:
		bool: whether anything was sent (and stored as notified).
	"""
	prefs = sub["notification_preferences"] or 0
	email = bool(prefs & 2) and (not sub.get("email_inactive_at") or DB.email_check_due(sub["id"]))
	telegram = bool(prefs & 1)
	if not (email or telegram):
		# Nothing sent: not stored as notified (with the email off for a dead mailbox, the
		# events go out with the check, or never).
		logger.debug(f"No channel for {sub['email']} ({'dead mailbox' if prefs & 2 else 'no preference'}).")
		return False

	if email:
		email_id = email_notification(sub, events, type)
		try:
			DB.store_email_send(sub["id"], email_id, EMAIL_KIND.get(type, type))
		except Exception as e:
			# Sent anyway: only its open will not be counted
			DB.connection.rollback()
			logger.error(f"Email send not stored for {sub['email']}: {e}")
		logger.debug(f"Email notification sent to {sub['email']}.")
	if telegram:
		tg_notification(sub, events, type)
		logger.debug(f"Telegram notification sent to {sub['email']}.")

	store_notification(sub["id"], events, DB)

	return True
