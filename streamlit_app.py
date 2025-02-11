import streamlit as st
import os
from pathlib import Path
import json
import tempfile
import asyncio
from datetime import datetime
import shutil
from telegram.ext import ContextTypes
from telegram import Bot

# Add the current directory to Python path
import sys
sys.path.append(str(Path(__file__).parent))

# Load railway.json configuration first
railway_file = Path("railway.json")
if railway_file.exists():
    with open(railway_file, 'r') as f:
        config = json.load(f)
    
    # Set up environment variables from railway.json
    for key, value in config.items():
        os.environ[key] = value
    
    # Set up Google credentials
    if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in config:
        # Create credentials directory if it doesn't exist
        creds_dir = Path("credentials")
        creds_dir.mkdir(exist_ok=True)
        
        # Parse and save Google credentials
        creds_json = json.loads(config["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
        google_creds_file = creds_dir / "google_credentials.json"
        with open(google_creds_file, 'w') as f:
            json.dump(creds_json, f, indent=2)
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(google_creds_file.absolute())
else:
    raise ValueError("railway.json not found")

# Now import VideoBot after environment is configured
from new_bot import VideoBot
from pipeline import Step_1_download_video, Step_7_cleanup

# Initialize VideoBot
bot = VideoBot()

# Set page config
st.set_page_config(
    page_title="AI Video Commentary Bot",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS with mobile responsiveness and centered content
st.markdown("""
    <style>
    /* Center content and add responsive design */
    .main-content {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    .stButton>button {
        width: 100%;
        height: 3em;
        margin-top: 1em;
    }
    
    /* Processing animation container */
    .processing-container {
        text-align: center;
        padding: 2rem;
        margin: 2rem auto;
        max-width: 90%;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* Telegram-style animations */
    .telegram-animation {
        font-size: 3rem;
        margin: 1rem 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    /* Video container */
    .video-container {
        position: relative;
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
        border-radius: 1rem;
        overflow: hidden;
    }
    
    .video-container video {
        width: 100%;
        height: auto;
        border-radius: 1rem;
    }
    
    /* Download button styling */
    .download-btn {
        background: linear-gradient(45deg, #2196F3, #00BCD4);
        color: white;
        padding: 1rem 2rem;
        border-radius: 2rem;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        width: 100%;
        max-width: 300px;
        margin: 1rem auto;
        display: block;
    }
    
    .download-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.2);
    }
    
    /* Mobile optimization */
    @media (max-width: 768px) {
        .main-content {
            padding: 0.5rem;
        }
        
        .processing-container {
            padding: 1rem;
            margin: 1rem auto;
        }
        
        .telegram-animation {
            font-size: 2rem;
        }
    }
    
    /* Status messages */
    .status-message {
        text-align: center;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background-color: #2196F3;
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'settings' not in st.session_state:
    st.session_state.settings = bot.default_settings.copy()
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'status' not in st.session_state:
    st.session_state.status = ""

# Title and description
st.title("🎬 AI Video Commentary Bot")
st.markdown("""
    Transform your videos with AI-powered commentary in multiple styles and languages.
    Upload a video or provide a URL to get started!
""")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Style selection
    st.subheader("Commentary Style")
    style = st.selectbox(
        "Choose your style",
        options=list(bot.styles.keys()),
        format_func=lambda x: f"{bot.styles[x]['icon']} {bot.styles[x]['name']}",
        key="style"
    )
    st.caption(bot.styles[style]['description'])
    
    # AI Model selection
    st.subheader("AI Model")
    llm = st.selectbox(
        "Choose AI model",
        options=list(bot.llm_providers.keys()),
        format_func=lambda x: f"{bot.llm_providers[x]['icon']} {bot.llm_providers[x]['name']}",
        key="llm"
    )
    st.caption(bot.llm_providers[llm]['description'])
    
    # Language selection
    st.subheader("Language")
    available_languages = {
        code: info for code, info in bot.languages.items()
        if not info.get('requires_openai') or llm == 'openai'
    }
    language = st.selectbox(
        "Choose language",
        options=list(available_languages.keys()),
        format_func=lambda x: f"{bot.languages[x]['icon']} {bot.languages[x]['name']}",
        key="language"
    )
    
    # Update settings in session state and bot's user settings
    user_id = 0  # Default user ID for Streamlit interface
    bot.update_user_setting(user_id, 'style', style)
    bot.update_user_setting(user_id, 'llm', llm)
    bot.update_user_setting(user_id, 'language', language)
    st.session_state.settings = bot.get_user_settings(user_id)

# Main content area
tab1, tab2 = st.tabs(["📤 Upload Video", "🔗 Video URL"])

# Upload Video Tab
with tab1:
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'mov', 'avi'],
        help="Maximum file size: 50MB"
    )
    
    if uploaded_file:
        if uploaded_file.size > bot.MAX_VIDEO_SIZE:
            st.error("❌ Video is too large. Maximum size is 50MB.")
        else:
            st.video(uploaded_file)
            if st.button("Process Video", key="process_upload"):
                st.session_state.processing = True
                st.session_state.progress = 0
                st.session_state.status = "Starting video processing..."

# Video URL Tab
with tab2:
    video_url = st.text_input(
        "Enter video URL",
        placeholder="https://example.com/video.mp4",
        help="Support for YouTube, Vimeo, TikTok, and more"
    )
    
    if video_url:
        if st.button("Process URL", key="process_url"):
            if not video_url.startswith(('http://', 'https://')):
                st.error("❌ Please provide a valid URL starting with http:// or https://")
            else:
                st.session_state.processing = True
                st.session_state.progress = 0
                st.session_state.status = "Starting video processing..."

# Progress display
if st.session_state.processing:
    # Center the progress display
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    # Remove the default progress bar
    # progress_bar = st.progress(st.session_state.progress)
    status_box = st.empty()
    
    # Processing animation container
    animation_container = st.empty()
    
    class StreamlitMessage:
        """Mock Telegram message for status updates"""
        def __init__(self):
            self.message_id = 0
            self.text = ""
            self.video = None
            self.file_id = None
            self.file_name = None
            self.mime_type = None
            self.file_size = None
            self.download_placeholder = st.empty()
            self.video_placeholder = st.empty()
            self.status_placeholder = st.empty()
            self.output_filename = None
            self.animation_states = {
                "downloading": "📥",
                "analyzing": "🔍",
                "generating": "🎬",
                "processing": "⚙️",
                "finalizing": "✨",
                "complete": "✅"
            }
        
        def _show_animation(self, state):
            animation_container.markdown(
                f'<div class="processing-container">'
                f'<div class="telegram-animation">{self.animation_states[state]}</div>'
                f'<div class="status-message">{self.text}</div>'
                '</div>',
                unsafe_allow_html=True
            )
        
        async def reply_text(self, text, **kwargs):
            self.text = text
            st.session_state.status = text
            
            # Determine animation state based on text content
            state = "processing"
            if "downloading" in text.lower():
                state = "downloading"
            elif "analyzing" in text.lower():
                state = "analyzing"
            elif "generating" in text.lower():
                state = "generating"
            elif "finalizing" in text.lower():
                state = "finalizing"
            elif "complete" in text.lower():
                state = "complete"
            
            self._show_animation(state)
            
            # Remove progress tracking since we removed the progress bar
            # if "%" in text:
            #     try:
            #         progress = int(text.split("%")[0].split()[-1]) / 100
            #         st.session_state.progress = progress
            #     except:
            #         pass
            
            return self
        
        async def edit_text(self, text, **kwargs):
            return await self.reply_text(text)
        
        async def reply_video(self, video, caption=None, **kwargs):
            try:
                # Handle both file-like objects and file paths
                if hasattr(video, 'read'):
                    video_data = video.read()
                    video_path = None
                elif isinstance(video, str) and os.path.exists(video):
                    with open(video, "rb") as f:
                        video_data = f.read()
                    video_path = video
                else:
                    st.error("Invalid video format")
                    return self

                # Save to a more permanent location if we have a path
                self.output_filename = f"enhanced_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                if video_path:
                    shutil.copy2(video_path, self.output_filename)
                else:
                    with open(self.output_filename, "wb") as f:
                        f.write(video_data)

                try:
                    # Clear animation container
                    animation_container.empty()
                    
                    # Display video and caption in centered container
                    st.markdown('<div class="video-container">', unsafe_allow_html=True)
                    if caption:
                        st.markdown(f"### {caption}")
                    self.video_placeholder.video(video_data)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Create styled download button using Streamlit's native component
                    self.download_placeholder.markdown(
                        '<div style="text-align: center; padding: 1rem;">',
                        unsafe_allow_html=True
                    )
                    self.download_placeholder.download_button(
                        label="⬇️ Download Enhanced Video",
                        data=video_data,
                        file_name=self.output_filename,
                        mime="video/mp4",
                        use_container_width=False,
                        key="download_btn"
                    )
                    self.download_placeholder.markdown('</div>', unsafe_allow_html=True)
                    
                    # Now that video is loaded in browser memory, we can delete the file
                    if self.output_filename and os.path.exists(self.output_filename):
                        try:
                            os.remove(self.output_filename)
                            logger.info(f"Successfully deleted temporary file after browser load: {self.output_filename}")
                        except Exception as cleanup_error:
                            logger.error(f"Error deleting temporary file {self.output_filename}: {str(cleanup_error)}")
                            st.error(f"Error cleaning up temporary files: {str(cleanup_error)}")
                    
                except Exception as e:
                    st.error(f"Error displaying video: {str(e)}")
                    if self.output_filename and os.path.exists(self.output_filename):
                        try:
                            os.remove(self.output_filename)
                            logger.info(f"Cleaned up temporary file after display error: {self.output_filename}")
                        except Exception as cleanup_error:
                            logger.error(f"Error cleaning up after display error - {self.output_filename}: {str(cleanup_error)}")
                
            except Exception as e:
                st.error(f"Error handling video: {str(e)}")
                if hasattr(self, 'output_filename') and self.output_filename and os.path.exists(self.output_filename):
                    try:
                        os.remove(self.output_filename)
                        logger.info(f"Cleaned up temporary file after handling error: {self.output_filename}")
                    except Exception as cleanup_error:
                        logger.error(f"Final cleanup attempt failed - {self.output_filename}: {str(cleanup_error)}")
            
            return self
    
    class StreamlitUpdate:
        """Mock Telegram Update for bot compatibility"""
        def __init__(self):
            self.effective_user = type('User', (), {'id': 0})
            self.message = StreamlitMessage()
            self.effective_message = self.message
    
    class MockBot:
        """Mock Telegram Bot"""
        async def get_file(self, file_id):
            return None
            
        async def send_message(self, *args, **kwargs):
            return None
            
        async def edit_message_text(self, *args, **kwargs):
            return None
            
        async def send_video(self, *args, **kwargs):
            return None
            
        async def send_document(self, *args, **kwargs):
            return None

    class StreamlitContext:
        """Mock Telegram context"""
        def __init__(self):
            self._bot = MockBot()
            self.args = []
            self.matches = None
            self.user_data = {}
            self.chat_data = {}
            self.bot_data = {}
            
        @property
        def bot(self):
            return self._bot

    async def process_video():
        cleanup_task = None
        output_dir = None
        try:
            # Create output directory with timestamp
            output_dir = Path(f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            output_dir.mkdir(exist_ok=True)
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                update = StreamlitUpdate()
                context = StreamlitContext()
                
                # Handle video input
                if uploaded_file:
                    video_path = temp_dir_path / "input_video.mp4"
                    with open(video_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process the video using bot's process_video method
                    final_video = await bot.process_video_file(
                        update,
                        context,
                        str(video_path),
                        update.message,
                        {
                            'title': uploaded_file.name,
                            'uploader': 'streamlit_user',
                            'upload_date': datetime.now().strftime("%Y%m%d"),
                        }
                    )
                else:
                    # Process URL using bot's process_video_from_url method
                    final_video = await bot.process_video_from_url(update, context, video_url)
                
                if final_video and os.path.exists(final_video):
                    # Copy final video to output directory
                    output_video = output_dir / f"final_video_{st.session_state.settings['style']}.mp4"
                    shutil.copy2(final_video, output_video)
                    
                    try:
                        with open(output_video, "rb") as f:
                            video_data = f.read()
                        
                        # Display video
                        st.video(video_data)
                        
                        # Create download button
                        st.download_button(
                            label="⬇️ Download Enhanced Video",
                            data=video_data,
                            file_name=output_video.name,
                            mime="video/mp4"
                        )
                        
                        # Display countdown timer
                        total_time = 60
                        progress_text = st.empty()
                        for remaining in range(total_time, 0, -1):
                            progress_text.warning(f"⏳ Video will be available for download for {remaining} seconds")
                            await asyncio.sleep(1)
                        
                        progress_text.error("⚠️ Download time expired! Please process the video again if needed.")
                        
                        # Schedule cleanup using Step_7_cleanup
                        async def delayed_cleanup():
                            await asyncio.sleep(5)  # Give a few extra seconds after expiry
                            try:
                                # Use Step_7_cleanup to clean everything
                                Step_7_cleanup.execute_step(
                                    output_dir=output_dir,
                                    style_name=st.session_state.settings['style']
                                )
                            except Exception as cleanup_error:
                                st.error(f"Cleanup error: {cleanup_error}")
                        
                        cleanup_task = asyncio.create_task(delayed_cleanup())
                        
                    except Exception as e:
                        st.error(f"Error handling video display: {str(e)}")
                        if output_dir and output_dir.exists():
                            Step_7_cleanup.execute_step(
                                output_dir=output_dir,
                                style_name=st.session_state.settings['style']
                            )
                
        except Exception as e:
            st.error(f"❌ Error processing video: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            if output_dir and output_dir.exists():
                Step_7_cleanup.execute_step(
                    output_dir=output_dir,
                    style_name=st.session_state.settings['style']
                )
        finally:
            st.session_state.processing = False
            if not cleanup_task and output_dir and output_dir.exists():  # Only cleanup if no delayed cleanup is scheduled
                Step_7_cleanup.execute_step(
                    output_dir=output_dir,
                    style_name=st.session_state.settings['style']
                )

    # Run async processing
    asyncio.run(process_video())

# Help section
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
        ### How to Use
        1. Choose your preferred settings in the sidebar
        2. Upload a video file or provide a video URL
        3. Click the process button and wait for the magic!
        
        ### Features
        - Multiple commentary styles
        - Support for different languages
        - Choice of AI models
        - Professional voice synthesis
        
        ### Limitations
        - Maximum video size: 50MB
        - Maximum duration: 5 minutes
        - Supported formats: MP4, MOV, AVI
        
        ### Need Help?
        If you encounter any issues, try:
        - Using a shorter video
        - Converting your video to MP4 format
        - Checking your internet connection
        - Refreshing the page
    """) 