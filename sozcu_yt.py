import subprocess
import os

CHANNEL_URL = "https://www.youtube.com/channel/UCOulx_rep5O4i9y6AyDqVvw/live"
M3U_FILE = "main.m3u"
TARGET_CHANNEL_NAME = ",Sözcü TV"  # <-- Replace with the exact channel name in your m3u

def get_m3u8_url():
    # For GitHub Actions, we need to ensure the tool is in the PATH and executable
    ytdlp_cmd = "yt-dlp"
    
    # Create command array
    cmd = [
        ytdlp_cmd,
        "--cookies", "cookies.txt",
        "-g",
        "-f", "best",
        CHANNEL_URL
    ]
    
    try:
        # Run the command
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check if successful
        if result.returncode == 0:
            url = result.stdout.strip()
            # Verify we actually got a URL
            if url and (url.startswith("http") or url.startswith("rtmp")):
                print(f"Successfully found stream URL: {url[:50]}...")  # Print just the beginning for security
                return url
            else:
                print(f"Command succeeded but returned unexpected output: {url[:100]}")
        else:
            print(f"Command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
    
    return None

def update_channel_url_in_m3u(m3u8_url):
    if not os.path.exists(M3U_FILE):
        print(f"Warning: M3U file '{M3U_FILE}' does not exist.")
        return False
        
    try:
        # Read the file with UTF-8 encoding to handle special characters
        with open(M3U_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        i = 0
        found = False
        
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            
            # Check if this is the target channel line
            if line.startswith("#EXTINF") and TARGET_CHANNEL_NAME in line:
                found = True
                # Next line is the URL, replace it
                i += 1
                if i < len(lines):
                    new_lines.append(m3u8_url + "\n")
                else:
                    # If this is the last line, add the URL anyway
                    new_lines.append(m3u8_url + "\n")
                    
            i += 1
        
        if not found:
            print(f"Warning: Target channel '{TARGET_CHANNEL_NAME}' not found in the M3U file.")
            return False
            
        # Write the updated content back to the file
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        print(f"Successfully updated M3U file for channel: {TARGET_CHANNEL_NAME}")
        return True
        
    except Exception as e:
        print(f"Error updating M3U file: {str(e)}")
        return False

def main():
    print(f"Starting M3U updater for channel: {TARGET_CHANNEL_NAME}")
    
    # Get the live stream URL
    m3u8_url = get_m3u8_url()
    
    if m3u8_url:
        # Update the M3U file
        success = update_channel_url_in_m3u(m3u8_url)
        
        if success:
            print("M3U file successfully updated.")
        else:
            print("Failed to update M3U file.")
    else:
        print("No live stream URL found.")

if __name__ == "__main__":
    main()
