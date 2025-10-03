# main.py - Filter for US events this week and next week

from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

app = Flask(__name__)

@app.route('/')
def home():
    """Main endpoint - returns economic calendar"""
    return jsonify({
        "message": "Economic Calendar API",
        "endpoints": {
            "/calendar": "Get economic calendar events (default: US only, this week + next week)",
            "/calendar?weeks=1": "Get only this week",
            "/calendar?weeks=2": "Get this week + next week (default)",
            "/calendar?country=all": "Get all countries",
            "/health": "Health check",
            "/": "This page"
        }
    })

@app.route('/calendar')
def get_calendar():
    """Scrape and return economic calendar from Investing.com"""
    try:
        # Get query parameters
        weeks_param = request.args.get('weeks', '2')  # Default: 2 weeks
        country_filter = request.args.get('country', 'US')  # Default: US only
        
        try:
            num_weeks = int(weeks_param)
        except:
            num_weeks = 2
        
        # Calculate date range
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())  # This Monday
        week_end = week_start + timedelta(days=7 * num_weeks - 1)  # End of period
        
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
        table = soup.find('table', {'id': 'economicCalendarData'})
        
        if not table:
            return jsonify({"error": "Could not find calendar table"}), 500
        
        events = []
        rows = table.find_all('tr', {'class': 'js-event-item'})
        
        # Track current date from headers
        current_date = today
        
        for row in rows:
            try:
                # Check if this row has a date attribute
                event_date_attr = row.get('data-event-datetime')
                if event_date_attr:
                    try:
                        # Parse date from timestamp (format: 2025/10/03)
                        current_date = datetime.strptime(event_date_attr.split()[0], '%Y/%m/%d').date()
                    except:
                        pass
                
                # Skip if date is outside our range
                if current_date < week_start or current_date > week_end:
                    continue
                
                # Extract event data
                time_elem = row.find('td', {'class': 'time'})
                event_elem = row.find('td', {'class': 'event'})
                impact_elem = row.find('td', {'class': 'sentiment'})
                
                # Extract country
                country = 'N/A'
                country_elem = row.find('td', {'class': 'flagCur'})
                if country_elem:
                    span = country_elem.find('span')
                    if span and span.get('title'):
                        country = span.get('title')
                    elif country_elem.find('i'):
                        i_tag = country_elem.find('i')
                        if i_tag.get('title'):
                            country = i_tag.get('title')
                    elif country_elem.get('title'):
                        country = country_elem.get('title')
                    else:
                        flag_span = country_elem.find('span', class_='ceFlags')
                        if flag_span:
                            classes = flag_span.get('class', [])
                            for cls in classes:
                                if cls.startswith('ceFlags_'):
                                    country = cls.replace('ceFlags_', '').upper()
                                    break
                
                # Filter by country if needed
                if country_filter.lower() != 'all' and country != "United States":
                    continue
                
                # Get impact level
                impact = 0
                if impact_elem:
                    bulls = impact_elem.find_all('i', {'class': 'grayFullBullishIcon'})
                    impact = len(bulls)
                
                event_data = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'time': time_elem.text.strip() if time_elem else 'TBD',
                    'country': country,
                    'event': event_elem.text.strip() if event_elem else 'N/A',
                    'impact': impact,
                }
                
                # Get actual/forecast/previous values
                try:
                    actual_elem = row.find('td', {'id': lambda x: x and x.startswith('eventActual_')})
                    forecast_elem = row.find('td', {'id': lambda x: x and x.startswith('eventForecast_')})
                    previous_elem = row.find('td', {'id': lambda x: x and x.startswith('eventPrevious_')})
                    
                    event_data['actual'] = actual_elem.text.strip() if actual_elem and actual_elem.text.strip() else ''
                    event_data['forecast'] = forecast_elem.text.strip() if forecast_elem and forecast_elem.text.strip() else ''
                    event_data['previous'] = previous_elem.text.strip() if previous_elem and previous_elem.text.strip() else ''
                except:
                    event_data['actual'] = ''
                    event_data['forecast'] = ''
                    event_data['previous'] = ''
                
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
            "filter": {
                "country": "United States" if country_filter.lower() != 'all' else "All countries"
            },
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