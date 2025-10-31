# main.py - Fixed version with Investing.com API endpoint

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re

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
        # Create a session to maintain cookies
        session = requests.Session()
        
        # First, visit the main page to get cookies
        main_url = "https://www.investing.com/economic-calendar/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Get initial cookies
        try:
            session.get(main_url, headers=headers, timeout=15)
        except:
            pass
        
        # Now try the API endpoint
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        # Format dates for the API (YYYY-MM-DD)
        date_from = today.strftime('%Y-%m-%d')
        date_to = tomorrow.strftime('%Y-%m-%d')
        
        # Investing.com's internal API endpoint
        api_url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
        
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.investing.com',
            'Referer': 'https://www.investing.com/economic-calendar/',
        }
        
        # Prepare form data - Investing.com expects specific parameters
        # Note: Remove country[] filter to get all countries, or specify countries like 5 (US), 39 (Eurozone), etc.
        # First try with US only, then try all countries if that fails
        form_data_us = {
            'country[]': '5',  # 5 = United States
            'importance[]': '1,2,3',  # 1=Low, 2=Medium, 3=High
            'dateFrom': date_from,
            'dateTo': date_to,
            'timeZone': '55',  # UTC timezone
            'currentTab': 'today',
            'limit_from': '0',
            'limit': '500'  # Request up to 500 events
        }
        
        form_data_all = {
            'importance[]': '1,2,3',  # 1=Low, 2=Medium, 3=High
            'dateFrom': date_from,
            'dateTo': date_to,
            'timeZone': '55',  # UTC timezone
            'currentTab': 'today',
            'limit_from': '0',
            'limit': '500'  # Request up to 500 events
        }
        
        # Try with all countries first (more data), then US-only
        # This ensures we capture all events including US ones that come later
        form_data_list = [form_data_all, form_data_us]
        
        # Try API endpoint first
        for form_data in form_data_list:
            try:
                response = session.post(api_url, headers=api_headers, data=form_data, timeout=15)
                
                if response.status_code == 200:
                    try:
                        # The response might be JSON wrapped in HTML comments or plain JSON
                        response_text = response.text.strip()
                        
                        # Remove HTML comment wrapper if present
                        if response_text.startswith('<!--'):
                            response_text = response_text.split('-->', 1)[1].split('<!--', 1)[0].strip()
                        
                        # Try to parse JSON - it might be in different formats
                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError:
                            # If it's not JSON, it might be HTML directly
                            # Try parsing as HTML
                            soup_test = BeautifulSoup(response_text, 'html.parser')
                            table_test = soup_test.find('table', {'id': 'economicCalendarData'})
                            if table_test:
                                # Response is HTML directly
                                data = {'data': response_text}
                            else:
                                continue
                        
                        # Check if data contains the calendar HTML
                        if 'data' in data or 'html' in data:
                            html_content = data.get('data', data.get('html', ''))
                            
                            if html_content:
                                soup = BeautifulSoup(html_content, 'html.parser')
                                table = soup.find('table', {'id': 'economicCalendarData'})
                                
                                if table:
                                    events = []
                                    rows = table.find_all('tr', {'class': 'js-event-item'})
                                    
                                    for row in rows:  # Process all available events (no limit)
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
                                            
                                            # Only add US events (temporarily showing all for debugging)
                                            # Check multiple possible US country names
                                            if (country == "United States" or 
                                                country == "US" or 
                                                country == "USA" or
                                                country.startswith("United States") or
                                                "US" in country.upper()):
                                                events.append(event_data)
                                            # TEMPORARY: Add all events for debugging (remove this after testing)
                                            # events.append(event_data)
                                            
                                        except Exception as e:
                                            # Skip problematic rows
                                            continue
                                    
                                    if events:
                                        return jsonify({
                                            "status": "success",
                                            "count": len(events),
                                            "events": events,
                                            "timestamp": datetime.now().isoformat(),
                                            "source": "api"
                                        })
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        continue
                else:
                    continue
            except Exception as e:
                continue
        
        # Fallback: Try scraping the main page directly with session
        # Try with date parameter to get today's full calendar
        try:
            # Try with date parameter in URL to get more events
            url = f"https://www.investing.com/economic-calendar/?date={date_from.replace('-', '')}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.investing.com/economic-calendar/',
            }
            
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return jsonify({"error": f"HTTP {response.status_code}", "message": "Failed to fetch calendar data"}), 500
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if there's calendar data in script tags (some sites embed data this way)
            script_tags = soup.find_all('script')
            calendar_data_found = False
            
            for script in script_tags:
                script_text = script.string or ''
                # Look for JSON data embedded in scripts
                if 'economicCalendarData' in script_text or 'js-event-item' in script_text:
                    # Try to extract JSON from script
                    try:
                        # Look for JSON objects in script
                        json_match = re.search(r'\{.*\}', script_text, re.DOTALL)
                        if json_match:
                            try:
                                potential_data = json.loads(json_match.group())
                                if isinstance(potential_data, dict) and ('events' in potential_data or 'data' in potential_data):
                                    # Found calendar data in script
                                    calendar_data_found = True
                                    break
                            except:
                                pass
                    except:
                        pass
            
            # Find the calendar table - try multiple possible table IDs/classes
            table = soup.find('table', {'id': 'economicCalendarData'})
            
            # If not found, try finding by class or other attributes
            if not table:
                tables = soup.find_all('table')
                for t in tables:
                    if 'economic' in t.get('id', '').lower() or 'calendar' in t.get('id', '').lower():
                        table = t
                        break
            
            if not table:
                # Try to find table body or rows directly
                tbody = soup.find('tbody', {'id': 'economicCalendarData'})
                if tbody:
                    table = tbody
                else:
                    # Try finding rows directly
                    rows_direct = soup.find_all('tr', {'class': 'js-event-item'})
                    if rows_direct:
                        # Create a fake table structure for processing
                        table = rows_direct[0].parent if rows_direct else None
            
            if not table:
                return jsonify({
                    "status": "error",
                    "message": "Could not find calendar table. Investing.com may have changed their structure or the calendar loads via JavaScript.",
                    "debug_info": {
                        "response_length": len(response.content),
                        "has_table_tag": bool(soup.find('table')),
                        "page_title": soup.title.string if soup.title else None
                    }
                }), 500
            
            # Parse events - try to find rows in different ways
            events = []
            rows = table.find_all('tr', {'class': 'js-event-item'})
            
            # If no rows found with js-event-item, try other classes
            if not rows:
                rows = table.find_all('tr', class_=lambda x: x and ('event' in str(x).lower() or 'js' in str(x).lower()))
            
            # If still no rows, get all rows from table
            if not rows:
                rows = table.find_all('tr')
            
            for row in rows:  # Process all available events (no limit)
                try:
                    # Extract basic data
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
                        elif country_elem.get('title'):
                            country = country_elem.get('title')
                    
                    # Get impact level
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
                        
                        event_data['actual'] = actual_elem.text.strip() if actual_elem and actual_elem.text.strip() else ''
                        event_data['forecast'] = forecast_elem.text.strip() if forecast_elem and forecast_elem.text.strip() else ''
                        event_data['previous'] = previous_elem.text.strip() if previous_elem and previous_elem.text.strip() else ''
                    except:
                        event_data['actual'] = ''
                        event_data['forecast'] = ''
                        event_data['previous'] = ''
                    
                    # Only add US events (check multiple possible US country names)
                    if (country == "United States" or 
                        country == "US" or 
                        country == "USA" or
                        country.startswith("United States") or
                        "US" in country.upper()):
                        events.append(event_data)
                    # TEMPORARY: Also show all events for debugging
                    # Uncomment the line below to see all events and check what country names exist
                    # events.append(event_data)
                    
                except Exception as e:
                    continue
            
            if events:
                return jsonify({
                    "status": "success",
                    "count": len(events),
                    "events": events,
                    "timestamp": datetime.now().isoformat(),
                    "source": "fallback_scraping"
                })
            else:
                return jsonify({
                    "status": "success",
                    "count": 0,
                    "events": [],
                    "message": "No US events found for today. Try checking all countries or different dates.",
                    "timestamp": datetime.now().isoformat(),
                    "source": "fallback_scraping"
                })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__
            }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }), 500

