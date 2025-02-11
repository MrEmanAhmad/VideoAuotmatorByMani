import os
import sys
import logging
from pathlib import Path
import json

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('streamlit_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

try:
    import streamlit as st
    
    # Set page config first
    st.set_page_config(
        page_title="AI Video Commentary Bot",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Show loading message
    loading_placeholder = st.empty()
    loading_placeholder.info("🔄 Initializing application...")
    
    # Load configuration
    try:
        # First check if required environment variables are set directly in Railway
        required_vars = [
            'OPENAI_API_KEY',
            'DEEPSEEK_API_KEY',
            'GOOGLE_APPLICATION_CREDENTIALS_JSON'
        ]
        
        # Check if all required variables are in environment
        all_vars_present = all(os.getenv(var) for var in required_vars)
        
        if not all_vars_present:
            # If not all variables are present, try loading from railway.json as fallback
            railway_file = Path("railway.json")
            if railway_file.exists():
                logger.info("Loading configuration from railway.json")
                with open(railway_file, 'r') as f:
                    config = json.load(f)
                for key, value in config.items():
                    if not os.getenv(key):  # Only set if not already in environment
                        os.environ[key] = str(value)
            else:
                logger.warning("No railway.json found, checking if required variables are set in environment")
                # Check which variables are missing
                missing_vars = [var for var in required_vars if not os.getenv(var)]
                if missing_vars:
                    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Set up Google credentials if provided
        if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
            creds_dir = Path("credentials")
            creds_dir.mkdir(exist_ok=True)
            
            google_creds_file = creds_dir / "google_credentials.json"
            with open(google_creds_file, 'w') as f:
                json.dump(json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]), f, indent=2)
            
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(google_creds_file.absolute())
            logger.info("Google credentials configured successfully")
        
        # Import required modules
        import tempfile
        import asyncio
        import json
        from datetime import datetime
        import shutil
        from telegram.ext import ContextTypes
        from telegram import Bot
        import gc
        import tracemalloc
        import psutil
        
        from new_bot import VideoBot
        from pipeline import Step_1_download_video, Step_7_cleanup
        
        # Initialize VideoBot with proper caching
        @st.cache_resource(show_spinner=False)
        def init_bot():
            """Initialize the VideoBot instance with caching"""
            try:
                return VideoBot()
            except Exception as e:
                logger.error(f"Bot initialization error: {e}")
                raise
        
        # Initialize bot instance
        bot = init_bot()
        
        # Initialize session state
        if 'initialized' not in st.session_state:
            st.session_state.initialized = False
            st.session_state.settings = bot.default_settings.copy()
            st.session_state.is_processing = False
            st.session_state.progress = 0
            st.session_state.status = ""
            st.session_state.initialized = True
        
        # Clear loading message
        loading_placeholder.empty()
        
        # Safe cleanup function
        def cleanup_memory(force=False):
            """Force garbage collection and clear memory"""
            try:
                if force or not st.session_state.get('is_processing', False):
                    gc.collect()
                    
                    # Clear temp directories that are older than 1 hour
                    current_time = datetime.now().timestamp()
                    for pattern in ['temp_*', 'output_*']:
                        for path in Path().glob(pattern):
                            try:
                                if path.is_dir():
                                    # Check if directory is older than 1 hour
                                    if current_time - path.stat().st_mtime > 3600:
                                        shutil.rmtree(path, ignore_errors=True)
                            except Exception as e:
                                logger.warning(f"Failed to remove directory {path}: {e}")
                    
                    logger.info("Cleanup completed successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
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
                options=list(init_bot().styles.keys()),
                format_func=lambda x: f"{init_bot().styles[x]['icon']} {init_bot().styles[x]['name']}",
                key="style"
            )
            st.caption(init_bot().styles[style]['description'])
            
            # AI Model selection
            st.subheader("AI Model")
            llm = st.selectbox(
                "Choose AI model",
                options=list(init_bot().llm_providers.keys()),
                format_func=lambda x: f"{init_bot().llm_providers[x]['icon']} {init_bot().llm_providers[x]['name']}",
                key="llm"
            )
            st.caption(init_bot().llm_providers[llm]['description'])
            
            # Language selection
            st.subheader("Language")
            available_languages = {
                code: info for code, info in init_bot().languages.items()
                if not info.get('requires_openai') or llm == 'openai'
            }
            language = st.selectbox(
                "Choose language",
                options=list(available_languages.keys()),
                format_func=lambda x: f"{init_bot().languages[x]['icon']} {init_bot().languages[x]['name']}",
                key="language"
            )
            
            # Update settings in session state and bot's user settings
            user_id = 0  # Default user ID for Streamlit interface
            init_bot().update_user_setting(user_id, 'style', style)
            init_bot().update_user_setting(user_id, 'llm', llm)
            init_bot().update_user_setting(user_id, 'language', language)
            st.session_state.settings = init_bot().get_user_settings(user_id)
        
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
                if uploaded_file.size > init_bot().MAX_VIDEO_SIZE:
                    st.error("❌ Video is too large. Maximum size is 50MB.")
                else:
                    st.video(uploaded_file)
                    if st.button("Process Video", key="process_upload"):
                        if not st.session_state.is_processing:
                            st.session_state.is_processing = True
                            st.session_state.progress = 0
                            st.session_state.status = "Starting video processing..."
                            try:
                                # Run video processing
                                asyncio.run(process_video())
                            except Exception as e:
                                logger.error(f"Error in process_upload: {str(e)}")
                                st.error("❌ Failed to process video. Please try again.")
                                st.session_state.is_processing = False
                        else:
                            st.warning("⚠️ Already processing a video. Please wait.")
        
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
                        if not st.session_state.is_processing:
                            st.session_state.is_processing = True
                            st.session_state.progress = 0
                            st.session_state.status = "Starting video processing..."
                            try:
                                # Run video processing
                                asyncio.run(process_video())
                            except Exception as e:
                                logger.error(f"Error in process_url: {str(e)}")
                                st.error("❌ Failed to process video URL. Please try again.")
                                st.session_state.is_processing = False
                        else:
                            st.warning("⚠️ Already processing a video. Please wait.")
        
        # Add memory monitoring
        if st.sidebar.checkbox("Show Memory Usage"):
            process = psutil.Process()
            memory_info = process.memory_info()
            st.sidebar.write(f"Memory Usage: {memory_info.rss / 1024 / 1024:.2f} MB")
            if st.sidebar.button("Force Cleanup"):
                cleanup_memory()
                st.sidebar.success("Memory cleaned up!")
        
        # Modify the video display section to use st.cache_data
        @st.cache_data(ttl=60)  # Cache for 60 seconds
        def display_video(video_data, caption=None):
            if caption:
                st.markdown(f"### {caption}")
            st.video(video_data)
            return True
        
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
        
        # Add these classes before the process_video function
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
                
            async def reply_text(self, text, **kwargs):
                logger.info(f"Status update: {text}")
                self.text = text
                st.session_state.status = text
                self.status_placeholder.markdown(f"🔄 {text}")
                return self
                
            async def edit_text(self, text, **kwargs):
                return await self.reply_text(text)
                
            async def reply_video(self, video, caption=None, **kwargs):
                logger.info("Handling video reply")
                try:
                    if hasattr(video, 'read'):
                        video_data = video.read()
                    elif isinstance(video, str) and os.path.exists(video):
                        with open(video, "rb") as f:
                            video_data = f.read()
                    else:
                        logger.error("Invalid video format")
                        st.error("Invalid video format")
                        return self
                    
                    self.video_placeholder.video(video_data)
                    if caption:
                        st.markdown(f"### {caption}")
                    return self
                    
                except Exception as e:
                    logger.error(f"Error in reply_video: {str(e)}")
                    st.error(f"Error displaying video: {str(e)}")
                    return self
        
        class StreamlitUpdate:
            """Mock Telegram Update for bot compatibility"""
            def __init__(self):
                logger.info("Initializing StreamlitUpdate")
                self.effective_user = type('User', (), {'id': 0})
                self.message = StreamlitMessage()
                self.effective_message = self.message
        
        class StreamlitContext:
            """Mock Telegram context"""
            def __init__(self):
                logger.info("Initializing StreamlitContext")
                self.bot = type('MockBot', (), {
                    'get_file': lambda *args, **kwargs: None,
                    'send_message': lambda *args, **kwargs: None,
                    'edit_message_text': lambda *args, **kwargs: None,
                    'send_video': lambda *args, **kwargs: None,
                    'send_document': lambda *args, **kwargs: None
                })()
                self.args = []
                self.matches = None
                self.user_data = {}
                self.chat_data = {}
                self.bot_data = {}
        
        # Modify the process_video function to be more robust
        async def process_video():
            if st.session_state.is_processing:
                logger.warning("Already processing a video")
                return
            
            st.session_state.is_processing = True
            cleanup_task = None
            output_dir = None
            
            try:
                logger.info("Starting video processing")
                # Create output directory with timestamp
                output_dir = Path(f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                output_dir.mkdir(exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
                
                # Create temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_dir_path = Path(temp_dir)
                    logger.info(f"Created temporary directory: {temp_dir_path}")
                    
                    update = StreamlitUpdate()
                    context = StreamlitContext()
                    
                    # Handle video input
                    if uploaded_file:
                        logger.info(f"Processing uploaded file: {uploaded_file.name}")
                        video_path = temp_dir_path / "input_video.mp4"
                        with open(video_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Process the video using bot's process_video method
                        logger.info("Starting video file processing")
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
                        logger.info(f"Processing video URL: {video_url}")
                        final_video = await bot.process_video_from_url(update, context, video_url)
                    
                    if final_video and os.path.exists(final_video):
                        logger.info(f"Video processing complete: {final_video}")
                        # Copy final video to output directory
                        output_video = output_dir / f"final_video_{st.session_state.settings['style']}.mp4"
                        shutil.copy2(final_video, output_video)
                        logger.info(f"Copied video to output directory: {output_video}")
                        
                        try:
                            with open(output_video, "rb") as f:
                                video_data = f.read()
                            
                            # Display video using cached function
                            logger.info("Displaying video")
                            display_video(video_data)
                            
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
                            
                            # Schedule cleanup
                            async def delayed_cleanup():
                                await asyncio.sleep(5)  # Give a few extra seconds after expiry
                                logger.info("Running delayed cleanup")
                                cleanup_memory()
                            
                            cleanup_task = asyncio.create_task(delayed_cleanup())
                            
                        except Exception as e:
                            logger.error(f"Error handling video display: {str(e)}")
                            st.error(f"Error handling video display: {str(e)}")
                            cleanup_memory()
            
            except Exception as e:
                logger.error(f"Error processing video: {str(e)}", exc_info=True)
                st.error(f"❌ Error processing video: {str(e)}")
            finally:
                st.session_state.is_processing = False
                cleanup_memory(force=True)
                logger.info("Video processing completed")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        st.error(f"⚠️ Failed to initialize application: {str(e)}")
        st.stop()
        
except Exception as e:
    logger.error(f"Critical error: {e}", exc_info=True)
    # If streamlit itself fails to import or initialize
    print(f"Critical error: {e}")
    sys.exit(1) 