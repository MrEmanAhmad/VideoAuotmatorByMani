# Video Commentary Bot

A Telegram bot that generates engaging commentary for videos using AI.

## Features

- Multiple commentary styles (Documentary, Energetic, Analytical, Storyteller, Urdu)
- Intelligent video analysis using Google Cloud Vision AI
- Natural language commentary generation
- Professional audio synthesis with multi-language support
- Automatic video processing and generation

## Commentary Styles

- 🎥 Documentary - Professional and informative
- 🔥 Energetic - Dynamic and enthusiastic
- 🔬 Analytical - Detailed and technical
- 📖 Storyteller - Narrative and emotional
- 🇵🇰 Urdu - Natural Urdu language commentary (GPT-4 only)

## Deployment on Railway

1. Fork this repository to your GitHub account

2. Create a new project on Railway and connect it to your GitHub repository

3. Add the following environment variables in Railway:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   GOOGLE_APPLICATION_CREDENTIALS_JSON=your_google_credentials_json
   CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
   CLOUDINARY_API_KEY=your_cloudinary_api_key
   CLOUDINARY_API_SECRET=your_cloudinary_secret
   ```

4. Deploy! Railway will automatically build and deploy your bot using the Dockerfile

### Example Railway Variables JSON

You can also set up your Railway environment by creating a `railway.json` file with the following format:

```json
{
  "OPENAI_API_KEY": "sk-your-openai-api-key",
  "DEEPSEEK_API_KEY": "sk-your-deepseek-api-key",
  "CLOUDINARY_CLOUD_NAME": "your-cloud-name",
  "CLOUDINARY_API_KEY": "your-cloudinary-api-key",
  "CLOUDINARY_API_SECRET": "your-cloudinary-secret",
  "TELEGRAM_BOT_TOKEN": "1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQr",
  "GOOGLE_APPLICATION_CREDENTIALS_JSON": "{\"type\":\"service_account\",\"project_id\":\"your-project-id\",\"private_key_id\":\"your-key-id\",\"private_key\":\"-----BEGIN PRIVATE KEY-----\\nYour-Private-Key\\n-----END PRIVATE KEY-----\\n\",\"client_email\":\"your-service-account@your-project.iam.gserviceaccount.com\",\"client_id\":\"your-client-id\",\"auth_uri\":\"https://accounts.google.com/o/oauth2/auth\",\"token_uri\":\"https://oauth2.googleapis.com/token\",\"auth_provider_x509_cert_url\":\"https://www.googleapis.com/oauth2/v1/certs\",\"client_x509_cert_url\":\"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account@your-project.iam.gserviceaccount.com\",\"universe_domain\":\"googleapis.com\"}"
}
```

To use this:
1. Create a file named `railway.json` in your project root
2. Copy the above template
3. Replace all placeholder values with your actual credentials
4. In Railway dashboard:
   - Go to Variables tab
   - Click "Import from File"
   - Upload your `railway.json`

Note: Make sure to keep your `railway.json` file secure and never commit it to version control.

## Google Cloud Setup

1. Create a Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Note down your Project ID

2. Enable Required APIs:
   - Navigate to "APIs & Services" > "Library"
   - Enable the following APIs:
     * Cloud Vision API
     * Cloud Text-to-Speech API
     * Cloud Storage API

3. Create Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Name your service account (e.g., "video-bot")
   - Grant the following roles:
     * Cloud Vision API User
     * Cloud Text-to-Speech API User
     * Storage Object Viewer

4. Generate Credentials:
   - After creating the service account, click on it
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the JSON file

5. Format Credentials for Railway:
   - Open the downloaded JSON file
   - Convert it to a single line string
   - Escape all double quotes with backslashes
   - Set it as GOOGLE_APPLICATION_CREDENTIALS_JSON in your environment variables

Example of formatted credentials:
```json
{\"type\":\"service_account\",\"project_id\":\"your-project-id\",\"private_key_id\":\"your-key-id\",\"private_key\":\"-----BEGIN PRIVATE KEY-----\\nYour-Private-Key\\n-----END PRIVATE KEY-----\\n\",\"client_email\":\"your-service-account@your-project.iam.gserviceaccount.com\",\"client_id\":\"your-client-id\"}
```

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/video-commentary-bot.git
   cd video-commentary-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your credentials (see `.env.example`)

5. Run the bot:
   ```bash
   python bot.py
   ```

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `OPENAI_API_KEY`: OpenAI API key for commentary generation (GPT-4 required for Urdu style)
- `DEEPSEEK_API_KEY`: Deepseek API key for alternative commentary generation
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Google Cloud credentials JSON string
- `CLOUDINARY_CLOUD_NAME`: Cloudinary cloud name
- `CLOUDINARY_API_KEY`: Cloudinary API key
- `CLOUDINARY_API_SECRET`: Cloudinary API secret

## System Requirements

- Python 3.10 or higher
- FFmpeg
- OpenCV dependencies

## Docker Support

Build the Docker image:
```bash
docker build -t video-commentary-bot .
```

Run the container:
```bash
docker run -d --env-file .env video-commentary-bot
```

## Troubleshooting Google Credentials

Common issues and solutions:

1. **Invalid Credentials Format**:
   - Ensure all quotes are properly escaped
   - The entire JSON should be on a single line
   - Verify all newlines in the private key are escaped with \\n

2. **Permission Denied**:
   - Check if all required APIs are enabled
   - Verify service account has correct roles assigned
   - Ensure project ID matches your active Google Cloud project

3. **API Quota Exceeded**:
   - Check your Google Cloud Console quotas
   - Consider requesting quota increase if needed
   - Monitor API usage in Google Cloud Console

## License

MIT License - feel free to use and modify for your own projects! 