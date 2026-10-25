from src.db import NotifierDB
from src.telegram import register_new_telegram_user
from src.events import get_events, filter_events_kw, search_events, remove_sent_events
from datetime import datetime, timedelta
from src.notifications import send_notification
from src.push import send_pushes
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

		DB = NotifierDB()  # Initialize DB connection

		time_start = datetime.now(pytz.timezone("Europe/Rome"))

		errors = 0
		notifications = 0

		logger.info("Start")

		# 1. Get all the subscribers data from the database
		subs = DB.get_subscribers() # sample ==> subscribers
		push_subs = DB.get_subscribers_push()  # one row per push device
		logger.info(f"[1] Got {len(subs)} subscribers and {len(push_subs)} push devices.")

		# 2. Register new telegram users
		register_new_telegram_user(subs, DB)
		logger.info("[2] Registered new telegram users.")

		# 3. Check if any user has unsubscribed
		'''
		try:
			logger.info(f"[3] Unsubscribed {unsub()} users.")
		except Exception as e:
			logger.error(f"[X] Error while checking for unsubscribed users: {e}")
			errors += 1
		'''

		# 4. Today's and tomorrow's events for every user's keywords, from the backend (the
		# school calendar, same rules as "Cerca eventi" and the timetable page), in one request.
		# Only the keywords set: "probable" events (the most similar class name) are gone, the
		# dashboard flags keywords that are no class instead.
		all_keywords = [kw for sub in subs if sub["notification_preferences"] != 0 for kw in (sub["tags"] or [])]
		all_keywords += [kw for sub in push_subs for kw in (sub["keywords"] or [])]
		today_rome = datetime.now(pytz.timezone("Europe/Rome")).replace(hour=0, minute=0, second=0, microsecond=0)
		tomorrow_rome = today_rome + timedelta(days=1)
		matches = search_events(all_keywords, today_rome.strftime("%Y-%m-%d"), tomorrow_rome.strftime("%Y-%m-%d"))
		if matches is not None:
			events = matches["events"]
			logger.info(f"[4] Events and keywords from the backend.")
		else:
			# Backend down: the CSV, and the keywords' words in the titles
			events = get_events() # sample ==> events
			logger.info(f"[4] Events from the CSV, keywords matched locally (backend unavailable).")
		# 4.1. Filter events of today and tomorrow
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
		# Push reads the ISO times: its own copies, before 4.2 reformats them for email/Telegram
		push_today = [dict(e) for e in events_today]
		push_tomorrow = [dict(e) for e in events_tomorrow]

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
			# not covered case: multi-day event with start.dateTime and end.dateTime in different days
		
		logger.info(f"[4] Got {len(events_today)} events of today and {len(events_tomorrow)} of tomorrow.")	

		# 5. Check for each user if there are events to notify
		logger.info("[5] Checking for events to notify...")
		for sub in subs:

			logger.debug(f"Checking subscriber {sub['email']}...")

			# 5.0. Check if the user has any notification preference
			if sub["notification_preferences"] == 0:
				logger.debug(f"No notification preference set for {sub['email']}.")
				continue

			# 5.1.1 Filter all events that don't match the user's keywords
			_events_today = filter_events_kw(events_today, sub["tags"], matches, sub.get("notify_optin"))
			_events_tomorrow = filter_events_kw(events_tomorrow, sub["tags"], matches, sub.get("notify_optin"))
			if not (_events_today or _events_tomorrow):
				continue

			# 5.2. Get the events that the user has already been notified 
			sent = DB.get_all_sent_id(sub["id"])
			# filter all events that have not been notified yet
			_events_today = remove_sent_events(_events_today, sent)
			_events_tomorrow = remove_sent_events(_events_tomorrow, sent)
			if not (_events_today or _events_tomorrow):
				continue

			# 5.3. Send the notifications
			# Check if it's time for Daily Notification
			
			# Convert the notification time to a datetime object
			daily_notification_datetime_end = datetime.combine(datetime.now(pytz.timezone("Europe/Rome")).date(), sub["notification_time"]) + timedelta(minutes=15)

			try:
				if sub["notification_time"] <= datetime.now(pytz.timezone("Europe/Rome")).time() <= daily_notification_datetime_end.time(): # Daily Notification
					if sub["notification_day_before"]:
						# Send the notification for today (usually empty - rare case new event added right now and not yet sent as last min) and tomorrow
						send_notification(sub, [[_events_today, _events_tomorrow], []], "Daily Notification", DB)
						logger.info(f"[>] Sent Daily Notification ({len(_events_today + _events_tomorrow)}) to {sub['email']}.")
						notifications += 1
					else:
						if _events_today:
							# Send the notification for today
							send_notification(sub, [[_events_today], []], "Daily Notification", DB)
							logger.info(f"[>] Sent Daily Notification ({len(_events_today)}) to {sub['email']}.")
							notifications += 1
				else: # Last Minute Notification
					if sub["notification_day_before"]: # if user wants the Daily Notification the day before send today notifications as Last Minute
						# if it's after the Daily Notification time send Last Minute Notification
						if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
							send_notification(sub, [[_events_today, _events_tomorrow], []], "Last Minute Notification", DB)
							logger.info(f"[>] Sent Last Minute Notification ({len(_events_today + _events_tomorrow)}) to {sub['email']}.")
							notifications += 1
						else: # if it's before the Daily Notification time send only today notifications as Last Minute (if not already sent)
							if _events_today:
								send_notification(sub, [[_events_today], []], "Last Minute Notification", DB)
								logger.info(f"[>] Sent Last Minute Notification ({len(_events_today)}) to {sub['email']}.")
								notifications += 1
					else: # if it's after the Daily Notification time and user doesn't want the Daily Notification the day before send only today notifications as Last Minute
						if _events_today:
							if datetime.now(pytz.timezone("Europe/Rome")).time() > daily_notification_datetime_end.time():
								send_notification(sub, [[_events_today], []], "Last Minute Notification", DB)
								logger.info(f"[>] Sent Last Minute Notification ({len(_events_today)}) to {sub['email']}.")
								notifications += 1

			except Exception as e:
				logger.error(f"[X] Error sending notification to {sub['email']}: {e}")
				errors += 1
		
		# 5.4 Push notifications, same events and matches (was the separate notifier-push)
		pushed, push_errors = send_pushes(DB, push_subs, push_today, push_tomorrow, matches)
		logger.info(f"[5] Sent push to {pushed} devices with {push_errors} errors.")
		notifications += pushed
		errors += push_errors

		time_diff = datetime.now(pytz.timezone("Europe/Rome")) - time_start

		if errors > 0:
			logger.error(f"[5] Sent {notifications} notifications with {errors} errors [{int(time_diff.total_seconds() // 60)}m {int(time_diff.total_seconds() % 60):02d}s].")
		else:
			logger.success(f"[5] Sent {notifications} notifications with {errors} errors [{int(time_diff.total_seconds() // 60)}m {int(time_diff.total_seconds() % 60):02d}s].")

		# 6. Clear DB Logs if last log is success
		clearDBLog()
		logger.console("[6] Cleared DB Logs.")

		# 7. Sleep
		logger.console("[7] Sleeping...")
		sleep(300)

		# Close DB connection
		DB.close_connection()

if __name__ == "__main__":
    main()
