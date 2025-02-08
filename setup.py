from setuptools import setup, find_packages

setup(
    name="video-processing-bot",
    version="1.0.0",
    packages=find_packages(include=['pipeline', 'pipeline.*']),
    package_data={
        'pipeline': ['*.py'],
    },
    include_package_data=True,
    install_requires=[
        'openai>=1.0.0',
        'python-dotenv>=0.19.0',
        'yt-dlp>=2023.11.16',
        'opencv-python>=4.8.0',
        'numpy>=1.24.0',
        'google-cloud-vision>=3.4.4',
        'google-cloud-texttospeech>=2.14.1',
        'cloudinary>=1.36.0',
        'requests>=2.31.0',
        'selenium>=4.15.2',
        'webdriver-manager>=4.0.1',
        'undetected-chromedriver>=3.5.3',
        'python-telegram-bot[http2]>=20.7',
        'httpx[http2]>=0.24.0',
        'psutil>=5.9.0'
    ],
    python_requires='>=3.10',
    description="A Telegram bot that generates engaging commentary for videos using AI, supporting multiple languages including Urdu",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    keywords='video, commentary, ai, telegram, bot, urdu',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'Natural Language :: Urdu',
        'Programming Language :: Python :: 3.10',
        'Topic :: Multimedia :: Video',
        'Topic :: Communications :: Chat',
    ],
) 