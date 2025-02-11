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
import tweepy
import requests
import json

logger = logging.getLogger(__name__)

class VideoDownloader:
    """Downloads videos using yt-dlp with fallback options."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize video downloader.
        
        Args:
            output_dir: Directory to save downloaded video
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
            title: Original video title
            
        Returns:
            Sanitized filename
        """
        # Remove emojis and special characters
        title = re.sub(r'[^\w\s-]', '', title)
        # Replace spaces and dashes with underscores
        title = re.sub(r'[-\s]+', '_', title)
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
            'ignoreerrors': False,
            'no_warnings': False,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Dest': 'document',
                'Referer': 'https://twitter.com/',
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
                        'api_key': None
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
    
    def _try_twitter_api_download(self, url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Try downloading Twitter video using Twitter API."""
        try:
            # Initialize Twitter API client if credentials are available
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            if not bearer_token:
                return False, None, None
                
            client = tweepy.Client(bearer_token=bearer_token)
            
            # Extract tweet ID from URL
            tweet_id = re.search(r'/status/(\d+)', url)
            if not tweet_id:
                return False, None, None
                
            tweet_id = tweet_id.group(1)
            
            # Get tweet info
            tweet = client.get_tweet(
                tweet_id,
                expansions=['attachments.media_keys'],
                media_fields=['url', 'variants']
            )
            
            if not tweet.includes or 'media' not in tweet.includes:
                return False, None, None
                
            # Get video URL from media variants
            media = tweet.includes['media'][0]
            if hasattr(media, 'variants'):
                # Get highest quality video URL
                video_url = max(
                    (v for v in media.variants if v['content_type'] == 'video/mp4'),
                    key=lambda x: x.get('bit_rate', 0)
                )['url']
                
                # Download video
                video_dir = self.output_dir / "video"
                video_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = video_dir / f'video_{timestamp}.mp4'
                
                response = requests.get(video_url, stream=True)
                with open(video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                metadata = {
                    'title': f'Twitter_Video_{tweet_id}',
                    'description': tweet.data.text if tweet.data else '',
                    'uploader': 'Twitter',
                    'upload_date': ''
                }
                
                return True, metadata, f'Twitter_Video_{tweet_id}'
                
        except Exception as e:
            logger.error(f"Twitter API download error: {str(e)}")
            
        return False, None, None
                
    def download(self, url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Download video from URL with fallback options.
        
        Args:
            url: Video URL
            
        Returns:
            Tuple containing:
            - Success status (bool)
            - Video metadata (dict or None)
            - Video title (str or None)
        """
        url = self._normalize_url(url)
        logger.info(f"Downloading video from: {url}")
        
        # Try yt-dlp first
        try:
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
            
            # For Twitter videos, try Twitter API as fallback
            if 'twitter.com' in url:
                logger.info("Attempting Twitter API fallback...")
                success, metadata, title = self._try_twitter_api_download(url)
                if success:
                    return success, metadata, title
        
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
    # Check if input is a local file
    if os.path.isfile(url_or_path):
        try:
            # Create video directory
            video_dir = output_dir / "video"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to output directory
            import shutil
            filename = os.path.basename(url_or_path)
            sanitized_name = VideoDownloader(output_dir)._sanitize_filename(filename)
            dest_path = video_dir / f"{sanitized_name}.mp4"
            shutil.copy2(url_or_path, dest_path)
            
            # Create basic metadata
            metadata = {
                'title': sanitized_name,
                'duration': 0,  # Will be updated later
                'description': 'Local video file',
                'uploader': 'Local',
                'upload_date': ''
            }
            
            return True, metadata, sanitized_name
            
        except Exception as e:
            logger.error(f"Error copying local file: {str(e)}")
            return False, None, None
    
    # Download from URL
    downloader = VideoDownloader(output_dir)
    success, metadata, video_title = downloader.download(url_or_path)
    
    if not success:
        logger.error("Video download failed")
        
    return success, metadata, video_title 

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