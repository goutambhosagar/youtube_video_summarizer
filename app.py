import re
from flask import Flask, render_template, request
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript
from googletrans import Translator
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
import nltk

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

# Your YouTube API key
api_key = "AIzaSyDtTMqEVr8v_BBUfv6NIywuFjGuEgyLIEI"

# Initialize the translator
translator = Translator()

# Function to get video ID from URL
def get_video_id(url):
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return video_id_match.group(1) if video_id_match else None

# Function to get video details
def get_video_details(video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.videos().list(part='snippet', id=video_id)
    response = request.execute()
    
    # Check if the response contains items
    if 'items' not in response or not response['items']:
        return None
    
    return response['items'][0]['snippet']['title']

# Function to fetch video transcripts
def fetch_transcripts(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        transcript_text = " ".join([entry['text'] for entry in transcript])
        return transcript_text
    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript):
        # Try to fetch transcripts in other available languages and translate to English
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            try:
                if transcript.language_code != 'en':
                    transcript = transcript.translate('en')
                transcript_text = " ".join([entry['text'] for entry in transcript.fetch()])
                return transcript_text
            except Exception as e:
                print(f"Error fetching transcript for language {transcript.language_code}: {e}")
        return None

# Function to summarize text
def summarize_text(text, summary_length=5):
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(text.lower())
    words = [word for word in words if word.isalnum() and word not in stop_words]

    word_freq = FreqDist(words)
    sentences = sent_tokenize(text)
    sentence_scores = {}

    for sentence in sentences:
        for word in word_tokenize(sentence.lower()):
            if word in word_freq:
                if sentence not in sentence_scores:
                    sentence_scores[sentence] = word_freq[word]
                else:
                    sentence_scores[sentence] += word_freq[word]

    summary_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:summary_length]
    summary = ' '.join(summary_sentences)
    return summary

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    video_url = request.form['video_url']
    print(f"Received video URL: {video_url}")
    try:
        video_id = get_video_id(video_url)
        if not video_id:
            print("Invalid YouTube URL")
            return render_template('index.html', error="Invalid YouTube URL")
        
        print(f"Extracted video ID: {video_id}")
        title = get_video_details(video_id)
        if not title:
            print("Could not retrieve video details")
            return render_template('index.html', error="Could not retrieve video details")
        
        print(f"Video title: {title}")
        transcript_text = fetch_transcripts(video_id)
        if not transcript_text:
            print("only english video  generate summary ! ")
            return render_template('index.html', error="only english video  generate summary ! ")
        
        print(f"Fetched transcript text: {transcript_text[:200]}...")  # Print first 200 characters
        summary = summarize_text(transcript_text)
        print(f"Generated summary: {summary}")

        return render_template('index.html', title=title, summary=summary)

    except Exception as e:
        print(f"Error: {e}")
        return render_template('index.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)
