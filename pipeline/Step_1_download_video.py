"""
Step 1: Video download module
Downloads videos from various sources using yt-dlp
"""

import logging
import os
import re
from pathlib import Path
from typing import Tuple, Dict, Optional, Any
import yt_dlp
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Constants
MAX_VIDEO_DURATION = 120  # Maximum video duration in seconds (2 minutes)

class VideoDownloader:
    """Downloads videos using yt-dlp."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize video downloader.
        
        Args:
            output_dir: Directory to save downloaded videos
        """
        self.output_dir = output_dir
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure compatibility."""
        # Convert x.com to twitter.com
        if 'x.com' in url:
            url = url.replace('x.com', 'twitter.com')
        # Ensure HTTPS
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        return url
        
    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize the filename to remove problematic characters.
        
        Args:
            title: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces and dots with underscores
        title = re.sub(r'[\s.]+', '_', title)
        # Ensure it's not empty and not too long
        if not title:
            title = 'video'
        return title[:100].strip('_')  # Limit length to 100 chars
        
    def _get_ydl_opts(self, is_twitter: bool = False) -> Dict[str, Any]:
        """Get yt-dlp options."""
        video_dir = self.output_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Use timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        opts = {
            'outtmpl': str(video_dir / f'video_{timestamp}.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'verbose': True,
            'format': 'best',
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'quiet': False,
            'extract_flat': False,
            'cookiefile': None,
            'source_address': '0.0.0.0',
            'force_generic_extractor': False,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_requests': 1,
            'max_sleep_interval_requests': 5,
            'http_chunk_size': 10485760,
            'retries': 10,
            'fragment_retries': 10,
            'retry_sleep_functions': {'http': lambda n: 5},
            'socket_timeout': 30,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
                'Origin': 'https://twitter.com'
            },
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4'
            }]
        }
        
        if is_twitter:
            opts.update({
                'extractor_args': {
                    'twitter': {
                        'api_key': None  # Let yt-dlp handle API key internally
                    }
                },
                'compat_opts': {
                    'no-youtube-unavailable-videos',
                    'no-youtube-prefer-utc',
                    'no-twitter-fail-incomplete'
                }
            })
        
        return opts
    
    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """
        Progress hook for download status.
        
        Args:
            d: Download status dictionary
        """
        if d['status'] == 'finished':
            logger.info('Download completed')
            logger.info(f'Downloaded file: {d["filename"]}')
                
    def download(self, url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            
        Returns:
            Tuple containing:
            - Success status (bool)
            - Video metadata (dict or None)
            - Video title (str or None)
        """
        try:
            # Normalize URL first
            url = self._normalize_url(url)
            logger.info(f"Downloading video from: {url}")
            
            # First extract info without downloading to check duration
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and info.get('duration', 0) > MAX_VIDEO_DURATION:
                    logger.error(f"Video duration ({info['duration']} seconds) exceeds maximum allowed duration ({MAX_VIDEO_DURATION} seconds)")
                    return False, None, None
            
            # If duration is acceptable, proceed with download
            is_twitter = 'twitter.com' in url
            with yt_dlp.YoutubeDL(self._get_ydl_opts(is_twitter)) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    metadata = {
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'description': info.get('description', ''),
                        'uploader': info.get('uploader', 'Unknown'),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'upload_date': info.get('upload_date', '')
                    }
                    
                    # Save metadata
                    metadata_file = self.output_dir / "video_metadata.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    return True, metadata, self._sanitize_filename(info.get('title', 'video'))
                
        except Exception as e:
            logger.error(f"yt-dlp download error: {str(e)}")
            
        return False, None, None

def execute_step(url_or_path: str, output_dir: Path) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Execute video download step.
    
    Args:
        url_or_path: Video URL or local file path
        output_dir: Directory to save downloaded video
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Video metadata (dict or None)
        - Video title (str or None)
    """
    downloader = VideoDownloader(output_dir)
    return downloader.download(url_or_path)

async def download_from_url(url: str, output_dir: Path) -> str:
    """
    Download video from URL asynchronously.
    
    Args:
        url: Video URL
        output_dir: Directory to save downloaded video
        
    Returns:
        Path to downloaded video file
    
    Raises:
        Exception if download fails
    """
    success, metadata, video_title = execute_step(url, output_dir)
    
    if not success:
        raise Exception("Failed to download video")
        
    # Look for the timestamp-based video file
    video_dir = output_dir / "video"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")  # Use partial timestamp for matching
    video_files = list(video_dir.glob(f"video_{timestamp}*.mp4"))
    
    if not video_files:
        raise Exception("Downloaded video file not found")
        
    # Return the most recently created file if multiple matches
    video_path = max(video_files, key=lambda p: p.stat().st_mtime)
    return str(video_path) 