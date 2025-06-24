import os
import boto3
import time
import requests
from pathlib import Path

# Load environment variables from GitHub Secrets
AWS_REGION = os.environ['AWS_REGION']
BUCKET = os.environ['S3_BUCKET']
PREFIX = os.environ.get('S3_PREFIX', 'beta/')  # Default to beta unless overridden
TARGET_LANG = os.environ.get('TARGET_LANG', 'es')  # Default to Spanish

s3 = boto3.client('s3', region_name=AWS_REGION)
transcribe = boto3.client('transcribe', region_name=AWS_REGION)
translate = boto3.client('translate', region_name=AWS_REGION)
polly = boto3.client('polly', region_name=AWS_REGION)

def upload_to_s3(local_path, s3_key):
    s3.upload_file(local_path, BUCKET, s3_key)

def transcribe_audio(filename):
    job_name = f"job-{int(time.time())}"
    s3_uri = f"s3://{BUCKET}/{PREFIX}audio_inputs/{filename}"
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat='mp3',
        LanguageCode='en-US',
        OutputBucketName=BUCKET,
        OutputKey=f"{PREFIX}transcripts/"
    )

    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)

    uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
    return uri  # Returns S3 URL to transcript JSON

def translate_text(text, target_lang):
    result = translate.translate_text(Text=text, SourceLanguageCode='en', TargetLanguageCode=target_lang)
    return result['TranslatedText']

def synthesize_speech(text, lang_code, output_path):
 # Map language codes to Polly voice IDs
    voice_map = {
        'es': 'Lupe',
        'en': 'Joanna',
        'zh': 'Zhiyu',        
        'hi': 'Kajal',
        
    }

    voice_id = voice_map.get(lang_code, 'Joanna')  # Default to 'Joanna' if not found

    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId=voice_id
    )

    with open(output_path, 'wb') as f:
        f.write(response['AudioStream'].read())

def process_file(filepath):
    filename = Path(filepath).name
    s3.upload_file(filepath, BUCKET, f"{PREFIX}audio_inputs/{filename}")
    
    transcript_uri = transcribe_audio(filename)
   
    response = requests.get(transcript_uri)

if response.status_code != 200:
    raise Exception(f"Failed to fetch transcript: {response.status_code}, {response.text}")

try:
    json_data = response.json()
    transcript_text = json_data['results']['transcripts'][0]['transcript']
except Exception as e:
    raise Exception(f"Could not parse transcript JSON. Raw content: {response.text[:200]}...") from e  
    
    translated_text = translate_text(transcript_text, TARGET_LANG)

    transcript_path = f"transcripts/{filename}.txt"
    translated_path = f"translations/{filename}_{TARGET_LANG}.txt"
    output_audio_path = f"audio_outputs/{filename}_{TARGET_LANG}.mp3"

    # Save files locally
    with open("tmp_transcript.txt", "w") as f:
        f.write(transcript_text)
    with open("tmp_translation.txt", "w") as f:
        f.write(translated_text)

    synthesize_speech(translated_text, TARGET_LANG, "tmp_audio.mp3")

    # Upload to S3
    upload_to_s3("tmp_transcript.txt", f"{PREFIX}transcripts/{filename}.txt")
    upload_to_s3("tmp_translation.txt", f"{PREFIX}translations/{filename}_{TARGET_LANG}.txt")
    upload_to_s3("tmp_audio.mp3", f"{PREFIX}audio_outputs/{filename}_{TARGET_LANG}.mp3")

# Loop through all .mp3 files in audio_inputs
for file in Path("audio_inputs").glob("*.mp3"):
    process_file(str(file))

