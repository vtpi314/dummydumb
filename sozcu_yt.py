import subprocess
import os

CHANNEL_URL = "https://www.youtube.com/channel/UCOulx_rep5O4i9y6AyDqVvw/live"
M3U_FILE = "main.m3u"
TARGET_CHANNEL_NAME = ",Sözcü TV"

def get_m3u8_url():
    # Use simpler format selection flag "-f b" as recommended in the error
    cmd = [
        "yt-dlp",
        "-g",       # Get direct media URL
        "-f", "b",  # Best format as recommended in the error
        "--no-check-certificates",  # Skip certificate validation
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # Spoof a browser user agent
        "--geo-bypass",  # Try to bypass geo-restrictions
        "--skip-download",  # Don't download the actual video
        CHANNEL_URL
    ]
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            url = result.stdout.strip()
            if url and (url.startswith("http") or url.startswith("rtmp")):
                print(f"Successfully found stream URL")
                return url
            else:
                print(f"Command succeeded but returned unexpected output")
        else:
            print(f"Command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            
            # Try alternative channel URL formats if the main one fails
            alt_urls = [
                f"https://www.youtube.com/@SozcuTelevizyon/live",
                f"https://www.youtube.com/watch?v=live_stream&channel=UCOulx_rep5O4i9y6AyDqVvw"
            ]
            
            for alt_url in alt_urls:
                print(f"Trying alternative URL: {alt_url}")
                cmd[-1] = alt_url  # Replace the URL in the command
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            
            # If we reach here, try a direct method
            print("Trying to extract video ID from the live page...")
            try:
                # Get just the video ID from the live page
                cmd_vid = ["yt-dlp", "--get-id", CHANNEL_URL]
                result_vid = subprocess.run(cmd_vid, capture_output=True, text=True)
                if result_vid.returncode == 0 and result_vid.stdout.strip():
                    video_id = result_vid.stdout.strip()
                    print(f"Found video ID: {video_id}")
                    
                    # Now get the direct URL with the video ID
                    cmd_url = [
                        "yt-dlp", 
                        "-g", 
                        "-f", "b",
                        f"https://www.youtube.com/watch?v={video_id}"
                    ]
                    result_url = subprocess.run(cmd_url, capture_output=True, text=True)
                    if result_url.returncode == 0 and result_url.stdout.strip():
                        return result_url.stdout.strip()
            except Exception as e:
                print(f"Error with video ID approach: {str(e)}")
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
    
    return None

def update_channel_url_in_m3u(m3u8_url):
    if not os.path.exists(M3U_FILE):
        print(f"Warning: M3U file '{M3U_FILE}' does not exist.")
        return False
        
    try:
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        i = 0
        found = False
        
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            
            if line.startswith("#EXTINF") and TARGET_CHANNEL_NAME in line:
                found = True
                i += 1
                if i < len(lines):
                    new_lines.append(m3u8_url + "\n")
                else:
                    new_lines.append(m3u8_url + "\n")
            i += 1
        
        if not found:
            print(f"Warning: Target channel '{TARGET_CHANNEL_NAME}' not found in the M3U file.")
            return False
            
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        print(f"Successfully updated M3U file for channel: {TARGET_CHANNEL_NAME}")
        return True
        
    except Exception as e:
        print(f"Error updating M3U file: {str(e)}")
        return False

def main():
    print(f"Starting M3U updater for channel: {TARGET_CHANNEL_NAME}")
    
    m3u8_url = get_m3u8_url()
    
    if m3u8_url:
        success = update_channel_url_in_m3u(m3u8_url)
        
        if success:
            print("M3U file successfully updated.")
        else:
            print("Failed to update M3U file.")
    else:
        print("No live stream URL found.")

if __name__ == "__main__":
    main()
