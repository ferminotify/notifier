'''
Check the status of the notifier and send a message to the admin if the notifier is down.
Designed to be run as a separate process on another server in order to run backup notifier.
	The backup notifier process connects to another logging table (logs_backup_notifier) to keep checking the status of the main notifier.
'''
from src.db import DB
from src.telegram import tg_notification, delete_message
import os
from time import time, sleep
import subprocess

def main():
	error = False
	error_id = None
	default_sleep = 600
	error_sleep = 300
	script_path = '../main.py'
	process = None
	while True:
		print("===\nChecking status")
		db = DB()
		log = db.get_notifier_log_last()
		if error:
			# check if notifier is back up
			if log[0][1] == "success":
				delete_message(error_id)
				error = False
				print("Notifier up - deleted error message " + str(error_id))
				process.terminate()
				process.wait()
		else:
			if log[0][1] == "error":
				error_id = tg_notification(os.getenv("TELEGRAM_CHAT_ID"), f"***⚠️ Notifier is down***: ```{log[0][2]}```")
				error = True
				print("Notifier down - error message: " + str(error_id))
				process = subprocess.Popen(['python3', script_path])
			else:
				# if more than 10 minutes have passed since the last notification, alert user
				if (time() - log[0][0].timestamp()) > 600:
					error_id = tg_notification(os.getenv("TELEGRAM_CHAT_ID"), f"***⚠️ Notifier is down***: more than 15 minutes have passed since ```{log[0][2]}```")
					error = True
					print("Notifier is loading for more than 15 minutes - error message: " + str(error_id))
					process = subprocess.Popen(['python3', script_path])
		db.close_connection()
		if error:
			print("Sleeping for " + str(error_sleep) + " seconds")
			sleep(error_sleep)
		else:
			print("Sleeping for " + str(default_sleep) + " seconds")
			sleep(default_sleep)

if __name__ == "__main__":
    main()