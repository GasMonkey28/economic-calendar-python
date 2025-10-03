# main.py - Copy all of this!

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/')
def home():
    """Main endpoint - returns economic calendar"""
    return jsonify({
        "message": "Economic Calendar API",
        "endpoints": {
            "/calendar": "Get economic calendar events",
            "/": "This page"
        }
    })

@app.route('/calendar')
def get_calendar():
    """Scrape and return economic calendar from Investing.com"""
    try:
        url = "https://www.investing.com/economic-calendar/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}"}), 500
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the calendar table
        table = soup.find('table', {'id': 'economicCalendarData'})
        
        if not table:
            return jsonify({"error": "Could not find calendar table"}), 500
        
        # Parse events
        events = []
        rows = table.find_all('tr', {'class': 'js-event-item'})
        
        for row in rows[:50]:  # Limit to 50 events
            try:
                # Extract data
                time_elem = row.find('td', {'class': 'time'})
                country_elem = row.find('td', {'class': 'flagCur'})
                event_elem = row.find('td', {'class': 'event'})
                impact_elem = row.find('td', {'class': 'sentiment'})
                
                # Get impact level (number of bull icons)
                impact = 0
                if impact_elem:
                    impact = len(impact_elem.find_all('i', {'class': 'grayFullBullishIcon'}))
                
                event_data = {
                    'time': time_elem.text.strip() if time_elem else 'TBD',
                    'country': country_elem.get('title', 'N/A') if country_elem else 'N/A',
                    'event': event_elem.text.strip() if event_elem else 'N/A',
                    'impact': impact,
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
                # Try to get actual/forecast/previous values
                try:
                    actual_elem = row.find('td', {'id': lambda x: x and x.startswith('eventActual_')})
                    forecast_elem = row.find('td', {'id': lambda x: x and x.startswith('eventForecast_')})
                    previous_elem = row.find('td', {'id': lambda x: x and x.startswith('eventPrevious_')})
                    
                    if actual_elem:
                        event_data['actual'] = actual_elem.text.strip()
                    if forecast_elem:
                        event_data['forecast'] = forecast_elem.text.strip()
                    if previous_elem:
                        event_data['previous'] = previous_elem.text.strip()
                except:
                    pass
                
                events.append(event_data)
                
            except Exception as e:
                continue
        
        return jsonify({
            "status": "success",
            "count": len(events),
            "events": events,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)