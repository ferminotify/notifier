import os
import time
from dotenv import load_dotenv
import psycopg2

class DB():

	def __init__(self):
		load_dotenv(override=True)
		# Inizializzatore della connessione
		HOSTNAME = os.getenv('HOSTNAME')
		DATABASE = os.getenv('DATABASE')
		USERNAME = os.getenv('USERNAME')
		PASSWORD = os.getenv('PASSWORD')
		PORT_ID = os.getenv('PORT_ID')

		try:
			self.connection = psycopg2.connect(
				host=HOSTNAME,
				dbname=DATABASE,
				user=USERNAME,
				password=PASSWORD,
				port=PORT_ID,
			)
		except Exception as e:
			time.sleep(30)
			DB()

		self.cursor = self.connection.cursor()

	def close_connection(self) -> None:
		self.connection.close()
		return
	
	def get_notifier_status(self) -> str:
		self.cursor.execute(f"SELECT * FROM logs_notifier ORDER BY timestamp DESC LIMIT 1")
		response = self.cursor.fetchall()
		self.connection.commit()
		return response[0][1]
	
	def get_notifier_log_last(self) -> list:
		self.cursor.execute(f"SELECT * FROM logs_notifier ORDER BY timestamp DESC LIMIT 1")
		response = self.cursor.fetchall()
		self.connection.commit()
		return response