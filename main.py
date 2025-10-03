# main.py - Complete fixed version with country extraction

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
            "/health": "Health check",
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
                # Extract basic data
                time_elem = row.find('td', {'class': 'time'})
                event_elem = row.find('td', {'class': 'event'})
                impact_elem = row.find('td', {'class': 'sentiment'})
                
                # Extract country - improved method
                country = 'N/A'
                country_elem = row.find('td', {'class': 'flagCur'})
                if country_elem:
                    # Try to find span with title
                    span = country_elem.find('span')
                    if span and span.get('title'):
                        country = span.get('title')
                    # Or try i tag with title
                    elif country_elem.find('i'):
                        i_tag = country_elem.find('i')
                        if i_tag.get('title'):
                            country = i_tag.get('title')
                    # Or get from td title directly
                    elif country_elem.get('title'):
                        country = country_elem.get('title')
                    # Last resort - check for flag class names
                    else:
                        flag_span = country_elem.find('span', class_='ceFlags')
                        if flag_span:
                            classes = flag_span.get('class', [])
                            for cls in classes:
                                if cls.startswith('ceFlags_'):
                                    country = cls.replace('ceFlags_', '').upper()
                                    break
                
                # Get impact level (number of bull icons)
                impact = 0
                if impact_elem:
                    bulls = impact_elem.find_all('i', {'class': 'grayFullBullishIcon'})
                    impact = len(bulls)
                
                event_data = {
                    'time': time_elem.text.strip() if time_elem else 'TBD',
                    'country': country,
                    'event': event_elem.text.strip() if event_elem else 'N/A',
                    'impact': impact,
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                
                # Try to get actual/forecast/previous values
                try:
                    actual_elem = row.find('td', {'id': lambda x: x and x.startswith('eventActual_')})
                    forecast_elem = row.find('td', {'id': lambda x: x and x.startswith('eventForecast_')})
                    previous_elem = row.find('td', {'id': lambda x: x and x.startswith('eventPrevious_')})
                    
                    if actual_elem and actual_elem.text.strip():
                        event_data['actual'] = actual_elem.text.strip()
                    else:
                        event_data['actual'] = ''
                        
                    if forecast_elem and forecast_elem.text.strip():
                        event_data['forecast'] = forecast_elem.text.strip()
                    else:
                        event_data['forecast'] = ''
                        
                    if previous_elem and previous_elem.text.strip():
                        event_data['previous'] = previous_elem.text.strip()
                    else:
                        event_data['previous'] = ''
                except:
                    event_data['actual'] = ''
                    event_data['forecast'] = ''
                    event_data['previous'] = ''
                
                events.append(event_data)
                
            except Exception as e:
                # Skip problematic rows
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