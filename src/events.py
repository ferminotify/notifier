from src.logger import Logger
logger = Logger()

import requests
import csv
import re

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
	URL = "https://docs.google.com/spreadsheets/d/1ADaUVRQeYU078-suUxGk0u1aMj_GbcjsAzG11YlMp5g/gviz/tq?tqx=out:csv"

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

def filter_events_kw(events, keywords):
	filtered_events = []

	if not keywords:
		return filtered_events

	for keyword in keywords:

		keyword = re.escape(keyword)
		filtered_events = [
			event for event in events
			if re.search(r"\b" + keyword + r"\b", event.get("summary", ""), re.IGNORECASE)
		]
		
	return filtered_events