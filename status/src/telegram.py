import os
from dotenv import load_dotenv
import telepot

class Telegram:

	def __init__(self):
		load_dotenv()
		self.API_KEY = os.getenv('TELEGRAM_API_KEY')
		self.bot = telepot.Bot(self.API_KEY)

	def chatMessage(self, message: dict):
		try:
			response = self.bot.sendMessage(
				message["receiver"], 
				message["body"],
				parse_mode='MARKDOWN'
			)
			return response
		except Exception as e:
			pass
		
	def deleteMessage(self, message_id) -> None:
		try:
			self.bot.deleteMessage(telepot.message_identifier(message_id))
		except Exception as e:
			pass
						

def tg_notification(receiver: int, body: str):

	message = {
		"receiver": receiver,
		"body": body
	}

	TG = Telegram()
	return TG.chatMessage(message)

def delete_message(message_id) -> None:
	TG = Telegram()
	TG.deleteMessage(message_id)