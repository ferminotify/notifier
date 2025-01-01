from src.db import get_subscribers, get_all_sent_id
from src.telegram import register_new_telegram_user
from src.events import get_events, filter_events_kw
from datetime import datetime, timedelta
from src.notifications import send_notification
from time import sleep
import pytz

from src.logger import Logger
logger = Logger()

'''
Main
'''

def main():
	'''
	Handles all notifier functions.
	'''
	while True:

		logger.info("Start")

		# 1. Get all the subscribers data from the database
		subs = get_subscribers() # sample ==> subscribers
		logger.info(f"[1] Got {len(subs)} subscribers.")

		# 2. Register new telegram users
		register_new_telegram_user(subs)
		logger.info("[2] Registered new telegram users.")

		# 3. Get all the events
		events = get_events() # sample ==> events
		# 3.1. Filter events of today and tomorrow
		today_rome = datetime.now(pytz.timezone("Europe/Rome")).replace(hour=0, minute=0, second=0, microsecond=0)
		tomorrow_rome = today_rome + timedelta(days=1)
		events_today = [
			event for event in events
			if (
				# For events with start.dateTime
				event.get("start.dateTime") and
				today_rome <= datetime.fromisoformat(event["start.dateTime"]).astimezone(pytz.timezone("Europe/Rome")) < today_rome + timedelta(days=1)
			) or (
				# For events with start.date
				event.get("start.date") and
				today_rome.date() <= datetime.strptime(event["start.date"], "%Y-%m-%d").date() < today_rome.date() + timedelta(days=1)
			)
		]
		events_tomorrow = [
			event for event in events
			if (
				# For events with start.dateTime
				event.get("start.dateTime") and
				tomorrow_rome <= datetime.fromisoformat(event["start.dateTime"]).astimezone(pytz.timezone("Europe/Rome")) < tomorrow_rome + timedelta(days=1)
			) or (
				# For events with start.date
				event.get("start.date") and
				tomorrow_rome.date() <= datetime.strptime(event["start.date"], "%Y-%m-%d").date() < tomorrow_rome.date() + timedelta(days=1)
			)
		]
		# 3.2 Reformat events time
		for event in events_today + events_tomorrow:
			if event.get('start.date'):
				event['start.date'] = datetime.strptime(event['start.date'], '%Y-%m-%d').strftime('%d/%m/%Y')
			if event.get('end.date'):
				event['end.date'] = datetime.strptime(event['end.date'], '%Y-%m-%d').strftime('%d/%m/%Y')
			if event.get('start.dateTime'):
				event['start.dateTime'] = datetime.strptime(event['start.dateTime'], '%Y-%m-%dT%H:%M:%S%z').strftime('%H:%M')
			if event.get('end.dateTime'):
				event['end.dateTime'] = datetime.strptime(event['end.dateTime'], '%Y-%m-%dT%H:%M:%S%z').strftime('%H:%M')
		
		logger.info(f"[3] Got {len(events_today)} events of today and {len(events_tomorrow)} of tomorrow.")	

		# 4. Check for each user if there are events to notify
		logger.info("[4] Checking for events to notify...")
		errors = 0
		for sub in subs:

			# 4.0. Check if the user has any notification preference
			if sub["notification_preferences"] == 0:
				logger.info(f"No notification preference set for {sub['email']}.")
				continue

			# 4.1. Get the events that the user has already been notified
			sent = get_all_sent_id(sub["id"])

			# 4.2. Check if there are events to notify
			# filter all events that have not been notified yet
			events_today = [event for event in events_today if event["uid"] not in sent]
			events_tomorrow = [event for event in events_tomorrow if event["uid"] not in sent]
			if not events_today and not events_tomorrow:
				continue

			# 4.3. Filter all events that don't match the user's keywords
			events_today = filter_events_kw(events_today, sub["tags"])
			events_tomorrow = filter_events_kw(events_tomorrow, sub["tags"])
			if not events_today and not events_tomorrow:
				continue

			# 4.4. Send the notifications
			# Check if it's time for Daily Notification
			
			# Convert the notification time to a datetime object
			daily_notification_datetime_end = datetime.combine(datetime.now(pytz.timezone("Europe/Rome")).date(), sub["notification_time"]) + timedelta(minutes=15)

			try:
				if sub["notification_time"] <= datetime.now(pytz.timezone("Europe/Rome")).time() <= daily_notification_datetime_end.time():
					if sub["notification_day_before"]:
						# Send the notification for today (usually empty - rare case new event added right now and not yet sent as last min) and tomorrow
						send_notification(sub, [events_today, events_tomorrow], "Daily Notification")
						logger.info(f"[>] Sent Daily Notification ({len(events_today) + len(events_tomorrow)}) to {sub['email']}.")
					else:
						if events_today:
							# Send the notification for today
							send_notification(sub, [events_today], "Daily Notification")
							logger.info(f"[>] Sent Daily Notification ({len(events_today)}) to {sub['email']}.")
				else: # Last Minute Notification
					if sub["notification_day_before"]: # if user wants the Daily Notification the day before send today notifications as Last Minute
						# if it's after the Daily Notification time send Last Minute Notification
						if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
							send_notification(sub, [events_today, events_tomorrow], "Last Minute Notification")
							logger.info(f"[>] Sent Last Minute Notification ({len(events_today) + len(events_tomorrow)}) to {sub['email']}.")
						else: # if it's before the Daily Notification time send only today notifications as Last Minute (if not already sent)
							if events_today:
								send_notification(sub, [events_today], "Last Minute Notification")
								logger.info(f"[>] Sent Last Minute Notification ({len(events_today)}) to {sub['email']}.")
					else: # if it's after the Daily Notification time and user doesn't want the Daily Notification the day before send only today notifications as Last Minute
						if events_today:
							if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
								send_notification(sub, [events_today], "Last Minute Notification")
								logger.info(f"[>] Sent Last Minute Notification ({len(events_today)}) to {sub['email']}.")

			except Exception as e:
				logger.error(f"[X] Error sending notification to {sub['email']}: {e}")
				errors += 1
		
		logger.success(f"[4] Notified all events with {errors} errors.")

		# 5. Sleep
		logger.info("[5] Sleeping...")
		sleep(300)

if __name__ == "__main__":
    main()
