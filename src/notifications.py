from src.logger import Logger
logger = Logger()

from src.db import store_notification, NotifierDB
from src.email import email_notification
from src.telegram import tg_notification

def send_notification(sub: dict, events: list, type: str, DB: NotifierDB) -> None:
	"""
	Send a notification to the user based on his notification preference.
	
	Args:
		sub (dict): dictionary containing the user's data.
		events (list): list of events to notify.
	"""
	# Check if the user has any notification preference
	if sub["notification_preferences"] == 3:
		# Email failure must not block Telegram
		email_error = None
		try:
			email_notification(sub, events, type)
		except Exception as e:
			email_error = e
			logger.error(f"Email notification failed for {sub['email']} ({e}). Sending Telegram anyway.")
		tg_sent = tg_notification(sub, events, type)
		if email_error is not None and not tg_sent:
			raise email_error
		logger.debug(f"Email and Telegram notification sent to {sub['email']}.")

	elif sub["notification_preferences"] == 2:
		email_notification(sub, events, type)
		logger.debug(f"Email notification sent to {sub['email']}.")

	elif sub["notification_preferences"] == 1:
		tg_notification(sub, events, type)
		logger.debug(f"Telegram notification sent to {sub['email']}.")

	elif sub["notification_preferences"] == 0: # Should be cleared in main
		logger.debug(f"No notification preference set for {sub['email']}.")
		return

	store_notification(sub["id"], events, DB)

	return