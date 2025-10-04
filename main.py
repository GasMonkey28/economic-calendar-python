# main.py - Forex Factory scraper with DEBUG logging

from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Economic Calendar API (Forex Factory)",
        "endpoints": {
            "/calendar": "Get economic calendar events",
            "/calendar/debug": "Get debug info about date parsing",
            "/health": "Health check"
        }
    })

@app.route('/calendar/debug')
def get_calendar_debug():
    """Debug endpoint to see what dates are being found"""
    try:
        url = "https://www.forexfactory.com/calendar"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        debug_info = []
        rows = soup.find_all('tr', class_='calendar__row')[:20]  # First 20 rows
        
        for i, row in enumerate(rows):
            date_cell = row.find('td', class_='calendar__cell calendar__date')
            event_cell = row.find('td', class_='calendar__cell calendar__event')
            
            row_info = {
                'row_number': i,
                'date_cell_html': str(date_cell)[:200] if date_cell else None,
                'date_cell_text': date_cell.get_text(strip=True) if date_cell else None,
                'event': event_cell.get_text(strip=True) if event_cell else None
            }
            debug_info.append(row_info)
        
        return jsonify({"debug_rows": debug_info})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/calendar')
def get_calendar():
    try:
        weeks_param = request.args.get('weeks', '2')
        num_weeks = int(weeks_param) if weeks_param.isdigit() else 2
        
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7 * num_weeks - 1)
        
        url = "https://www.forexfactory.com/calendar"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        current_date = today
        date_updates = []  # Track when dates change for debugging
        
        rows = soup.find_all('tr', class_='calendar__row')
        
        for row in rows:
            try:
                date_cell = row.find('td', class_='calendar__cell calendar__date')
                if date_cell:
                    date_text = date_cell.get_text(strip=True)
                    
                    if date_text:
                        old_date = current_date
                        
                        if date_text.lower() == 'today':
                            current_date = today
                        elif date_text.lower() == 'tomorrow':
                            current_date = today + timedelta(days=1)
                        elif date_text.lower() == 'yesterday':
                            current_date = today - timedelta(days=1)
                        else:
                            try:
                                date_text_clean = ' '.join(date_text.split())
                                current_date = datetime.strptime(f"{date_text_clean} {today.year}", "%a %b %d %Y").date()
                                
                                if current_date < today - timedelta(days=180):
                                    current_date = datetime.strptime(f"{date_text_clean} {today.year + 1}", "%a %b %d %Y").date()
                            except:
                                pass
                        
                        if old_date != current_date:
                            date_updates.append({
                                'text': date_text,
                                'parsed_date': current_date.strftime('%Y-%m-%d')
                            })
                
                if current_date < week_start or current_date > week_end:
                    continue
                
                time_cell = row.find('td', class_='calendar__cell calendar__time')
                currency_cell = row.find('td', class_='calendar__cell calendar__currency')
                impact_cell = row.find('td', class_='calendar__cell calendar__impact')
                event_cell = row.find('td', class_='calendar__cell calendar__event')
                
                if not event_cell or not event_cell.get_text(strip=True):
                    continue
                
                country = currency_cell.get_text(strip=True) if currency_cell else 'N/A'
                
                if country != 'USD':
                    continue
                
                impact = 0
                if impact_cell:
                    impact_span = impact_cell.find('span')
                    if impact_span:
                        impact_class = ' '.join(impact_span.get('class', []))
                        if 'high' in impact_class.lower():
                            impact = 3
                        elif 'medium' in impact_class.lower():
                            impact = 2
                        elif 'low' in impact_class.lower():
                            impact = 1
                
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
            "date_updates_found": date_updates,  # Show what dates were parsed
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