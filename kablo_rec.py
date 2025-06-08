import requests
import json
import gzip
import os
from io import BytesIO
from cloudscraper import CloudScraper

def get_kablo_data():
    """Kablo TV verilerini çeker"""
    url = "https://core-api.kablowebtv.com/api/channels"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://tvheryerde.com",
        "Origin": "https://tvheryerde.com",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJMSVZFIiwiaXBiIjoiMCIsImNnZCI6IjA5M2Q3MjBhLTUwMmMtNDFlZC1hODBmLTJiODE2OTg0ZmI5NSIsImNzaCI6IlRSS1NUIiwiZGN0IjoiM0VGNzUiLCJkaSI6ImE2OTliODNmLTgyNmItNGQ5OS05MzYxLWM4YTMxMzIxOGQ0NiIsInNnZCI6Ijg5NzQxZmVjLTFkMzMtNGMwMC1hZmNkLTNmZGFmZTBiNmEyZCIsInNwZ2QiOiIxNTJiZDUzOS02MjIwLTQ0MjctYTkxNS1iZjRiZDA2OGQ3ZTgiLCJpY2giOiIwIiwiaWRtIjoiMCIsImlhIjoiOjpmZmZmOjEwLjAuMC4yMDYiLCJhcHYiOiIxLjAuMCIsImFibiI6IjEwMDAiLCJuYmYiOjE3NDUxNTI4MjUsImV4cCI6MTc0NTE1Mjg4NSwiaWF0IjoxNzQ1MTUyODI1fQ.OSlafRMxef4EjHG5t6TqfAQC7y05IiQjwwgf6yMUS9E"
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
            return ""
        
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
            
            if not name or not hls_url:
                continue
            
            group = categories[0].get('Name', 'Genel') if categories else 'Genel'
            
            if group == "Bilgilendirme":
                continue

            tvg_id = str(kanal_index)
            m3u_content.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u_content.append(hls_url)
            kanal_index += 1
        
        return '\n'.join(m3u_content)
        
    except Exception as e:
        print(f"❌ Kablo TV Hatası: {e}")
        return ""

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
                "appBuild": "81",
                "appInstanceId": "evON8ZdeSr-0wUYxf0qs68",
                "appId": "1:791583031279:android:1",
            }
        )
        
        main_url = response.json().get("entries", {}).get("api_url", "")
        base_domain = main_url.replace("/api/", "")
        print(f"🟢 RecTV domain alındı: {base_domain}")
        
        # Tüm kanalları al
        all_channels = []
        page = 0
        
        while True:
            url = f"{base_domain}/api/channel/by/filtres/0/0/{page}/4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
            response = requests.get(url)
            
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

def merge_m3u_file(target_file="main.m3u"):
    """Ana M3U dosyasını günceller"""
    
    # Veri kaynaklarından içerikleri al
    kablo_content = get_kablo_data()
    rectv_content = get_rectv_data()
    
    # Hedef dosya yoksa oluştur
    if not os.path.exists(target_file):
        print(f"📄 {target_file} bulunamadı. Yeni oluşturuluyor...")
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n\n")
            f.write("# KABLO_START\n")
            f.write("# KABLO_END\n\n")
            f.write("# REC_START\n")
            f.write("# REC_END\n")
    
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

if __name__ == "__main__":
    merge_m3u_file()
