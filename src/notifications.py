from src.logger import Logger
logger = Logger()

from src.db import store_notification
from src.email import email_notification
from src.telegram import tg_notification

def send_notification(sub: dict, events: list, type: str) -> None:
	"""
	Send a notification to the user based on his notification preference.
	
	Args:
		sub (dict): dictionary containing the user's data.
		events (list): list of events to notify.
	"""
	# Check if the user has any notification preference
	if sub["notification_preferences"] == 3:
		email_notification(sub, events, type)
		tg_notification(sub, events, type)
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

	store_notification(sub["id"], events)

	return