# Calendar Sync

Sync loughborough's student timetable calendar with Google Calendar via webscraping and the GCal API

## Use

1. Launch the module e.g. `python gregle`
2. Within the opened browser, sign-in to lboro with your normal credentials.
3. Authenticate Duo if required.
4. Once the timetable is visable, do **NOT** interact with anything.
5. Wait for the program to cycle through all the weeks of the timetable.
6. The window will close automatically.
7. A new window will popopen for a google sign-in.
8. Sign-in to the desired google account and authenticate the app.
9. Follow the prompts on screen.
10. Wait for the program to finish.

## Requirements

- An empty google calendar named `Timetable` on a google account.
- Ensure all required resources are found in [/res](./res/README.md)
