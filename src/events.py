from src.logger import Logger
logger = Logger()

import os
import requests
import csv
import re
import unicodedata
from datetime import datetime, timedelta
import pytz

"""
All the operations involving the Fermi Calendar and its events.
"""

def get_events() -> list[dict]:
	"""
	Get events from Google Sheets as a CSV file.

	This file is obtained through a Google Script that takes the events from the
	Fermi Calendar
	and puts them in a CSV file.
	The events in the file get deleted after a day to optimize the operations.

	Returns:
		list: list of dictionaries containing all the events.
	"""
	URL = "https://docs.google.com/spreadsheets/d/1ADaUVRQeYU078-suUxGk0u1aMj_GbcjsAzG11YlMp5g/export?format=csv&id=1ADaUVRQeYU078-suUxGk0u1aMj_GbcjsAzG11YlMp5g&gid=0"

	data = []
	try:
		response = requests.get(URL)
		response.raise_for_status()
		logger.debug("Successfully fetched events from Google Sheets.")

		decoded_content = response.content.decode('utf-8')
		csv_reader = csv.DictReader(decoded_content.splitlines(), delimiter=',')
		for row in csv_reader:
			data.append(row)
		logger.debug("Successfully parsed CSV data into a list of dictionaries.")
	except requests.exceptions.RequestException as e:
		logger.error(f"Error fetching events from Google Sheets: {e}")
	except Exception as e:
		logger.error(f"Error processing CSV data: {e}")

	return data

def _words(text: str, keyword: bool = False) -> list[str]:
	"""
	Upper-case words without accents: "Cracò" -> ["CRACO"], "5 CIIN" -> ["5CIIN"].
	In keywords the ordinal marks and dots go too ("5ºCIIN", "3A." -> "5CIIN", "3A").
	Same rules as the backend (utils/timetable/keywords.js).
	"""
	text = unicodedata.normalize("NFD", str(text or "")).upper()
	text = "".join(c for c in text if not unicodedata.combining(c))
	if keyword:
		text = re.sub(r"[ºª°.^]", "", text)
	text = re.sub(r"\b([1-5])\s+([A-Z])", r"\1\2", text)  # "3 CIIN"
	return [w for w in re.split(r"[^A-Z0-9]+", text) if w]

def _title_has(summary: str, keyword: str) -> bool:
	"""The keyword's words in a row in the title, as whole words."""
	kw = _words(keyword, keyword=True)
	if not kw:
		return False
	w = _words(summary)
	return any(w[i:i + len(kw)] == kw for i in range(len(w) - len(kw) + 1))

def _from_backend(ev: dict) -> dict:
	"""
	Backend event {uid, summary, date, start, end, allDay} as a CSV row (get_events), the
	format the rest of the notifier reads: Rome times with offset, all-day end exclusive.
	"""
	row = {"uid": ev["uid"], "summary": ev["summary"], "description": "",
	       "start.date": "", "start.dateTime": "", "start.timeZone": "Europe/Rome",
	       "end.date": "", "end.dateTime": "", "end.timeZone": "Europe/Rome"}
	if ev.get("allDay") or not ev.get("start"):
		day = datetime.strptime(ev["date"], "%Y-%m-%d")
		row["start.date"] = day.strftime("%Y-%m-%d")
		row["end.date"] = (day + timedelta(days=1)).strftime("%Y-%m-%d")
		return row
	rome = pytz.timezone("Europe/Rome")
	at = lambda hm: rome.localize(datetime.strptime(f"{ev['date']} {hm}", "%Y-%m-%d %H:%M")).isoformat()
	row["start.dateTime"] = at(ev["start"])
	row["end.dateTime"] = at(ev.get("end") or ev["start"])
	return row

def search_events(keywords: list[str], date_from: str, date_to: str) -> dict | None:
	"""
	The events of those days (YYYY-MM-DD, included) that concern the keywords, from the
	backend: the same endpoint and rules as "Cerca eventi" and the timetable page (whole
	years like "CLASSI PRIME", joint classes, teachers' names, rooms), on the school calendar.

	Returns:
		dict: {"events": [CSV-like rows], "matches": keyword -> set of uids,
		"optional": keyword -> category -> set of uids}, or None when the backend is not
		reachable (the caller then reads the CSV and searches the words itself). "optional":
		opt-in activities (help desks…) reaching the keyword's class only through its year,
		sent only to users with that category in notify_optin.
	"""
	url = os.getenv("BACKEND_URL")
	key = os.getenv("NOTIFICATION_API_KEY")
	if not url or not key:
		return None
	try:
		response = requests.post(
			f"{url.rstrip('/')}/timetable/search",
			json={"keywords": sorted(set(keywords)), "from": date_from, "to": date_to},
			headers={"Authorization": f"Bearer {key}"},  # the notifier skips the public limits
			timeout=60,  # the backend may be waking up
		)
		response.raise_for_status()
		data = response.json()
		logger.debug(f"Backend: {len(data['events'])} events for {len(data['matches'])} keywords.")
		return {
			"events": [_from_backend(e) for e in data["events"]],
			"matches": {kw: set(uids) for kw, uids in data["matches"].items()},
			"optional": {
				kw: {cat: set(uids) for cat, uids in cats.items()}
				for kw, cats in (data.get("optional") or {}).items()
			},
		}
	except Exception as e:
		logger.error(f"Event search on the backend failed, using the CSV: {e}")
		return None

def filter_events_kw(events, keywords, matches: dict | None = None, optin=()):
	"""
	Events that concern any of the keywords: from the backend's matches when available
	(plus the opt-in categories the user chose), else (or for a keyword it did not answer)
	the keyword's words in the title.
	"""
	if not keywords:
		return []
	uids = set()
	local = []
	for kw in keywords:
		if matches is not None and kw in matches["matches"]:
			uids |= matches["matches"][kw]
			for cat in optin or ():
				uids |= matches["optional"].get(kw, {}).get(cat, set())
		else:
			local.append(kw)
	return [
		evt for evt in events
		if evt.get("uid") in uids or any(_title_has(evt.get("summary", ""), kw) for kw in local)
	]

def remove_sent_events(events, sent):
	return [event for event in events if event["uid"] not in sent]