@app.route('/calendar/all')
def get_calendar_all():
    """Debug endpoint - returns ALL events without US filter"""
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        # First, visit the main page to get cookies
        main_url = "https://www.investing.com/economic-calendar/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        try:
            session.get(main_url, headers=headers, timeout=15)
        except:
            pass
        
        # Try with date parameter
        today = datetime.now()
        date_from = today.strftime('%Y-%m-%d')
        url = f"https://www.investing.com/economic-calendar/?date={date_from.replace('-', '')}"
        
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}"}), 500
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'id': 'economicCalendarData'})
        
        if not table:
            return jsonify({"error": "Could not find calendar table"}), 500
        
        events = []
        rows = table.find_all('tr', {'class': 'js-event-item'})
        
        # Get unique countries for debugging
        countries_found = set()
        
        for row in rows:
            try:
                time_elem = row.find('td', {'class': 'time'})
                event_elem = row.find('td', {'class': 'event'})
                country_elem = row.find('td', {'class': 'flagCur'})
                
                country = 'N/A'
                if country_elem:
                    span = country_elem.find('span')
                    if span and span.get('title'):
                        country = span.get('title')
                    elif country_elem.get('title'):
                        country = country_elem.get('title')
                
                countries_found.add(country)
                
                event_data = {
                    'time': time_elem.text.strip() if time_elem else 'TBD',
                    'country': country,
                    'event': event_elem.text.strip() if event_elem else 'N/A',
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
                events.append(event_data)
            except:
                continue
        
        return jsonify({
            "status": "success",
            "count": len(events),
            "events": events,
            "unique_countries": sorted(list(countries_found)),
            "message": "Showing ALL events (no filter) for debugging"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)