import os 
import boto3
import time
import json
from pathlib import Path

# Load environment variables from GitHub Secrets
AWS_REGION = os.environ['AWS_REGION']
BUCKET = os.environ['S3_BUCKET']
PREFIX = os.environ.get('S3_PREFIX', 'beta/')
TARGET_LANG = os.environ.get('TARGET_LANG', 'hi')  # Default to Spanish

# Initialize AWS clients
s3 = boto3.client('s3', region_name=AWS_REGION)
transcribe = boto3.client('transcribe', region_name=AWS_REGION)
translate = boto3.client('translate', region_name=AWS_REGION)
polly = boto3.client('polly', region_name=AWS_REGION)

def upload_to_s3(local_path, s3_key):
    s3.upload_file(local_path, BUCKET, s3_key)

def transcribe_audio(filename):
    job_name = f"job-{int(time.time())}"
    s3_uri = f"s3://{BUCKET}/{PREFIX}audio_inputs/{filename}"
    transcript_s3_key = f"{PREFIX}transcripts/{filename}.json"

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': s3_uri},
        MediaFormat='mp3',
        LanguageCode='en-US',
        OutputBucketName=BUCKET,
        OutputKey=transcript_s3_key
    )

    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)

    return transcript_s3_key

def translate_text(text, target_lang):
    result = translate.translate_text(Text=text, SourceLanguageCode='en', TargetLanguageCode=target_lang)
    return result['TranslatedText']

def synthesize_speech(text, lang_code, output_path):
    voice_map = {
        'es': ('Lupe', 'neural'),
        'en': ('Joanna', 'neural'),
        'zh': ('Zhiyu', 'neural'),
        'hi': ('Kajal', 'neural'),
    }

    voice_id, engine = voice_map.get(lang_code, ('Joanna', 'neural'))

    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId=voice_id,
        Engine=engine
    )

    with open(output_path, 'wb') as f:
        f.write(response['AudioStream'].read())

def wait_for_transcript_file(s3_key, timeout=60, poll_interval=5):
    for _ in range(int(timeout / poll_interval)):
        try:
            s3.head_object(Bucket=BUCKET, Key=s3_key)
            return True
        except s3.exceptions.ClientError:
            time.sleep(poll_interval)
    raise TimeoutError(f"Transcript file not found in S3 after waiting: {s3_key}")

def process_file(filepath):
    filename = Path(filepath).name
    s3_key = f"{PREFIX}audio_inputs/{filename}"
    s3.upload_file(filepath, BUCKET, s3_key)

    transcript_s3_key = transcribe_audio(filename)
    wait_for_transcript_file(transcript_s3_key)

    local_transcript_json = "/tmp/tmp_transcript.json"
    s3.download_file(BUCKET, transcript_s3_key, local_transcript_json)

    try:
        with open(local_transcript_json) as f:
            json_data = json.load(f)
        transcript_text = json_data['results']['transcripts'][0]['transcript']
    except Exception as e:
        raise Exception("Could not parse downloaded transcript JSON.") from e

    translated_text = translate_text(transcript_text, TARGET_LANG)

    transcript_path = f"transcripts/{filename}.txt"
    translated_path = f"translations/{filename}_{TARGET_LANG}.txt"
    output_audio_path = f"audio_outputs/{filename}_{TARGET_LANG}.mp3"

    with open("tmp_transcript.txt", "w") as f:
        f.write(transcript_text)
    with open("tmp_translation.txt", "w") as f:
        f.write(translated_text)

    synthesize_speech(translated_text, TARGET_LANG, "tmp_audio.mp3")

    upload_to_s3("tmp_transcript.txt", f"{PREFIX}{transcript_path}")
    upload_to_s3("tmp_translation.txt", f"{PREFIX}{translated_path}")
    upload_to_s3("tmp_audio.mp3", f"{PREFIX}{output_audio_path}")

# Process all .mp3 files in local audio_inputs directory
for file in Path("audio_inputs").glob("*.mp3"):
    process_file(str(file))

