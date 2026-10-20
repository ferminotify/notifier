"""
Push notifications (web push through the backend's /user/push/notify), sent in the same
round as email and Telegram, on the same events and keyword matches.
Ported from ferminotify/notifier-push: same texts, timing and push_sent table per device.
"""
import os
from datetime import datetime, timedelta
import pytz
import requests

from src.events import filter_events_kw, remove_sent_events
from src.logger import Logger
_LOGGER = Logger()

TZ = pytz.timezone("Europe/Rome")


def _parse_event_datetime(ev: dict, tz):
    """Return (start_date, start_time, end_date, end_time).
    Each value may be None. Accepts ISO datetimes or already-formatted HH:MM strings;
    also checks start.date / end.date. Keeps parsing defensive and logs on parse failures.
    """
    start_date = None
    start_time = ''
    end_date = None
    end_time = ''

    # start.dateTime or start.date
    sdt = ev.get('start.dateTime')
    if sdt:
        if 'T' in sdt:
            try:
                dt = datetime.fromisoformat(sdt)
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                dt = dt.astimezone(tz)
                start_time = dt.strftime('%H:%M')
                start_date = dt.date()
            except Exception:
                start_time = sdt
                if _LOGGER:
                    _LOGGER.debug(f"_parse_event_datetime: failed to parse start.dateTime '{sdt}'")
        else:
            # already a time string like 'HH:MM'
            start_time = sdt

    sd = ev.get('start.date')
    if sd:
        try:
            if '-' in sd:
                start_date = datetime.strptime(sd, '%Y-%m-%d').date()
            elif '/' in sd:
                start_date = datetime.strptime(sd, '%d/%m/%Y').date()
        except Exception:
            if _LOGGER:
                _LOGGER.debug(f"_parse_event_datetime: failed to parse start.date '{sd}'")

    # end.dateTime or end.date
    edt = ev.get('end.dateTime')
    if edt:
        if 'T' in edt:
            try:
                dt = datetime.fromisoformat(edt)
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                dt = dt.astimezone(tz)
                end_time = dt.strftime('%H:%M')
                end_date = dt.date()
            except Exception:
                end_time = edt
                if _LOGGER:
                    _LOGGER.debug(f"_parse_event_datetime: failed to parse end.dateTime '{edt}'")
        else:
            end_time = edt

    ed = ev.get('end.date')
    if ed:
        try:
            if '-' in ed:
                end_date = datetime.strptime(ed, '%Y-%m-%d').date()
            elif '/' in ed:
                end_date = datetime.strptime(ed, '%d/%m/%Y').date()
        except Exception:
            if _LOGGER:
                _LOGGER.debug(f"_parse_event_datetime: failed to parse end.date '{ed}'")

    return start_date, start_time or None, end_date, end_time or None


def _build_body_for_event(ev: dict, tz, today, tomorrow):
    start_date, start_time, end_date, end_time = _parse_event_datetime(ev, tz)

    # Use formatted time if available (from main.py format_event_for_display)
    formatted_start = ev.get('_formatted_time')
    if formatted_start:
        start_time = formatted_start
    # main.py may format end.dateTime as HH:MM; prefer explicit _formatted_end_time if present
    formatted_end = ev.get('_formatted_end_time') or ev.get('end.dateTime')
    if formatted_end and ':' in str(formatted_end):
        end_time = formatted_end

    summary = ev.get('summary', '').strip()

    # Helper to format a date to human DD/MM (no year)
    def _fmt_date_short(d):
        return d.strftime('%d/%m') if d else None

    # Same-day events (or only start date known)
    if start_date and (not end_date or start_date == end_date):
        if start_date == today:
            day_label = 'Oggi'
        elif start_date == tomorrow:
            day_label = 'Domani'
        else:
            day_label = _fmt_date_short(start_date)

        if start_time and end_time:
            return f"{day_label} {start_time} - {end_time}: {summary}"
        if start_time:
            return f"{day_label} {start_time}: {summary}"
        if day_label:
            return f"{day_label}: {summary}"

    # Multi-day events
    if start_date and end_date and start_date != end_date:
        start_str = _fmt_date_short(start_date)
        end_str = _fmt_date_short(end_date)
        # If both have times, include them per day
        if start_time and end_time:
            return f"{start_str} {start_time} - {end_str} {end_time}: {summary}"
        # If only dates, show date range without year
        return f"{start_str} - {end_str}: {summary}"

    # If only end date/time present
    if end_date and not start_date:
        if end_date == today:
            day_label = 'Oggi'
        elif end_date == tomorrow:
            day_label = 'Domani'
        else:
            day_label = _fmt_date_short(end_date)
        if end_time:
            return f"{day_label} {end_time}: {summary}"
        return f"{day_label}: {summary}"

    # Fallbacks: if times exist without dates or nothing parsed
    if start_time and end_time:
        return f"{start_time} - {end_time}: {summary}"
    if start_time:
        return f"{start_time}: {summary}"
    return summary


def _event_start(event):
	"""Aware start (Rome) from start.dateTime, or midnight of start.date; None if unreadable."""
	try:
		if event.get("start.dateTime"):
			dt = datetime.fromisoformat(event["start.dateTime"])
			return (TZ.localize(dt) if dt.tzinfo is None else dt).astimezone(TZ)
		if event.get("start.date"):
			return TZ.localize(datetime.strptime(event["start.date"], "%Y-%m-%d"))
	except ValueError:
		return None
	return None


