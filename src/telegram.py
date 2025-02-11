import os
from dotenv import load_dotenv
import telepot
from urllib3.exceptions import ReadTimeoutError
from time import sleep
from datetime import datetime, timedelta

from src.db import get_tg_offset, update_tg_offset, update_telegram_id

from src.logger import Logger
logger = Logger()

"""
Summary of all the operations involving Telegram.
"""

class Telegram:
    """
    Class methods for the telegram operations.

    Such as:
    - Sending a notification to a chat
    - Sending a welcome message to a user
    - Registering a new user

    Attributes:
        API_KEY (str): The telegram API key.
        bot (telepot.Bot): The telegram bot.
    """

    def __init__(self):
        load_dotenv()
        self.API_KEY = os.getenv('TELEGRAM_API_KEY')
        self.bot = telepot.Bot(self.API_KEY)
        logger.debug("Telegram bot initialized with API key.")

    def chat_notification(self, message: dict) -> None:
        """Sends a notification to the chat through the bot.

        Args:
            message (dict): A dictionary containing the receiver's id and the message to be sent.
        """
        try:
            self.bot.sendMessage(
                message["receiver"], 
                message["body"], 
                parse_mode='MARKDOWN'
            )
            logger.debug(f"Notification sent to {message['receiver']}.")
        except Exception as e:
            logger.debug(f"Failed to send notification: {e}") # most likely the user has blocked the bot

    def user_welcome(self, telegram_id: str) -> None:
        """Sends a welcome confirmation message to the user to notify him
        that the connection between the account id and the service
        has been established with success.

        Args:
            telegram_id (str): The user's telegram id.
        """
        self.chat_notification(message = {
            "receiver": telegram_id, 
            "body": "Registrazione effettuata correttamente. \nAbilita la notifica via telegram nella tua dashboard (https://fn.lkev.in/dashboard / https://ferminotify.sirico.dev/dashboard)" 
        })
        logger.debug(f"Welcome message sent to {telegram_id}.")

    def safe_get_updates(self):
        retries = 3
        
        for i in range(retries):
            try:
                logger.debug(f"Attempt {i+1} to get updates.")
                updates = self.bot.getUpdates(offset=get_tg_offset())
                logger.debug("Successfully retrieved updates.")
                return updates
            except ReadTimeoutError:
                logger.warning(f"ReadTimeoutError on attempt {i+1}.")
                if i < retries - 1:
                    sleep(2 ** i)  # Exponential backoff
                    logger.debug(f"Retrying after {2 ** i} seconds.")
                else:
                    logger.error("Max retries reached. Raising exception.")
                    raise

    def register_new_telegram_user(self, subs: list[dict]) -> None:
        """Associates a telegram account to a subscriber of the service
        using a unique id.

        The id is received in the inbox of the telegram bot and if
        it is present in the database, the user is registered.

        Args:
            subs (list): A list of dictionaries containing the user's info.
        """
        try:
            inbox_messages = self.safe_get_updates()
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return
        # inbox_messages = self.bot.getUpdates(offset=get_tg_offset())
        for message in inbox_messages:
            for sub in subs:
                # The next lines I check if I got messages from any
                # new user or some stranger (first 2 lines to check 
                # if I didn't get messages from groups, last one 
                # check for the message that i got from my new user)
                if "my_chat_member" not in message.keys():
                    try:
                        if ("new_chat_participant" not in message["message"]) and \
                            ("left_chat_participant" not in message["message"]) and \
                            ("document" not in message["message"].keys()):
                            if message["message"]["text"] == sub["telegram"]:
                                user_email = sub["email"]
                                telegram_id = message["message"]["from"]["id"]

                                update_tg_offset(message["update_id"])
                                update_telegram_id(user_email, telegram_id)
                                self.user_welcome(telegram_id)
                                logger.info(f"User {user_email} registered with telegram ID {telegram_id}.")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        logger.error(f"Message causing error: {message}")
                        
###############################################
#                                             #
#                                             #
#           HANDLE USER REGISTRATION          #
#                                             #
#                                             #
###############################################

def register_new_telegram_user(subs: list[dict]) -> None:
    """Associates a telegram account to a subscriber of the service.

    Args:
        subs (list): A list of dictionaries containing the user's info.
    """
    TG = Telegram()
    TG.register_new_telegram_user(subs)
    logger.debug("New telegram user registration process completed.")
    

################################################
#                                              #
#                                              #
#          USER NOTIFICATION MESSAGE           #
#                                              #
#                                              #
################################################

def tg_notification(sub: dict, events: list, type: str) -> None:
    """Sends a notification to the user through telegram.

    Args:
        sub (dict): A dictionary containing the user's info.
        events (list): A list of events to notify.
        type (str): The type of notification.
    """

    if str(sub["telegram"])[0] == 'X':
        # Exit the function when the user did not connect telegram.
        logger.error("User did not connect telegram. Exiting notification function.")
        return

    message = {
        "receiver": sub["telegram"]
    }
    try:
        message["body"] = get_tg_message(sub, events, type)
    except Exception as e:
        raise Exception(f"Error generating Telegram message: {e}")

    TG = Telegram()
    TG.chat_notification(message)
    logger.debug(f"Telegram notification sent to {sub['email']}.")

    return

def get_tg_message(sub: dict, events: list, type: str) -> str:
    body = ""
    try:
        if type == "Daily Notification":
            body += f"""Ciao {sub["name"]}, ci sono degli eventi previsti:\n"""
        else:
            body += f"""Ciao {sub["name"]},\nabbiamo trovato {len(events)} """
            body += f"event{'i' if len(events) > 1 else 'o'} dell'ultimo minuto:\n"

        # Get today and tomorrow's events (if any) from events[0] and events[1]
        events_today = events[0] if len(events) > 0 else []
        events_tomorrow = events[1] if len(events) > 1 else []

        giorns = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

        if len(events_today) > 0:
            body += f"\n*Oggi* {giorns[datetime.now().weekday()]} {datetime.now().strftime('%d/%m')}:\n"
            body += get_tg_event_body(events_today)

        if len(events_tomorrow) > 0:
            body += f"\n*Domani* {giorns[(datetime.now() + timedelta(days=1)).weekday()]} {(datetime.now() + timedelta(days=1)).strftime('%d/%m')}:\n"
            body += get_tg_event_body(events_tomorrow)
            
        body += "\nBuona giornata <3\n_Fermi Notify Team_\n"
        body += "mail@fn.lkev.in"
        logger.debug(f"Generated daily notification Telegram message for {sub['email']}.")
        return body
    except Exception as e:
        raise e

def get_tg_event_body(events: list) -> str:
    body = ""
    for _ in events:
        body += f"""\n· `{_["summary"]}`"""

        # if event has same start and end date/time (es. entrata posticipata)
        if _["start.date"] == _["end.date"] and _["start.dateTime"] == _["end.dateTime"]:
            if _["start.dateTime"] != None:
                body += "\n· *Orario* 📅 "
            else:
                body += "\n· *Data* 📅 "
            body += _["start.dateTime"] if _["start.dateTime"] else _["start.date"]
        # if event has same start date but different end date/time
        else:
            body += "\n· *Inizio* ⏰ "
            body += _["start.dateTime"] if _["start.dateTime"] else _["start.date"]
            body += "\n· *Fine* 🔚 "
            body += _["end.dateTime"] if _["end.dateTime"] else _["end.date"]
        body += "\n"
    return body