# AI Video Commentary Bot

A powerful application that adds AI-generated commentary to videos using multiple styles and languages. Available both as a Telegram bot and a Streamlit web application.

## 🎯 Latest Updates

- ✨ Added Telegram-style animations during video processing
- 🎨 Improved mobile-responsive UI design
- 🚀 Optimized video processing and cleanup
- 💾 Instant video availability after processing
- 🔄 Automatic cleanup of temporary files
- 📱 Enhanced mobile viewing experience

## ✨ Features

- 🎭 Multiple commentary styles (Documentary, Energetic, Analytical, Storyteller)
- 🤖 Choice of AI models (OpenAI GPT-4, Deepseek)
- 🌐 Multiple language support (English, Urdu)
- 🎙️ Professional voice synthesis
- 📤 Support for video upload and URL processing
- 🎬 Support for various video platforms (YouTube, Vimeo, TikTok, etc.)
- 📱 Mobile-responsive design
- 🎨 Beautiful UI with Telegram-style animations

## 🚀 Quick Deploy to Railway

1. Fork this repository to your GitHub account
2. Create a new project on [Railway](https://railway.app/)
3. Connect your GitHub repository to Railway
4. Add the following environment variables in Railway:
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (entire JSON content)
   - Other variables from `.env.example`
5. Deploy! Railway will automatically build and deploy your app

Your app will be available at: `https://your-project-name.railway.app`

## 🛠️ Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Deepseek API key
- Google Cloud credentials (for Text-to-Speech)
- Telegram Bot Token (for Telegram bot only)

## 📦 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

4. Set up configuration:
Copy `railway.json.example` to `railway.json` and update with your credentials:
```bash
cp railway.json.example railway.json
```

## 🚀 Running the Applications

### Streamlit Web App
```bash
streamlit run streamlit_app.py
```
The web interface will be available at `http://localhost:8501`

### Telegram Bot
```bash
python new_bot.py
```

## 💡 Usage

### Web Interface
1. Open the Streamlit app in your browser
2. Choose your preferred settings in the sidebar:
   - Commentary style
   - AI model
   - Language
3. Either upload a video file or provide a video URL
4. Click "Process" and watch the Telegram-style animations
5. Download your enhanced video when processing is complete

### Telegram Bot
1. Start a chat with the bot
2. Use /start to see available commands
3. Configure your preferences using /settings
4. Send a video file or URL to process
5. Wait for the bot to return your enhanced video

## ⚠️ Limitations

- Maximum video size: 50MB
- Maximum video duration: 5 minutes
- Supported formats: MP4, MOV, AVI

## 🔧 Troubleshooting

If you encounter issues:
- Check your API keys and credentials
- Ensure your video meets the size and format requirements
- Check your internet connection
- Look for error messages in the console output
- For Railway deployment issues, check the deployment logs

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Share Your App

After deploying to Railway, you can share your app using the Railway-provided URL:
`https://your-project-name.railway.app`

To customize the domain:
1. Go to your Railway project settings
2. Navigate to the "Domains" section
3. Add a custom domain or use Railway's provided domain

Remember to secure your API keys and credentials when sharing the app! 