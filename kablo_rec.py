import requests
import json
import gzip
from io import BytesIO
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

def format_datetime_for_xmltv(date_str):
    """Convert Turkish date format to XMLTV format"""
    try:
        # Parse "20.07.2025 12:00" format
        dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        # Return in XMLTV format: YYYYMMDDHHMMSS +0300 (Turkey timezone)
        return dt.strftime("%Y%m%d%H%M%S +0300")
    except:
        return ""

def create_epg_xml(kablo_data, output_file="kablo_epg.xml"):
    """Create EPG XML file from Kablo TV data"""
    
    # Create root TV element
    tv = ET.Element("tv")
    tv.set("source-info-url", "https://kablowebtv.com")
    tv.set("source-info-name", "Kablo TV")
    tv.set("generator-info-name", "Kablo TV EPG Generator")
    tv.set("generator-info-url", "https://kablowebtv.com")
    
    if not kablo_data.get('IsSucceeded') or not kablo_data.get('Data', {}).get('AllChannels'):
        print("❌ Invalid Kablo TV data for EPG generation!")
        return False
    
    channels_data = kablo_data['Data']['AllChannels']
    
    # Track processed channels and programs
    processed_channels = set()
    program_count = 0
    
    for channel_data in channels_data:
        channel_uid = channel_data.get('UId')
        channel_name = channel_data.get('Name', 'Unknown Channel')
        channel_description = channel_data.get('Description', '')
        logo_url = channel_data.get('PrimaryLogoImageUrl', '')
        remote_number = channel_data.get('RemoteNumber', '')
        categories = channel_data.get('Categories', [])
        
        # Skip if no channel UID or if it's an info channel
        if not channel_uid:
            continue
            
        # Skip info channels
        if categories and categories[0].get('Name') == "Bilgilendirme":
            continue
        
        # Create channel element only once per channel
        if channel_uid not in processed_channels:
            channel_elem = ET.SubElement(tv, "channel")
            channel_elem.set("id", channel_uid)
            
            # Channel display name
            display_name = ET.SubElement(channel_elem, "display-name")
            display_name.text = channel_name
            
            # Add remote number as additional display name if available
            if remote_number:
                display_name_num = ET.SubElement(channel_elem, "display-name")
                display_name_num.text = str(remote_number)
            
            # Channel description
            if channel_description:
                desc_elem = ET.SubElement(channel_elem, "desc")
                desc_elem.set("lang", "tr")
                desc_elem.text = channel_description
            
            # Channel icon/logo
            if logo_url:
                icon_elem = ET.SubElement(channel_elem, "icon")
                icon_elem.set("src", logo_url)
            
            processed_channels.add(channel_uid)
        
        # Process EPG programs for this channel
        epgs = channel_data.get('Epgs', [])
        
        for epg in epgs:
            # Skip if essential data is missing
            if not epg.get('StartDateTime') or not epg.get('EndDateTime'):
                continue
                
            # Create programme element
            programme = ET.SubElement(tv, "programme")
            programme.set("channel", channel_uid)
            programme.set("start", format_datetime_for_xmltv(epg.get('StartDateTime')))
            programme.set("stop", format_datetime_for_xmltv(epg.get('EndDateTime')))
            
            # Program title
            title = ET.SubElement(programme, "title")
            title.set("lang", "tr")
            title.text = epg.get('Title', 'Unknown Program')
            
            # Program description
            description = epg.get('ShortDescription', '')
            if description and description != "Kablo TV platformundaki kanallardan seçmeler...":
                desc = ET.SubElement(programme, "desc")
                desc.set("lang", "tr")
                desc.text = description
            
            # Categories/Genres
            genres = epg.get('Genres', [])
            for genre in genres:
                if isinstance(genre, dict) and genre.get('Name'):
                    category = ET.SubElement(programme, "category")
                    category.set("lang", "tr")
                    category.text = genre['Name']
            
            # Cast members
            cast_members = epg.get('CastMembers', [])
            if cast_members:
                credits = ET.SubElement(programme, "credits")
                for cast_member in cast_members:
                    if isinstance(cast_member, dict):
                        actor = ET.SubElement(credits, "actor")
                        actor.text = cast_member.get('Name', '')
            
            # Rating information based on audience flags
            if epg.get('Plus18Audience'):
                rating = ET.SubElement(programme, "rating")
                rating.set("system", "TR")
                value = ET.SubElement(rating, "value")
                value.text = "18+"
            elif epg.get('Plus13Audience'):
                rating = ET.SubElement(programme, "rating")
                rating.set("system", "TR")
                value = ET.SubElement(rating, "value")
                value.text = "13+"
            elif epg.get('Plus7Audience'):
                rating = ET.SubElement(programme, "rating")
                rating.set("system", "TR")
                value = ET.SubElement(rating, "value")
                value.text = "7+"
            elif epg.get('GeneralAudience'):
                rating = ET.SubElement(programme, "rating")
                rating.set("system", "TR")
                value = ET.SubElement(rating, "value")
                value.text = "Genel İzleyici"
            
            # Add previously shown flag if it's a repeat
            if epg.get('Percentage', 0) < 100:
                previously_shown = ET.SubElement(programme, "previously-shown")
            
            program_count += 1
    
    # Create pretty XML string
    rough_string = ET.tostring(tv, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove empty lines and fix XML declaration
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    lines.insert(1, '<!DOCTYPE tv SYSTEM "xmltv.dtd">')
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ EPG XML created: {output_file}")
    print(f"📺 Channels: {len(processed_channels)}")
    print(f"📋 Programs: {program_count}")
    
    return True

def get_kablo_data():
    """Get Kablo TV data for EPG generation"""
    url = "https://core-api.kablowebtv.com/api/channels"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://tvheryerde.com",
        "Origin": "https://tvheryerde.com",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJMSVZFIiwiaXBiIjoiMCIsImNnZCI6IjA5M2Q3MjBhLTUwMmMtNDFlZC1hODBmLTJiODE2OTg0ZmI5NSIsImNzaCI6IlRSS1NUIiwiZGN0IjoiM0VGNzUiLCJkaSI6IjMwYTM5YzllLWE4ZDYtNGEwMC05NDBmLTFjMTE4NDgzZDcxMiIsInNnZCI6ImJkNmUyNmY5LWJkMzYtNDE2ZC05YWQzLTYzNjhlNGZkYTMyMiIsInNwZ2QiOiJjYjZmZGMwMi1iOGJlLTQ3MTYtYTZjYi1iZTEyYTg4YjdmMDkiLCJpY2giOiIwIiwiaWRtIjoiMCIsImlhIjoiOjpmZmZmOjEwLjAuMC4yMDYiLCJhcHYiOiIxLjAuMCIsImFibiI6IjEwMDAiLCJuYmYiOjE3NTE3MDMxODQsImV4cCI6MTc1MTcwMzI0NCwiaWF0IjoxNzUxNzAzMTg0fQ.SGC_FfT7cU1RVM4E5rMYO2IsA4aYUoYq2SXl51-PZwM"
    }
    
    try:
        print("📡 Fetching data from Kablo TV API...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
                content = gz.read().decode('utf-8')
        except:
            content = response.content.decode('utf-8')
        
        data = json.loads(content)
        
        if not data.get('IsSucceeded') or not data.get('Data', {}).get('AllChannels'):
            print("❌ Failed to get valid data from Kablo TV API!")
            return None
        
        channels = data['Data']['AllChannels']
        print(f"✅ Kablo TV: Found {len(channels)} channels")
        
        return data
        
    except Exception as e:
        print(f"❌ Kablo TV Error: {e}")
        return None

def update_epg_only(epg_file="kablo_epg.xml"):
    """Generate EPG XML file only"""
    print("=== EPG Generator ===")
    
    # Get Kablo TV data
    kablo_data = get_kablo_data()
    
    if not kablo_data:
        print("❌ Failed to get data. EPG generation aborted.")
        return False
    
    # Generate EPG
    print("📺 Generating EPG XML file...")
    success = create_epg_xml(kablo_data, epg_file)
    
    if success:
        print(f"🎉 EPG successfully generated: {epg_file}")
    else:
        print("❌ EPG generation failed!")
    
    return success

if __name__ == "__main__":
    # Generate EPG only
    update_epg_only("kablo_epg.xml")
