import streamlit as st
import os
import sys
import logging
from pathlib import Path
import json
import tempfile
import asyncio
from datetime import datetime, timedelta
import shutil
from telegram.ext import ContextTypes
from telegram import Bot
import gc
import tracemalloc
import psutil

# Disable Streamlit's welcome message
st.set_option('client.showErrorDetails', False)
st.set_option('server.enableCORS', False)
st.set_option('server.enableXsrfProtection', False)
st.set_option('browser.gatherUsageStats', False)

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('streamlit_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Streamlit configuration
try:
    st.set_page_config(
        page_title="Video Processor",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items=None
    )
except Exception as e:
    logger.error(f"Failed to set page config: {str(e)}")
    sys.exit(1)

# Import required modules
try:
    from new_bot import VideoBot
    import json
    import shutil
    from datetime import datetime, timedelta
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    st.error(f"Failed to import required modules: {str(e)}")
    sys.exit(1)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.processing = False
    st.session_state.bot = None
    st.session_state.error = None

def init_bot():
    """Initialize the VideoBot with proper error handling"""
    if not st.session_state.initialized:
        try:
            config_path = Path("railway.json")
            if not config_path.exists():
                raise FileNotFoundError("railway.json not found")
            
            with open(config_path) as f:
                config = json.load(f)
            
            st.session_state.bot = VideoBot(config)
            st.session_state.initialized = True
            logger.info("VideoBot initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize VideoBot: {str(e)}"
            logger.error(error_msg)
            st.session_state.error = error_msg
            return False
    return True

def cleanup_memory():
    """Clean up temporary files and directories"""
    try:
        # Only clean if we're not processing
        if not st.session_state.processing:
            temp_dir = Path("analysis_temp")
            if temp_dir.exists():
                # Remove directories older than 1 hour
                current_time = datetime.now()
                for item in temp_dir.glob("*"):
                    if item.is_dir():
                        dir_time = datetime.fromtimestamp(item.stat().st_mtime)
                        if current_time - dir_time > timedelta(hours=1):
                            shutil.rmtree(item, ignore_errors=True)
            logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

# Main app
try:
    st.title("Video Processor")
    
    if not init_bot():
        st.error(st.session_state.error)
        st.stop()
    
    # Video URL input
    video_url = st.text_input("Enter YouTube Video URL")
    
    if st.button("Process Video", key="process_button"):
        if st.session_state.processing:
            st.warning("A video is already being processed. Please wait.")
        elif not video_url:
            st.warning("Please enter a video URL")
        else:
            try:
                st.session_state.processing = True
                with st.spinner("Processing video..."):
                    result = st.session_state.bot.process_video(video_url)
                st.success("Video processed successfully!")
                st.json(result)
            except Exception as e:
                error_msg = f"Error processing video: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
            finally:
                st.session_state.processing = False
                cleanup_memory()

except Exception as e:
    logger.error(f"Unexpected error in main app: {str(e)}")
    st.error(f"An unexpected error occurred. Please try again later.")

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
    if st.session_state.processing:
        logger.warning("Already processing a video")
        return
        
    st.session_state.processing = True
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
        st.session_state.processing = False
        cleanup_memory()
        logger.info("Video processing completed") 