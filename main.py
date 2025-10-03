# main.py - Forex Factory scraper (no Selenium needed)

from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Economic Calendar API (Forex Factory)",
        "endpoints": {
            "/calendar": "Get economic calendar events",
            "/health": "Health check"
        }
    })

@app.route('/calendar')
def get_calendar():
    try:
        weeks_param = request.args.get('weeks', '2')
        num_weeks = int(weeks_param) if weeks_param.isdigit() else 2
        
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7 * num_weeks - 1)
        
        # Forex Factory URL - includes this week and next week by default
        url = "https://www.forexfactory.com/calendar"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        current_date = today
        
        # Find all calendar rows
        rows = soup.find_all('tr', class_='calendar__row')
        
        for row in rows:
            try:
                # Check if this is a date header row
                date_cell = row.find('td', class_='calendar__cell calendar__date')
                if date_cell and date_cell.get_text(strip=True):
                    date_text = date_cell.get_text(strip=True)
                    try:
                        # Parse date like "Fri Oct 4"
                        current_date = datetime.strptime(f"{date_text} {today.year}", "%a %b %d %Y").date()
                    except:
                        pass
                
                # Skip if outside date range
                if current_date < week_start or current_date > week_end:
                    continue
                
                # Extract event details
                time_cell = row.find('td', class_='calendar__cell calendar__time')
                currency_cell = row.find('td', class_='calendar__cell calendar__currency')
                impact_cell = row.find('td', class_='calendar__cell calendar__impact')
                event_cell = row.find('td', class_='calendar__cell calendar__event')
                
                if not event_cell:
                    continue
                
                # Get country/currency
                country = currency_cell.get_text(strip=True) if currency_cell else 'N/A'
                
                # Filter for USD (US events)
                if country != 'USD':
                    continue
                
                # Get impact level
                impact = 0
                if impact_cell:
                    impact_span = impact_cell.find('span')
                    if impact_span:
                        impact_class = impact_span.get('class', [])
                        if 'high' in str(impact_class):
                            impact = 3
                        elif 'medium' in str(impact_class):
                            impact = 2
                        elif 'low' in str(impact_class):
                            impact = 1
                
                # Get actual/forecast/previous
                actual_cell = row.find('td', class_='calendar__cell calendar__actual')
                forecast_cell = row.find('td', class_='calendar__cell calendar__forecast')
                previous_cell = row.find('td', class_='calendar__cell calendar__previous')
                
                event_data = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'time': time_cell.get_text(strip=True) if time_cell else 'TBD',
                    'country': 'United States',
                    'event': event_cell.get_text(strip=True),
                    'impact': impact,
                    'actual': actual_cell.get_text(strip=True) if actual_cell else '',
                    'forecast': forecast_cell.get_text(strip=True) if forecast_cell else '',
                    'previous': previous_cell.get_text(strip=True) if previous_cell else ''
                }
                
                events.append(event_data)
                
            except Exception as e:
                continue
        
        return jsonify({
            "status": "success",
            "count": len(events),
            "date_range": {
                "start": week_start.strftime('%Y-%m-%d'),
                "end": week_end.strftime('%Y-%m-%d'),
                "weeks": num_weeks
            },
            "filter": {"country": "United States"},
            "events": events,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)