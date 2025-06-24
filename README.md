# AWS Audio Processor CI/CD Pipeline

This project automatically processes `.mp3` files using AWS Transcribe, Translate, and Polly, and stores outputs in S3.

## 📦 AWS Services Used
- **Amazon S3**: Stores inputs and outputs
- **Amazon Transcribe**: Converts speech to text
- **Amazon Translate**: Translates text to text of another language
- **Amazon Polly**: Generates speech from translated text

## 🛠 Setup

### 1. AWS Setup
- Create an S3 bucket
- Create an IAM user with appropriate permissions
- Enable Transcribe, Translate, Polly in your region

### 2. GitHub Secrets
Add these in **Settings → Secrets → Actions**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET`


## 🚀 How It Works

- Add a '.mp3' file, modify the process_audio.py file or any of the workflow files within the repository. 
- Once done, select "Commit changes"


### Pull Request

Select "Commit changes":

- Create a commit message and then select "Create a new branch for this commit and start a pull request": a branch name will be auto-generated.
- Next select "Propose changes"
- Now select "Create pull request"; you should see message "Convert Text to Speech - Beta/synthesize-and-upload-beta (pull_request) successful.

### Merge

- Manual approval is expected from someone other than person initiating PR.
- You can check the "Merge without waiting for requirements to be met (bypass rules)"
- Select "Bypass rules and merge pull request"
- Select "Confirm bypass rules and merge
- You should see a "Pull request successfully merged and closed.

## 📂 Output S3 Structure

s3://pixel-learning-language-s3/beta/
├── audio_inputs/
├── transcripts/
├── translations/
└── audio_outputs/

s3://pixel-learning-language-s3/prod/
├── audio_inputs/
├── transcripts/
├── translations/
└── audio_outputs/

## 🧪 Verifying Results
- Go to your S3 bucket via AWS Console
- Check `beta/` or `prod/` folders for needed audio output files, transcripts or translations
