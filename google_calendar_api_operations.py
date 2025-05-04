from googleapiclient.discovery import build
from datetime import datetime

class GoogleCalendarAPIOperationsExecutor:
    def __init__(self, creds, calendar_id):
        self.creds = creds
        self.calendar_id = calendar_id
        self.default_meeting_name = "Default meeting name created by AI Agent"
        self.default_description = "Default description of meeting created by AI Agent"
        self.default_participants = []
        self.client = build('calendar', 'v3', credentials=self.creds)

    def add_meeting(self, date_begin, date_end, name=None, description=None, participants=None):
        event = {
        'summary': name if name != None else self.default_meeting_name,
        'location': 'Default location',
        'description': description if description != None else self.default_description,
        'start': {
            "dateTime": date_begin,
            "timeZone": "Europe/Moscow"},
        'end': {
            "dateTime": date_end, 
            "timeZone": "Europe/Moscow"},
        'attendees': participants if participants != None else self.default_participants,
        }

        # Call the Calendar API
        event = self.client.events().insert(calendarId='primary', body=event).execute()
        print(f"Event '{event['summary']}' at {event['start']['dateTime']} created: {event.get('htmlLink')}")

    def delete_meeting(self, name):
        events_result = self.client.events().list(
            calendarId=self.calendar_id,
            q=name,  # Search query
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    
        events = events_result.get('items', [])

        if not events:
            print(f"No events found with name: {name}")
            return

        # Delete all matching events
        for event in events:
            self.client.events().delete(
                calendarId=self.calendar_id,
                eventId=event['id']
            ).execute()
            print(f"Event {event['summary']} (ID: {event['id']}) deleted")

    def find_slots(self, date_begin, date_end):
        # Query freebusy API
        freebusy_query = {
            "timeMin": date_begin,
            "timeMax": date_end,
            "items": [{"id": "primary"}],
            "timeZone": "Europe/Moscow"
        }
        
        freebusy_result = self.client.freebusy().query(body=freebusy_query).execute()
        busy_periods = freebusy_result['calendars']['primary']['busy']

        # Get start and end of all busy periods
        busy_slots = []
        for busy_period in busy_periods:
            busy_period_start = datetime.fromisoformat(busy_period['start'])
            busy_period_end = datetime.fromisoformat(busy_period['end'])
            busy_slots.append((busy_period_start, busy_period_end))

        # Get free slots from busy slots list
        initial_free_slots = [(datetime.fromisoformat(date_begin), datetime.fromisoformat(date_end))]
        free_slots = initial_free_slots
        for busy_slot in busy_slots:
            busy_slot_start, busy_slot_end = busy_slot
            for i in range(len(free_slots)):
                if free_slots[i][0] < busy_slot_start < free_slots[i][1] and free_slots[i][0] < busy_slot_end < free_slots[i][1]:
                    new_free_slots = free_slots[:i] + [(free_slots[i][0], busy_slot_start), (busy_slot_end, free_slots[i][1])] + (free_slots[i+1:] if i != len(free_slots)-1 else [])
                    break
                elif free_slots[i][0] < busy_slot_start < free_slots[i][1]:
                    new_free_slots = free_slots[:i] + [(free_slots[i][0], busy_slot_start)] + (free_slots[i+1:] if i != len(free_slots)-1 else [])
                elif free_slots[i][0] < busy_slot_end < free_slots[i][1]:
                    new_free_slots = free_slots[:i] + [(busy_slot_end, free_slots[i][1])] + (free_slots[i+1:] if i != len(free_slots)-1 else [])
            free_slots = new_free_slots

        print(f"Free slots between {datetime.fromisoformat(date_begin)} and {datetime.fromisoformat(date_end)}: {free_slots}")
        return f"Free slots between {datetime.fromisoformat(date_begin)} and {datetime.fromisoformat(date_end)}: {free_slots}"

    def change_meeting(self, name, description=None, date_begin=None, date_end=None, participants=None):
        # List existing events in the calendar
        events = self.client.events().list(calendarId="primary", q=name).execute()

        # Find and update the event
        for event in events.get('items', []):
            if event['summary'] == name:
                print(f"Found event '{event['summary']}' at {event['start']['dateTime']}")
                if description != None:
                    event['description'] = description
                if date_begin != None:
                    event['start']['dateTime'] = date_begin
                if date_end != None:
                    event['end']['dateTime'] = date_end
                if participants != None:
                    event['attendees'] = participants

                changed_event = self.client.events().update(calendarId="primary", eventId=event['id'], body=event).execute()
                print(f"Event '{changed_event['summary']}' at {changed_event['start']['dateTime']} changed: {changed_event.get('htmlLink')}")
                break
        else:
            print("Event not found.")
