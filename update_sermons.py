import os
import re
import datetime
import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# --- CONFIGURATION ---
CHANNEL_URL = "https://www.youtube.com/@TucsonTabernacle/streams"
# This is the file we append to
DATA_FILE = "All_Sermons_Clean.txt" 

def get_existing_video_ids(filepath):
    """Scans the existing text file to find YouTube URLs so we don't duplicate."""
    if not os.path.exists(filepath):
        return set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex to find youtube IDs in the metadata blocks
    # URL:     https://www.youtube.com/watch?v=VIDEO_ID
    ids = set(re.findall(r'youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})', content))
    return ids

def format_sermon_entry(video_id, title, date_str, transcript_text):
    """Formats the new entry exactly like the existing file structure."""
    
    # Attempt to guess speaker from title (Simplistic logic)
    speaker = "Unknown Speaker"
    if "Evans" in title:
        speaker = "Brother Daniel Evans"
    elif "Brisson" in title:
        speaker = "Brother Steeve Brisson"
    elif "Guerra" in title:
        speaker = "Brother Aaron Guerra"
    
    # Create the header block
    header = f"""
################################################################################
START OF FILE: {date_str} - {title} - {speaker} - Clean.txt
################################################################################

SERMON DETAILS
========================================
Date:    {date_str}
Title:   {title}
Speaker: {speaker}
URL:     https://www.youtube.com/watch?v={video_id}
========================================

"""
    return header + transcript_text + "\n"

def main():
    print("Loading existing sermons...")
    existing_ids = get_existing_video_ids(DATA_FILE)
    print(f"Found {len(existing_ids)} existing videos.")

    # Fetch recent videos from the "Live" tab (streams)
    print("Fetching video list from YouTube...")
    videos = scrapetube.get_channel(channel_url=CHANNEL_URL, content_type='streams')

    new_entries = []
    
    # Check the last 10 videos (to be safe/efficient)
    count = 0
    for video in videos:
        if count > 10: break
        count += 1
        
        video_id = video['videoId']
        title = video['title']['runs'][0]['text']
        
        # Get date (publishedTimeText is relative like "2 days ago", accurate date requires more work or API)
        # For automation, we usually just use "Today" or try to parse, but let's use the current date 
        # of the run as a fallback if metadata is tricky without API key.
        # Ideally, we scrape the specific date, but for this snippet, we'll use YYYY-MM-DD of detection
        # or try to extract if available. 
        # Note: scrapetube doesn't always give exact ISO dates. 
        # We will use today's date for the log, or "Unknown Date" if critical.
        # BETTER: Assuming the cron runs daily, the date is roughly today/yesterday.
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        if video_id in existing_ids:
            continue

        print(f"New sermon found: {title} ({video_id})")

        try:
            # Fetch Transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Prefer manually created English, fallback to auto-generated
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                transcript = transcript_list.find_generated_transcript(['en'])
            
            # Fetch the actual data
            transcript_data = transcript.fetch()
            
            # Format to plain text
            formatter = TextFormatter()
            text_formatted = formatter.format_transcript(transcript_data)
            
            # Create the entry
            entry = format_sermon_entry(video_id, title, date_str, text_formatted)
            new_entries.append(entry)
            
        except Exception as e:
            print(f"Could not retrieve transcript for {video_id}: {e}")

    # Append to file if we found anything
    if new_entries:
        # Prepend or Append? Your file seems chronological. 
        # If we append, it goes to bottom.
        with open(DATA_FILE, 'a', encoding='utf-8') as f:
            for entry in reversed(new_entries): # Oldest of the new ones first
                f.write(entry)
        print(f"Successfully added {len(new_entries)} new sermons.")
    else:
        print("No new sermons found.")

if __name__ == "__main__":
    main()