def _in_day(event, day_start):
	dt = _event_start(event)
	return bool(dt) and day_start <= dt < day_start + timedelta(days=1)


def _for_display(event):
	"""Copy with the time formatted for the body; ISO dates kept for the day labels."""
	e = dict(event)
	try:
		if e.get("start.date"):
			e["start.date"] = datetime.strptime(e["start.date"], "%Y-%m-%d").strftime("%d/%m/%Y")
		if e.get("end.date"):
			e["end.date"] = datetime.strptime(e["end.date"], "%Y-%m-%d").strftime("%d/%m/%Y")
		if e.get("start.dateTime"):
			dt = datetime.fromisoformat(e["start.dateTime"])
			e["_formatted_time"] = (TZ.localize(dt) if dt.tzinfo is None else dt).astimezone(TZ).strftime("%H:%M")
		if e.get("end.dateTime"):
			dt = datetime.fromisoformat(e["end.dateTime"])
			e["end.dateTime"] = (TZ.localize(dt) if dt.tzinfo is None else dt).astimezone(TZ).strftime("%H:%M")
	except ValueError:
		pass
	return e


def _post(session, payload, DB, user_id, device_id, uids):
	"""POST one push; on success record its events for the device. Returns (ok, removed)."""
	headers = {"Content-Type": "application/json"}
	key = os.getenv("NOTIFICATION_API_KEY")
	if key:
		headers["Authorization"] = f"Bearer {key}"
	try:
		resp = session.post(f"{os.getenv('BACKEND_URL', '').rstrip('/')}/user/push/notify", headers=headers, json=payload, timeout=10)
	except requests.RequestException as e:
		_LOGGER.error(f"[push] notify request failed: {e}")
		return False, False
	if resp.status_code != 200:
		_LOGGER.error(f"[push] notify POST failed: {resp.status_code} {resp.text[:200]}")
		return False, resp.status_code in (403, 404, 410)
	for uid in uids:
		if uid:
			DB.store_push_sent(user_id, uid, device_id)
	return True, False


def send_push_notification(DB, sub, events, notification_type):
	"""Daily Notification: one push (a summary, or the event when there is one).
	Last Minute: one push per event, stopping if the backend says the device is gone."""
	if not events:
		return
	today = datetime.now(TZ).date()
	tomorrow = today + timedelta(days=1)
	endpoint, user_id, device_id = sub["endpoint"], sub["id"], sub["device_id"]
	with requests.Session() as s:
		if notification_type == "Daily Notification":
			count = len(events)
			title = f"Daily Notification ({count} {'evento' if count == 1 else 'eventi'})"
			if count > 1:
				payload = {"title": title, "body": f"Sono previsti {count} eventi.", "url": "/dashboard", "endpoint": endpoint}
			else:
				ev = events[0]
				payload = {"title": title, "body": _build_body_for_event(ev, TZ, today, tomorrow),
				           "url": ev.get("htmlLink", f"/dashboard?id={ev.get('uid', '')}"), "endpoint": endpoint}
			_post(s, payload, DB, user_id, device_id, [e.get("uid") for e in events])
			return
		for ev in events:
			payload = {"title": "Nuova variazione dell'orario!", "body": _build_body_for_event(ev, TZ, today, tomorrow),
			           "url": ev.get("htmlLink", f"/dashboard?id={ev.get('uid', '')}"), "endpoint": endpoint}
			ok, removed = _post(s, payload, DB, user_id, device_id, [ev.get("uid")])
			if removed:
				_LOGGER.info(f"[push] device gone, stopping sends to sub {user_id} device {device_id}")
				break


def send_pushes(DB, push_subs, events_today, events_tomorrow, matches):
	"""
	One round of push notifications. events_today / events_tomorrow: the round's events
	with their ISO times (before main.py reformats them for email/Telegram).
	matches: from search_events, or None (word search, as filter_events_kw).
	Returns (devices notified, errors).
	"""
	now = datetime.now(TZ)
	sent_count = errors = 0
	for sub in push_subs:
		try:
			optin = sub.get("notify_optin") or []
			sent = set(DB.get_all_sent_push_id(sub["id"], sub["device_id"]))
			today = remove_sent_events(filter_events_kw(events_today, sub["keywords"], matches, optin), sent)
			tomorrow = remove_sent_events(filter_events_kw(events_tomorrow, sub["keywords"], matches, optin), sent)
			if not (today or tomorrow):
				continue
			if sub["send_push_with_notifications"]:
				# Same timing as email/Telegram (main.py 5.3)
				daily_end = (datetime.combine(now.date(), sub["notification_time"]) + timedelta(minutes=15)).time()
				daily_now = sub["notification_time"] <= now.time() <= daily_end
				if daily_now:
					kind = "Daily Notification"
					events = today + tomorrow if sub["notification_day_before"] else today
				else:
					kind = "Last Minute Notification"
					if sub["notification_day_before"]:
						events = today + tomorrow if now.time() > daily_end else today
					else:
						events = today if now.time() > daily_end else []
			else:
				kind, events = "Last Minute Notification", today + tomorrow
			if not events:
				continue
			send_push_notification(DB, sub, [_for_display(e) for e in events], kind)
			_LOGGER.info(f"[>] Sent push {kind} ({len(events)}) to sub {sub['id']} device {sub['device_id']}.")
			sent_count += 1
		except Exception as e:
			_LOGGER.error(f"[X] Error sending push to sub {sub.get('id')} device {sub.get('device_id')}: {e}")
			errors += 1
	return sent_count, errors
