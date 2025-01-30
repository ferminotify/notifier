from src.db import get_subscribers, get_all_sent_id
from src.telegram import register_new_telegram_user
from src.events import get_events, filter_events_kw
from datetime import datetime, timedelta
from src.notifications import send_notification
from src.email import unsub
from time import sleep
import pytz

from src.logger import Logger, clearDBLog
logger = Logger()

'''
Main
'''

def main():
	'''
	Handles all notifier functions.
	'''
	while True:

		time_start = datetime.now(pytz.timezone("Europe/Rome"))

		errors = 0

		logger.info("Start")

		# 1. Get all the subscribers data from the database
		subs = get_subscribers() # sample ==> subscribers
		logger.info(f"[1] Got {len(subs)} subscribers.")

		# 2. Register new telegram users
		register_new_telegram_user(subs)
		logger.info("[2] Registered new telegram users.")

		# 3. Check if any user has unsubscribed
		try:
			logger.info(f"[3] Unsubscribed {unsub()} users.")
		except Exception as e:
			logger.error(f"[X] Error while checking for unsubscribed users: {e}")
			errors += 1

		# 4. Get all the events
		events = get_events() # sample ==> events
		# 4.1. Filter events of today and tomorrow
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
		# 4.2 Reformat events time
		for event in events_today + events_tomorrow:
			if event.get('start.date'):
				event['start.date'] = datetime.strptime(event['start.date'], '%Y-%m-%d').strftime('%d/%m/%Y')
			if event.get('end.date'):
				event['end.date'] = datetime.strptime(event['end.date'], '%Y-%m-%d').strftime('%d/%m/%Y')
			if event.get('start.dateTime'):
				event['start.dateTime'] = datetime.strptime(event['start.dateTime'], '%Y-%m-%dT%H:%M:%S%z').strftime('%H:%M')
			if event.get('end.dateTime'):
				event['end.dateTime'] = datetime.strptime(event['end.dateTime'], '%Y-%m-%dT%H:%M:%S%z').strftime('%H:%M')
		
		logger.info(f"[4] Got {len(events_today)} events of today and {len(events_tomorrow)} of tomorrow.")	

		# 5. Check for each user if there are events to notify
		logger.info("[5] Checking for events to notify...")
		for sub in subs:

			# 5.0. Check if the user has any notification preference
			if sub["notification_preferences"] == 0:
				logger.debug(f"No notification preference set for {sub['email']}.")
				continue

			# 5.1. Filter all events that don't match the user's keywords
			_events_today = filter_events_kw(events_today, sub["tags"])
			_events_tomorrow = filter_events_kw(events_tomorrow, sub["tags"])
			if not _events_today and not _events_tomorrow:
				continue

			# 5.2. Get the events that the user has already been notified 
			sent = get_all_sent_id(sub["id"])
			# filter all events that have not been notified yet
			_events_today = [event for event in _events_today if event["uid"] not in sent]
			_events_tomorrow = [event for event in _events_tomorrow if event["uid"] not in sent]
			if not _events_today and not _events_tomorrow:
				continue

			# 5.3. Send the notifications
			# Check if it's time for Daily Notification
			
			# Convert the notification time to a datetime object
			daily_notification_datetime_end = datetime.combine(datetime.now(pytz.timezone("Europe/Rome")).date(), sub["notification_time"]) + timedelta(minutes=15)

			try:
				if sub["notification_time"] <= datetime.now(pytz.timezone("Europe/Rome")).time() <= daily_notification_datetime_end.time():
					if sub["notification_day_before"]:
						# Send the notification for today (usually empty - rare case new event added right now and not yet sent as last min) and tomorrow
						send_notification(sub, [_events_today, _events_tomorrow], "Daily Notification")
						logger.info(f"[>] Sent Daily Notification ({len(_events_today) + len(_events_tomorrow)}) to {sub['email']}.")
					else:
						if _events_today:
							# Send the notification for today
							send_notification(sub, [_events_today], "Daily Notification")
							logger.info(f"[>] Sent Daily Notification ({len(_events_today)}) to {sub['email']}.")
				else: # Last Minute Notification
					if sub["notification_day_before"]: # if user wants the Daily Notification the day before send today notifications as Last Minute
						# if it's after the Daily Notification time send Last Minute Notification
						if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
							send_notification(sub, [_events_today, events_tomorrow], "Last Minute Notification")
							logger.info(f"[>] Sent Last Minute Notification ({len(_events_today) + len(events_tomorrow)}) to {sub['email']}.")
						else: # if it's before the Daily Notification time send only today notifications as Last Minute (if not already sent)
							if _events_today:
								send_notification(sub, [_events_today], "Last Minute Notification")
								logger.info(f"[>] Sent Last Minute Notification ({len(_events_today)}) to {sub['email']}.")
					else: # if it's after the Daily Notification time and user doesn't want the Daily Notification the day before send only today notifications as Last Minute
						if _events_today:
							if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
								send_notification(sub, [_events_today], "Last Minute Notification")
								logger.info(f"[>] Sent Last Minute Notification ({len(_events_today)}) to {sub['email']}.")

			except Exception as e:
				logger.error(f"[X] Error sending notification to {sub['email']}: {e}")
				errors += 1
		
		time_diff = datetime.now(pytz.timezone("Europe/Rome")) - time_start

		logger.success(f"[5] Notified all events with {errors} errors [{int(time_diff.total_seconds() // 60)}m {int(time_diff.total_seconds() % 60):02d}s].")

		# 6. Clear DB Logs if last log is success
		clearDBLog()
		logger.console("[6] Cleared DB Logs.")

		# 7. Sleep
		logger.console("[7] Sleeping...")
		sleep(300)

if __name__ == "__main__":
    main()
