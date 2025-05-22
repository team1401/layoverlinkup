# LayoverLinkUp

LayoverLinkUp is a simple web application that helps travelers discover potential meetups during airport layovers. Users can create accounts, add itineraries, join groups, and share travel plans. The app detects overlapping layovers within groups to suggest meetup opportunities.

## Features
- User registration and login
- Profile management with home airport and contact info
- Itinerary management with layover details
- Group system for sharing itineraries
- Matching algorithm that finds overlapping layovers within groups

## Setup
1. Install dependencies:
   ```bash
   pip install flask flask_sqlalchemy werkzeug
   ```
2. Initialize the database:
   ```bash
   flask --app app.py run --reload &
   # Or run `python app.py` then visit /initdb once
   ```
3. Run the app:
   ```bash
   python app.py
   ```

This project is intended as a starting point and demo for LayoverLinkUp.
