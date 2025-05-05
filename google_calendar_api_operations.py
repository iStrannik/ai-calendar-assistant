from googleapiclient.discovery import build
from datetime import datetime
from babel.dates import format_datetime
import pytz

class GoogleCalendarAPIOperationsExecutor:
    def __init__(self, creds, calendar_id, timezone):
        self.creds = creds
        self.calendar_id = calendar_id
        self.timezone = timezone
        self.default_meeting_name = "Default meeting name created by AI Agent"
        self.default_meeting_location = "Default meeting location created by AI Agent"
        self.default_meeting_description = "Default description of meeting created by AI Agent"
        self.default_meeting_participants = []
        self.client = build('calendar', 'v3', credentials=self.creds)

    def add_meeting(self, date_begin, date_end, name=None, description=None, participants=None):
        event = {
        'summary': name if name != None else self.default_meeting_name,
        'location': self.default_meeting_location,
        'description': description if description != None else self.default_meeting_description,
        'start': {
            "dateTime": date_begin,
            "timeZone": self.timezone},
        'end': {
            "dateTime": date_end, 
            "timeZone": self.timezone},
        'attendees': participants if participants != None else self.default_meeting_participants,
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
        tz = pytz.timezone(self.timezone)

        # Parse input and attach timezone (assumes input is naive ISO string)
        date_begin_dt = tz.localize(datetime.fromisoformat(date_begin))
        date_end_dt = tz.localize(datetime.fromisoformat(date_end))

        # Query freebusy API
        freebusy_query = {
            "timeMin": date_begin_dt.isoformat(),
            "timeMax": date_end_dt.isoformat(),
            "items": [{"id": "primary"}],
            "timeZone": self.timezone
        }

        freebusy_result = self.client.freebusy().query(body=freebusy_query).execute()
        busy_periods = freebusy_result['calendars']['primary']['busy']

        # Convert busy slots to datetime with timezone
        busy_slots = []
        for busy_period in busy_periods:
            busy_start = datetime.fromisoformat(busy_period['start'])
            busy_end = datetime.fromisoformat(busy_period['end'])

            # Convert to same timezone if not already
            if busy_start.tzinfo is None:
                busy_start = tz.localize(busy_start)
            else:
                busy_start = busy_start.astimezone(tz)

            if busy_end.tzinfo is None:
                busy_end = tz.localize(busy_end)
            else:
                busy_end = busy_end.astimezone(tz)

            busy_slots.append((busy_start, busy_end))

        # Initial free time
        free_slots = [(date_begin_dt, date_end_dt)]

        for busy_start, busy_end in busy_slots:
            updated_slots = []
            for slot_start, slot_end in free_slots:
                if slot_start < busy_start < slot_end and slot_start < busy_end < slot_end:
                    updated_slots.extend([(slot_start, busy_start), (busy_end, slot_end)])
                elif slot_start < busy_start < slot_end:
                    updated_slots.append((slot_start, busy_start))
                elif slot_start < busy_end < slot_end:
                    updated_slots.append((busy_end, slot_end))
                elif busy_start <= slot_start and slot_end <= busy_end:
                    # Whole slot is busy — remove it
                    continue
                else:
                    updated_slots.append((slot_start, slot_end))
            free_slots = updated_slots
            
        readable_slots = [
            f"{format_datetime(slot_start, format='d MMMM HH:mm', locale='ru_RU')}–{format_datetime(slot_end, format='HH:mm', locale='ru_RU')}"
            for slot_start, slot_end in free_slots
        ]

        result = "Свободные слоты:\n" + "\n".join(readable_slots)
        print(result)
        return result

        # print(f"Free slots between {date_begin_dt} and {date_end_dt}: {free_slots}")
        # return f"Free slots between {date_begin_dt} and {date_end_dt}: {free_slots}"


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