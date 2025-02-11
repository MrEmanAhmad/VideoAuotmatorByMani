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
import gc
import tracemalloc
import psutil

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
@st.cache_resource
def init_bot():
    """Initialize the VideoBot instance with caching"""
    return VideoBot()

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
    st.session_state.settings = init_bot().default_settings.copy()
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

# Add this at the start of the main content area
if 'initialized' not in st.session_state:
    cleanup_memory()
    st.session_state.initialized = True

# Add this function for memory cleanup
def cleanup_memory():
    """Force garbage collection and clear memory"""
    gc.collect()
    if hasattr(st.session_state, 'output_filename') and st.session_state.output_filename:
        try:
            os.remove(st.session_state.output_filename)
        except:
            pass
    
    # Clear any temp directories
    for path in Path().glob("temp_*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    for path in Path().glob("output_*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

# Initialize bot with caching
bot = init_bot()

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
                    
                    # Display video using cached function
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
                        cleanup_memory()
                    
                    cleanup_task = asyncio.create_task(delayed_cleanup())
                    
                except Exception as e:
                    st.error(f"Error handling video display: {str(e)}")
                    cleanup_memory()
    
    except Exception as e:
        st.error(f"❌ Error processing video: {str(e)}")
        cleanup_memory()
    finally:
        cleanup_memory()
        st.session_state.processing = False

# Run async processing
asyncio.run(process_video()) 