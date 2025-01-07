from src.logger import Logger
logger = Logger()

import requests
import csv

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
	URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSn-iVUb73XGXN7qWU0S2njYO8yl8LFv0V-1a3VTU7mPB6rJUqYasGPJcmWyc1wGvjDd7IWH3qci75l/pub?gid=0&single=true&output=csv"

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
	
		for event in events:
			# split event summary by spaces and punctuation
			event_summary = event['summary'].split()
			event_summary = [sub_item for item in event_summary for sub_item in item.replace('.', ',').replace('-', ',').split(',') if sub_item]
			# check if keyword is in event summary
			kw_in_summary = keyword.lower() in [word.lower() for word in event_summary]
			if kw_in_summary and event not in filtered_events:
				filtered_events.append(event)
	return filtered_events