import subprocess

CHANNEL_URL = "https://www.youtube.com/channel/UCOulx_rep5O4i9y6AyDqVvw/live"
M3U_FILE = "main.m3u"
TARGET_CHANNEL_NAME = ",Sözcü TV"  # <-- Replace with the exact channel name in your m3u

def get_m3u8_url():
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "best",
        CHANNEL_URL
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        url = result.stdout.strip()
        if url.endswith(".m3u8"):
            return url
    return None

def update_channel_url_in_m3u(m3u8_url):
    with open(M3U_FILE, "r") as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        if line.startswith("#EXTINF") and TARGET_CHANNEL_NAME in line:
            # Next line is the URL, replace it
            i += 1
            if i < len(lines):
                new_lines.append(m3u8_url + "\n")
            continue  # skip increment, already handled
        i += 1

    with open(M3U_FILE, "w") as f:
        f.writelines(new_lines)

def main():
    m3u8_url = get_m3u8_url()
    if m3u8_url:
        update_channel_url_in_m3u(m3u8_url)
        print("M3U file updated for target channel.")
    else:
        print("No live stream found.")

if __name__ == "__main__":
    main()
