import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import imaplib
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('src/email_templates'))
from src.logger import Logger
logger = Logger()
###############################################
#											 #
#											 #
#			   GENERAL PURPOSE			   #
#											 #
#											 #
###############################################

EMAIL_SENDER_INDEX = 0
class Email:

	sender_emails = [
		"master@fn.lkev.in",
	]

	def __init__(self):
		global EMAIL_SENDER_INDEX
		load_dotenv()
		EMAIL_SERVICE_PASSWORD = os.getenv('EMAIL_SERVICE_PASSWORD')
		EMAIL_SERVICE_PORT = os.getenv('EMAIL_SERVICE_PORT')
		EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL')
		self.client = smtplib.SMTP(EMAIL_SERVICE_URL, EMAIL_SERVICE_PORT)
		self.client.starttls()
		self.client.login(self.sender_emails[EMAIL_SENDER_INDEX], EMAIL_SERVICE_PASSWORD)
		logger.debug("SMTP client initialized and started TLS.")

		return

	def __update_sender_index(self) -> None:
		global EMAIL_SENDER_INDEX
		EMAIL_SENDER_INDEX = 0

		"""
		if EMAIL_SENDER_INDEX == 2:
			EMAIL_SENDER_INDEX = 0
		else:
			EMAIL_SENDER_INDEX += 1
		"""

	def notify_admin(self, new_user: str) -> None:
		msg = EmailMessage()
		msg["Subject"] = "Nuovo iscritto Calendar Notifier"
		msg["From"] = \
			f"Fermi Notify Team <{self.sender_emails[EMAIL_SENDER_INDEX]}>"
		msg["To"] = "master@fn.lkev.in"
		msg.set_content(f"Ciao,\n{new_user} si e' iscritto.\n\n\
							Fermi Notify Team")
		self.client.send_message(msg)
		logger.debug(f"Notification email sent to admin for new user: {new_user}.")
		self.__update_sender_index()
		self.save_mail(msg)
		
		return

	def sendHTMLMail(self, receiver: str, subject: str, 
						body: str, html_body: str) -> None:
		global EMAIL_SENDER_INDEX
		data = MIMEMultipart('alternative')
		data["Subject"] = subject
		data["From"] = \
			f"Fermi Notify Team <{self.sender_emails[EMAIL_SENDER_INDEX]}>"
		data["To"] = receiver
		data["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
		part1 = MIMEText(body, "plain")
		part2 = MIMEText(html_body, "html")
		data.attach(part1)
		data.attach(part2)
		
		self.client.sendmail(self.sender_emails[EMAIL_SENDER_INDEX], receiver,
								data.as_string())
		logger.debug(f"HTML email sent to {receiver} with subject: {subject}.")

		self.__update_sender_index()
		self.save_mail(data)

		return
	
	def save_mail(self, msg) -> bool:
		try:
			imap_user = self.sender_emails[EMAIL_SENDER_INDEX]
			imap_password = os.getenv('EMAIL_SERVICE_PASSWORD')
			imap_server = os.getenv('EMAIL_SERVICE_URL')
			
			# Convert the message to bytes for IMAP appending
			email_bytes = msg.as_bytes()
			
			# Connect to IMAP and log in
			with imaplib.IMAP4_SSL(imap_server) as imap:
				imap.login(imap_user, imap_password)
				
				# Select the Sent folder. Adjust the folder name if needed (e.g., "Sent Items" or "[Gmail]/Sent Mail")
				sent_folder = "Sent"
				imap.select(sent_folder)

				aware_datetime = datetime.now(timezone.utc)
				# Append the email to the Sent folder
				imap.append(sent_folder, '', imaplib.Time2Internaldate(aware_datetime), email_bytes)
				logger.debug("Email appended to Sent folder successfully.")

			return True
		except Exception as e:
			logger.error(f"Error saving email to IMAP: {e}")
			return False


	def closeConnection(self) -> None:
		self.client.quit()
		logger.debug("SMTP client connection closed.")
		return

def send_email(email: dict) -> None:
	EM = Email()
	logger.debug(f"Sending email to {email['Receiver']} with subject: {email['Subject']}.")

	EM.sendHTMLMail(
		email["Receiver"], email["Subject"],
		email["Raw"], email["Body"]
	)
	EM.closeConnection()

	return 


def notify_admin(new_user: str) -> None:
	EM = Email()
	logger.info(f"Notifying admin about new user: {new_user}.")

	EM.notify_admin(new_user)
	EM.closeConnection()

	return 

#############################################
#											#
#											#
#		   USER NOTIFICATION EMAIL		  	#
#											#
#											#
#############################################

def email_notification(sub: dict, events: list, type: str) -> None:
	'''
	This function is interfaced with the notifications.py
	'''
	logger.debug(f"Sending {type} email to {sub['email']}.")
	# Prepare the email
	# events are [0] today and [1] tomorrow
	events_today = events[0] if len(events) > 0 else []
	events_tomorrow = events[1] if len(events) > 1 else []
	email = {
		"Receiver": sub["email"],
		"Raw": f"{type}:\n{len(events_today + events_tomorrow)} event{'i' if len(events_today + events_tomorrow) > 1 else 'o'}"
	}
	email["Subject"] = f"{type} ({len(events_today + events_tomorrow)} event{'i' if len(events_today + events_tomorrow) > 1 else 'o'})" if type == 'Daily Notification' else type
	try:
		email["Body"] = get_email_body(sub, events_today, events_tomorrow, type)
	except Exception as e:
		raise e
	logger.debug(f"Generated notification mail body for {sub['email']}.")
	send_email(email)
	return


###############################################
#											  #
#											  #
#			 EMAIL FORMATTING				  #
#											  #
#											  #
###############################################
def get_email_body(sub: dict, events_today: list, events_tomorrow: list, type: str) -> str:
	'''
	Get the HTML body of the email.
	'''
	try:

		giorns = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

		# data to render
		data = {
			'title': "Eventi previsti" if type == "Daily Notification" else "Nuovo evento",
			'greetings': "Ciao" if not type == "Daily Notification" else "Buongiorno" if datetime.now().hour < 12 else "Buon pomeriggio" if datetime.now().hour < 18 else "Buonasera",
			'name': sub["name"],
			'gender': 'o' if sub["gender"] == "M" else 'a' if sub["gender"] == "F" else 'ǝ',
			'n_events': f"Sono previsti <b>{len(events_today) + len(events_tomorrow)} eventi</b>" if len(events_today) + len(events_tomorrow) > 1 else f"È previsto <b>{len(events_today) + len(events_tomorrow)} evento</b>" if type == "Daily Notification" else f"Abbiamo trovato <b>{len(events_today) + len(events_tomorrow)} nuovi eventi</b>" if len(events_today) + len(events_tomorrow) > 1 else f"Abbiamo trovato <b>{len(events_today) + len(events_tomorrow)} nuovo evento</b>",
			'events_today': events_today,
			'events_tomorrow': events_tomorrow,
			'date_today': f"{giorns[datetime.now().weekday()]} {datetime.now().strftime('%d/%m')}",
			'date_tomorrow': f"{giorns[(datetime.now() + timedelta(days=1)).weekday()]} {(datetime.now() + timedelta(days=1)).strftime('%d/%m')}",
		}
		
		template = env.get_template('mail_notification.min.html')
		body = template.render(data)

		return body
	except Exception as e:
		raise Exception(f"Error generating email body: {e}")
