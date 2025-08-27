import requests
import json
import gzip
import os
from io import BytesIO
from cloudscraper import CloudScraper
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
            
        # Skip info channels like we do in M3U generation
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
    """Kablo TV verilerini çeker ve M3U içeriği döndürür"""
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
        print("📡 Kablo TV API'den veri alınıyor...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
                content = gz.read().decode('utf-8')
        except:
            content = response.content.decode('utf-8')
        
        data = json.loads(content)
        
        if not data.get('IsSucceeded') or not data.get('Data', {}).get('AllChannels'):
            print("❌ Kablo TV API'den geçerli veri alınamadı!")
            return "", None
        
        channels = data['Data']['AllChannels']
        print(f"✅ Kablo TV: {len(channels)} kanal bulundu")
        
        m3u_content = []
        kanal_index = 1
        
        for channel in channels:
            name = channel.get('Name')
            stream_data = channel.get('StreamData', {})
            hls_url = stream_data.get('HlsStreamUrl') if stream_data else None
            logo = channel.get('PrimaryLogoImageUrl', '')
            categories = channel.get('Categories', [])
            channel_uid = channel.get('UId')
            
            if not name or not hls_url:
                continue
            
            group = categories[0].get('Name', 'Genel') if categories else 'Genel'
            
            if group == "Bilgilendirme":
                continue

            # Use channel UID as tvg-id for EPG compatibility
            tvg_id = channel_uid if channel_uid else str(kanal_index)
            m3u_content.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u_content.append(hls_url)
            kanal_index += 1
        
        return '\n'.join(m3u_content), data
        
    except Exception as e:
        print(f"❌ Kablo TV Hatası: {e}")
        return "", None

def get_rectv_data():
    """RecTV verilerini çeker"""
    try:
        # RecTV domain al
        session = CloudScraper()
        response = session.post(
            url="https://firebaseremoteconfig.googleapis.com/v1/projects/791583031279/namespaces/firebase:fetch",
            headers={
                "X-Goog-Api-Key": "AIzaSyBbhpzG8Ecohu9yArfCO5tF13BQLhjLahc",
                "X-Android-Package": "com.rectv.shot",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)",
            },
            json={
                "appBuild"      : "99",
                "appInstanceId" : "fx7f_3ndTJSg91iT8oPPI9",
                "appId"         : "1:791583031279:android:244c3d507ab299fcabc01a",
            }
        )
        
        main_url = response.json().get("entries", {}).get("api_url", "")
        base_domain = main_url.replace("/api/", "")
        print(f"🟢 RecTV domain alındı: {base_domain}")
        
        # Tüm kanalları al
        all_channels = []
        page = 0
        session.headers.update({
            'user-agent': 'Dart/3.7 (dart:io)'
        })

        while True:
            url = f"{base_domain}/api/channel/by/filtres/0/0/{page}/4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
            response = session.get(url, timeout=30, verify=False)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            if not data:
                break
                
            all_channels.extend(data)
            page += 1
        
        print(f"✅ RecTV: {len(all_channels)} kanal bulundu")
        
        # M3U formatına çevir
        m3u_content = []
        priority_order = ["Spor", "Haber", "Ulusal", "Sinema", "Belgesel", "Diğer", "Müzik"]
        grouped_channels = {}
        
        for channel in all_channels:
            title = channel.get("title", "Bilinmeyen")
            logo = channel.get("image", "")
            channel_id = str(channel.get("id", ""))
            categories = channel.get("categories", [])
            group_title = categories[0]["title"] if categories else "Diğer"
            
            sources = channel.get("sources", [])
            for source in sources:
                url = source.get("url")
                if url and url.endswith(".m3u8"):
                    quality = source.get("quality")
                    quality_str = f" [{quality}]" if quality and quality.lower() != "none" else ""
                    entry = [
                        f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" tvg-name="{title}" group-title="{group_title}",{title}{quality_str}',
                        '#EXTVLCOPT:http-user-agent=okhttp/4.12.0',
                        '#EXTVLCOPT:http-referrer=https://twitter.com',
                        url
                    ]
                    grouped_channels.setdefault(group_title, []).append(entry)
        
        # Grupları sırala ve içeriği oluştur
        for group in priority_order + sorted(set(grouped_channels.keys()) - set(priority_order)):
            entries = grouped_channels.get(group)
            if entries:
                sorted_entries = sorted(entries, key=lambda e: e[0].split(",")[-1].lower())
                for entry in sorted_entries:
                    m3u_content.extend(entry)
        
        return '\n'.join(m3u_content)
        
    except Exception as e:
        print(f"❌ RecTV Hatası: {e}")
        return ""

