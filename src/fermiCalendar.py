import pandas as pd
from src.databaseOperations import get_all_sent_id
from src.utility import is_event_today

"""
Summary of all the operations involving the Fermi Calendar and its events.
"""

def get_events() -> list[dict]:
    """
    Get events from Google Sheets as a CSV file.

    This file is obtained trough a Google Script that takes the events from the
    Fermi Calendar
    and puts them in a CSV file.
    The events in the file get deleted after a day to optimize the operations.

    Returns:
        list: list of dictionaries containing all the events.
    """
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSn-iVUb73XGXN7qWU0S2njYO8yl8LFv0V-1a3VTU7mPB6rJUqYasGPJcmWyc1wGvjDd7IWH3qci75l/pub?gid=0&single=true&output=csv"

    data = []
    try:
        data = pd.read_csv(URL, sep=',')    # Read CSV file
        data = data.to_numpy(na_value=None) # Convert to numpy array
    except:
        pass
    

    all_events = []
    for i in data:
        evt = {}
        evt["id"] = i[0]
        evt["subject"] = i[1]
        evt["desc"] = i[2]
        evt["startDate"] = i[3]
        evt["startDateTime"] = i[4]
        evt["startTimeZone"] = i[5]
        evt["endDate"] = i[6]
        evt["endDateTime"] = i[7]
        evt["endTimeZone"] = i[8]

        all_events.append(evt)
    
    return all_events

def collect_notifications(subs: list[dict]) -> list[dict]:
    """Collect all the notifications for the subscribers.

    This function gets all the events from the Google Sheets and compares them 
    to the subscribers.
    If there is a match, the subscriber gets notified.

    Args:
        subs (list): list of dictionaries containing all the subscribers.

    Returns:
        list: list of dictionaries containing all the subscribers that need to 
        be notified and
        the corresponding events.
    """
    events = get_events()

    # print("got events")

    notifications = []
    
    c = 0
    all_ids = get_all_sent_id()
    for sub in subs:
        print("start user", c)
        usr_kw = sub["tags"]
        
        # get the sent events ids
        sent = []
        for i in all_ids:
            if str(i[1]) == str(sub["id"]):
                sent.append(i[2])

        user_events = []

        for evt in events:
            if usr_kw:
                try:
                    event_title = "".join(c for c in evt["subject"].lower()
                        if ((c.isalpha() or c.isdecimal()) or c == ' ')) + " "
                except:
                    pass
                kw_in_subject = any(((kw.lower() + " ") in event_title
                                    for kw in usr_kw))
                # I append a space to the keyword so, for example, the user 
                # with the tag 4E doesn't receive the information about the 
                # events of 4EAU
                
                evt_not_in_db = evt["id"] not in sent

                if kw_in_subject and evt_not_in_db and is_event_today(evt):
                    user_events.append(evt)

        if len(user_events) > 0:
            notifications.append({
                "id": sub["id"],
                "name": sub["name"],
                "email": sub["email"],
                "n_pref": sub["n_pref"],
                "telegram": sub["telegram"],
                "events": user_events
            })
        
        print("end user", c)
        c+=1

    return notifications
