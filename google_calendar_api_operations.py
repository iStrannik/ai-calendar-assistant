from googleapiclient.discovery import build

class GoogleCalendarAPIOperationsExecutor:
    def __init__(self, creds, calendar_id):
        self.creds = creds
        self.calendar_id = calendar_id
        self.client = build('calendar', 'v3', credentials=self.creds)

    def add_meeting(self, date_begin, date_end, name, description, participants):
        event = {
        'summary': name,
        'location': 'Default location',
        'description': description,
        'start': {
            "dateTime": date_begin,
            "timeZone": "Europe/Moscow"},
        'end': {
            "dateTime": date_end, 
            "timeZone": "Europe/Moscow"},
        'attendees': participants,
        }

        # Call the Calendar API
        event = self.client.events().insert(calendarId='primary', body=event).execute()
        print(event)
        print(f"Event created: {event.get('htmlLink')}")

    def delete_meeting(self, name):
        events_result = self.client.events().list(
            calendarId=self.calendar_id,
            q=name,  # Search query
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    
        events = events_result.get('items', [])

        if not events:
            print(f"No events found with name: {meeting_name}")
            return

        # Delete all matching events (or you could choose the first one)
        for event in events:
            self.client.events().delete(
                calendarId=self.calendar_id,
                eventId=event['id']
            ).execute()
            print(f"Deleted event: {event['summary']} (ID: {event['id']})")

    def find_slots(self):
        pass

    def change_meeting(self):
        pass