def merge_m3u_file(target_file="main.m3u", generate_epg=True, epg_file="kablo_epg.xml"):
    """Ana M3U dosyasını günceller ve isteğe bağlı EPG oluşturur"""
    
    # Veri kaynaklarından içerikleri al
    kablo_content, kablo_data = get_kablo_data()
    rectv_content = get_rectv_data()
    
    # EPG oluştur (eğer istenirse ve Kablo TV verisi varsa)
    if generate_epg and kablo_data:
        print("📺 EPG XML dosyası oluşturuluyor...")
        create_epg_xml(kablo_data, epg_file)
    
    # Hedef dosya yoksa oluştur
    if not os.path.exists(target_file):
        print(f"📄 {target_file} bulunamadı. Yeni oluşturuluyor...")
        epg_reference = f' url-tvg="{epg_file}"' if generate_epg else ''
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(f"#EXTM3U{epg_reference}\n\n")
            f.write("# KABLO_START\n")
            f.write("# KABLO_END\n\n")
            f.write("# REC_START\n")
            f.write("# REC_END\n")
    else:
        # EPG referansını ekle (eğer yoksa)
        if generate_epg:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'url-tvg=' not in content:
                lines = content.split('\n')
                if lines[0].startswith('#EXTM3U'):
                    lines[0] = f'#EXTM3U url-tvg="https://raw.githubusercontent.com/vtpi314/dummydumb/refs/heads/main/kablo_epg.xml"'
                
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"✅ {target_file} EPG referansı eklendi")
    
    # Mevcut dosyayı oku
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kablo bloğunu güncelle
    if kablo_content:
        kablo_start = content.find("# KABLO_START")
        kablo_end = content.find("# KABLO_END")
        
        if kablo_start != -1 and kablo_end != -1:
            new_content = (
                content[:kablo_start + len("# KABLO_START")] + 
                "\n" + kablo_content + "\n" +
                content[kablo_end:]
            )
            content = new_content
            print("✅ Kablo TV içeriği güncellendi")
    
    # RecTV bloğunu güncelle
    if rectv_content:
        rec_start = content.find("# REC_START")
        rec_end = content.find("# REC_END")
        
        if rec_start != -1 and rec_end != -1:
            new_content = (
                content[:rec_start + len("# REC_START")] + 
                "\n" + rectv_content + "\n" +
                content[rec_end:]
            )
            content = new_content
            print("✅ RecTV içeriği güncellendi")
    
    # Güncellenmiş içeriği kaydet
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"🎉 {target_file} başarıyla güncellendi!")
    if generate_epg:
        print(f"📺 EPG dosyası: {epg_file}")

if __name__ == "__main__":
    print("=== M3U ve EPG Güncelleyici ===")
    
    # Default values for automated execution
    generate_epg = True
    m3u_file = "main.m3u"
    epg_file = "kablo_epg.xml"
    
    print(f"📄 M3U dosyası: {m3u_file}")
    print(f"📺 EPG dosyası: {epg_file}")
    
    # İşlemi başlat
    merge_m3u_file(m3u_file, generate_epg, epg_file)
