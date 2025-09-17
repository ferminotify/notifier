'''
send custom HTML email from mail@fn.lkev.in
'''

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import imaplib
from datetime import datetime, timezone

def sendHTMLMail(client, sender: str, receiver: str, subject: str, body: str, html_body: str) -> None:
	data = MIMEMultipart('alternative')
	data["Subject"] = subject
	data["From"] = \
		f"Fermi Notify Team <{sender}>"
	data["To"] = receiver
	data["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
	part1 = MIMEText(body, "plain")
	part2 = MIMEText(html_body, "html")
	data.attach(part1)
	data.attach(part2)
	
	client.sendmail(sender, receiver,
							data.as_string())

	save_mail(data)

	return

def save_mail(msg) -> bool:
	try:
		imap_user = EMAIL_SERVICE_USERNAME
		imap_password = os.getenv('EMAIL_SERVICE_PASSWORD')
		imap_server = os.getenv('EMAIL_SERVICE_SAVE_URL')
		
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

		return True
	except Exception as e:
		return False
	


dest = input("destination email address: ")

dest_domain = dest.split('@')[1]
# Load environment variables from .env file
load_dotenv()
if dest_domain == "fermimn.edu.it":
	# Self hosted
	EMAIL_SERVICE_PASSWORD = os.getenv('EMAIL_SERVICE_PASSWORD')
	EMAIL_SERVICE_PORT = os.getenv('EMAIL_SERVICE_PORT')
	EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL')
else:
	# Mailgun
	EMAIL_SERVICE_PASSWORD = os.getenv('EMAIL_SERVICE_PASSWORD')
	EMAIL_SERVICE_PORT = os.getenv('EMAIL_SERVICE_PORT')
	EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_MAILGUN_URL')

print(f"Using email service URL: {EMAIL_SERVICE_URL}")

subject = input("email subject: ")
html = input("html file path: ")


EMAIL_SERVICE_USERNAME = "mail@fn.lkev.in"
client = smtplib.SMTP(EMAIL_SERVICE_URL, EMAIL_SERVICE_PORT)
client.starttls()
client.login(EMAIL_SERVICE_USERNAME, EMAIL_SERVICE_PASSWORD)

# Load the HTML email
with open(html, 'r', encoding='utf-8') as file:
	html_content = file.read()

# Prepare the plain text version of the email
plain = input("plain text version of the email: ")

# Send the email
try:
	sendHTMLMail(client, EMAIL_SERVICE_USERNAME, dest, subject, plain, html_content)
	print("Email sent successfully!")
except Exception as e:
	print(f"Failed to send email: {e}")
	use_azure = input("Use Azure for sending email? (yes/no): ").strip().lower()
	if use_azure == 'yes':
		# try with azure
		EMAIL_SERVICE_PASSWORD = os.getenv('EMAIL_SERVICE_AZURE_PASSWORD')
		EMAIL_SERVICE_PORT = os.getenv('EMAIL_SERVICE_PORT')
		EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_AZURE_URL')
		EMAIL_SERVICE_USERNAME = os.getenv('EMAIL_SERVICE_AZURE_USERNAME')
		EMAIL_SERVICE_USERNAME = "donotreply@fn.lkev.in"
		try:
			sendHTMLMail(client, EMAIL_SERVICE_USERNAME, dest, subject, plain, html_content)
			print("Email sent successfully with Azure!")
		except Exception as e:
			print(f"Failed to send email: {e}")