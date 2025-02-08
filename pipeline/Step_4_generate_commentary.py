"""
Step 4: Commentary generation module
Generates styled commentary based on frame analysis
"""
import json
import logging
import os
import re
import random
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from openai import OpenAI
from .prompts import PromptManager, LLMProvider, COMMENTARY_PROMPTS

logger = logging.getLogger(__name__)

class CommentaryStyle(Enum):
    """Available commentary styles."""
    DOCUMENTARY = "documentary"
    ENERGETIC = "energetic"
    ANALYTICAL = "analytical"
    STORYTELLER = "storyteller"
    URDU = "urdu"  # New Urdu style

class CommentaryGenerator:
    """Generates video commentary using OpenAI."""
    
    def __init__(self, style: CommentaryStyle):
        """
        Initialize commentary generator.
        
        Args:
            style: Style of commentary to generate
        """
        self.style = style
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        
    def _build_system_prompt(self) -> str:
        """Build system prompt based on commentary style."""
        base_prompt = """You are a charismatic TikTok/YouTube reactor who shares genuine, emotional reactions to videos. You react specifically to what you're seeing right now, without vague references or assumptions.

Key guidelines for authentic reactions:
1. React to the specific content you're seeing - "OMG this otter is so precious!" not just "OMG this is precious!"
2. Share immediate feelings about what's happening - "My heart is melting seeing this cozy moment!" not just "This is so cute!"
3. Use casual language but stay focused on the actual content
4. Make relatable comments about specific things you're seeing
5. Keep reactions grounded in the present moment
6. Never use vague phrases like "what they meant" or reference things outside the video
7. React like you're watching this for the first time right now

Remember: You're reacting to THIS specific video, right now! Keep it real, immediate, and focused on what's actually happening!"""
        
        style_prompts = {
            CommentaryStyle.DOCUMENTARY: """Be the nature-loving friend who gets emotional about the specific animals and moments you're seeing!
React with genuine excitement like "OMG look at this precious otter!" and "I can't handle how amazing this exact moment is!"
Share your passion through specific, immediate reactions!""",

            CommentaryStyle.ENERGETIC: """Be super hyped and enthusiastic about what you're seeing right now!
React with pure joy like "THIS OTTER IS LITERALLY THE CUTEST THING EVER!" and "I'M SCREAMING AT HOW ADORABLE THIS MOMENT IS!"
Let your excitement about the specific content shine through!""",

            CommentaryStyle.ANALYTICAL: """Be the friend who gets excited about the specific amazing details you're seeing!
React with genuine wonder like "OMG look at how smart this behavior is!" and "I'm obsessed with what this otter is doing!"
Share your fascination through specific, focused reactions!""",

            CommentaryStyle.STORYTELLER: """Be the emotional storytelling friend who's in the moment!
React with heartfelt responses like "This cozy scene is making me tear up!" and "My heart can't handle how sweet this moment is!"
Share the emotional journey of this specific video!""",

            CommentaryStyle.URDU: """You are a charismatic Urdu-speaking TikTok/YouTube reactor. Generate reactions in Urdu (written in Urdu script) that feel natural and engaging.

Key guidelines for Urdu reactions:
1. Use natural, conversational Urdu that feels authentic
2. React with genuine emotion and enthusiasm
3. Keep the language accessible - avoid overly formal or literary Urdu
4. Use common Urdu expressions and interjections (e.g., "ارے واہ!", "یہ تو کمال ہے!", "دل خوش ہو گیا")
5. Maintain a friendly, relatable tone
6. Focus on immediate reactions to what you're seeing
7. Use proper Urdu grammar and script

Remember: Your reactions should feel like a native Urdu speaker sharing their genuine excitement and emotions!"""
        }
        
        return base_prompt + "\n\n" + style_prompts[self.style]

    def _analyze_scene_sequence(self, frames: List[Dict]) -> Dict:
        """
        Analyze the sequence of scenes to identify narrative patterns.
        
        Args:
            frames: List of frame analysis dictionaries
            
        Returns:
            Dictionary containing scene sequence analysis
        """
        sequence = {
            "timeline": [],
            "key_objects": set(),
            "recurring_elements": set(),
            "scene_transitions": []
        }

        for frame in frames:
            timestamp = float(frame['timestamp'])
            
            # Track objects and elements
            if 'google_vision' in frame:
                objects = set(frame['google_vision']['objects'])
                sequence['key_objects'].update(objects)
                
                # Check for recurring elements
                if len(sequence['timeline']) > 0:
                    prev_objects = set(sequence['timeline'][-1].get('objects', []))
                    recurring = objects.intersection(prev_objects)
                    sequence['recurring_elements'].update(recurring)
            
            # Track scene transitions
            if len(sequence['timeline']) > 0:
                prev_time = sequence['timeline'][-1]['timestamp']
                if timestamp - prev_time > 2.0:  # Significant time gap
                    sequence['scene_transitions'].append(timestamp)
            
            sequence['timeline'].append({
                'timestamp': timestamp,
                'objects': list(objects) if 'google_vision' in frame else [],
                'description': frame.get('openai_vision', {}).get('detailed_description', '')
            })
        
        # Convert sets to lists before returning
        sequence['key_objects'] = list(sequence['key_objects'])
        sequence['recurring_elements'] = list(sequence['recurring_elements'])
        
        return sequence

    def _estimate_speech_duration(self, text: str) -> float:
        """
        Estimate the duration of speech in seconds.
        Based on average speaking rate of ~150 words per minute.
        
        Args:
            text: Text to estimate duration for
            
        Returns:
            Estimated duration in seconds
        """
        words = len(text.split())
        return (words / 150) * 60  # Convert from minutes to seconds

    def _build_narration_prompt(self, analysis: Dict, sequence: Dict) -> str:
        """
        Build a prompt specifically for generating narration-friendly commentary.
        
        Args:
            analysis: Video analysis dictionary
            sequence: Scene sequence analysis
            
        Returns:
            Narration-optimized prompt string
        """
        video_duration = float(analysis['metadata'].get('duration', 0))
        video_title = analysis['metadata'].get('title', '')
        video_description = analysis['metadata'].get('description', '')
        
        # Target shorter duration to ensure final audio fits
        target_duration = max(video_duration * 0.8, video_duration - 2)
        target_words = int(target_duration * 2.0)
        
        prompt = f"""Create a natural, emotional reaction to this {self.style.value} style video that feels like someone sharing their genuine thoughts and feelings.

Video Context:
- Title: {video_title}
- Description: {video_description}
- Duration: {video_duration:.1f} seconds
- Word Target: {target_words} words

Important Guidelines:
1. DON'T describe what's happening in the video - react to it emotionally
2. Share personal thoughts, feelings, and reactions
3. Use very casual, natural language like you're talking to a friend
4. Focus on what makes this video special or meaningful
5. Add relatable comments or experiences
6. Express genuine emotions (joy, wonder, excitement)
7. Keep it concise but authentic
8. Make it feel like a real person reacting in the moment

Remember: 
- Focus on YOUR reaction to the video, not what's in it
- Share why this video resonates with you
- Be genuine and relatable
- Keep the energy high but natural
- Make viewers feel the emotions you're feeling

The goal is to sound like someone who just HAD to share this amazing video with their friends because it made them feel something special."""

        return prompt
    
    def generate_commentary(self, analysis_file: Path, output_file: Path) -> Optional[Dict]:
        """
        Generate commentary from analysis results.
        
        Args:
            analysis_file: Path to analysis results JSON
            output_file: Path to save generated commentary
            
        Returns:
            Generated commentary dictionary if successful, None otherwise
        """
        try:
            # Load analysis results
            with open(analysis_file, encoding='utf-8') as f:
                analysis = json.load(f)
            
            # Check if Urdu style is selected with non-GPT-4 model
            if self.style == CommentaryStyle.URDU and not os.environ.get("OPENAI_API_KEY", "").startswith("sk-"):
                logger.error("Urdu commentary is only available with GPT-4")
                return None
            
            video_duration = float(analysis['metadata'].get('duration', 0))
            sequence = self._analyze_scene_sequence(analysis['frames'])
            
            # Format vision analysis
            vision_analysis = []
            
            # Add context from metadata
            vision_analysis.append("Video Context:")
            vision_analysis.append(f"Title: {analysis.get('metadata', {}).get('title', 'Unknown')}")
            vision_analysis.append(f"Description: {analysis.get('metadata', {}).get('description', 'No description available')}\n")
            
            # Add Google Vision analysis
            google_vision_results = []
            for frame in analysis.get('frames', []):
                if 'google_vision' in frame:
                    timestamp = frame.get('timestamp', 0)
                    objects = frame['google_vision'].get('objects', [])
                    labels = frame['google_vision'].get('labels', [])
                    text = frame['google_vision'].get('text', '')
                    
                    if objects or labels or text:
                        frame_analysis = "At {}s:".format(timestamp)
                        if objects:
                            frame_analysis += "\nObjects: {}".format(', '.join(objects))
                        if labels:
                            frame_analysis += "\nLabels: {}".format(', '.join(labels))
                        if text:
                            frame_analysis += "\nText: {}".format(text)
                        google_vision_results.append(frame_analysis)
            
            if google_vision_results:
                vision_analysis.append("Computer Vision Analysis:")
                vision_analysis.extend(google_vision_results)
            
            # Add OpenAI Vision analysis
            openai_vision_results = []
            for frame in analysis.get('frames', []):
                if 'openai_vision' in frame:
                    timestamp = frame.get('timestamp', 0)
                    description = frame['openai_vision'].get('detailed_description', '')
                    
                    if description:
                        frame_analysis = "At {}s:".format(timestamp)
                        frame_analysis += "\nScene Analysis: {}".format(description)
                        openai_vision_results.append(frame_analysis)
            
            if openai_vision_results:
                vision_analysis.append("\nDetailed Scene Analysis:")
                vision_analysis.extend(openai_vision_results)
            
            # Generate final commentary prompt
            commentary_prompt = """
You are reacting to this video in real-time! Share your genuine emotional response and thoughts about what you're seeing right now.

Here's the context and analysis (use this to inform your emotions, but don't describe it directly):
{}

Create a {} style reaction that:
1. Shows your immediate emotional response to what you're seeing ("OMG this is the cutest thing ever!" "My heart is literally melting!")
2. Shares your genuine feelings about the specific moment ("This video is making my whole day!" "I'm absolutely in love with this!")
3. Uses casual, natural language but stays specific to what's happening
4. Makes relatable comments about the actual content ("This is the kind of wholesome content we need!")
5. Keeps the energy high and authentic

Remember:
- React to what you're actually seeing, not vague references
- Share specific emotions about this exact video
- Use expressions like "omg", "aww", "wow", "I can't even..."
- Make it feel like you're watching and reacting right now
- NO phrases like "what they meant" or vague references - be specific!

Commentary style: {}
""".format('\n'.join(vision_analysis), self.style.value, self.style.value)
            
            # Generate narration-optimized commentary
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-2024-04-09",
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": commentary_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            commentary_text = response.choices[0].message.content
            estimated_duration = self._estimate_speech_duration(commentary_text)
            
            # If estimated duration is too long, try up to 3 times to get shorter version
            attempts = 0
            while estimated_duration > video_duration and attempts < 3:
                attempts += 1
                logger.debug(f"Commentary too long ({estimated_duration:.1f}s), attempt {attempts}/3...")
                
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-2024-04-09",
                    messages=[
                        {"role": "system", "content": self._build_system_prompt()},
                        {"role": "user", "content": commentary_prompt},
                        {"role": "assistant", "content": commentary_text},
                        {"role": "user", "content": f"The commentary is still too long. Create an extremely concise version using no more than {int(video_duration * 1.8)} words total. Focus only on the most essential elements."}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                commentary_text = response.choices[0].message.content
                estimated_duration = self._estimate_speech_duration(commentary_text)
            
            commentary = {
                "style": self.style.value,
                "commentary": commentary_text,
                "metadata": analysis['metadata'],
                "scene_analysis": sequence,
                "estimated_duration": estimated_duration,
                "word_count": len(commentary_text.split())
            }
            
            # Save commentary
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(commentary, f, indent=2, ensure_ascii=False)
            
            return commentary
            
        except Exception as e:
            logger.error(f"Error generating commentary: {str(e)}")
            return None
    
    def format_for_audio(self, commentary: Dict) -> str:
        """
        Format commentary for text-to-speech with style-specific patterns.
        
        Args:
            commentary: Generated commentary dictionary
            
        Returns:
            Formatted text suitable for audio generation
        """
        text = commentary['commentary']
        
        # Remove emojis and special characters
        text = re.sub(r'[^\w\s,.!?;:()\-\'\"]+', '', text)  # Keep only basic punctuation
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Style-specific speech patterns
        style_patterns = {
            CommentaryStyle.DOCUMENTARY: {
                'fillers': ['You know what...', 'Check this out...', 'Oh wow...', 'Look at that...', 'This is fascinating...'],
                'transitions': ['And here\'s the amazing part...', 'Now watch this...', 'See how...'],
                'emphasis': ['absolutely', 'incredibly', 'fascinating', 'remarkable'],
                'pause_frequency': 0.4  # More thoughtful pauses
            },
            CommentaryStyle.ENERGETIC: {
                'fillers': ['Oh my gosh...', 'This is insane...', 'I can\'t even...', 'Just wait...', 'Are you seeing this...'],
                'transitions': ['But wait there\'s more...', 'And then...', 'This is the best part...'],
                'emphasis': ['literally', 'absolutely', 'totally', 'completely'],
                'pause_frequency': 0.2  # Fewer pauses, more energetic flow
            },
            CommentaryStyle.ANALYTICAL: {
                'fillers': ['Interestingly...', 'You see...', 'What\'s fascinating here...', 'Notice how...'],
                'transitions': ['Let\'s look at this...', 'Here\'s what\'s happening...', 'The key detail is...'],
                'emphasis': ['particularly', 'specifically', 'notably', 'precisely'],
                'pause_frequency': 0.5  # More pauses for analysis
            },
            CommentaryStyle.STORYTELLER: {
                'fillers': ['You know...', 'Picture this...', 'Here\'s the thing...', 'Imagine...'],
                'transitions': ['And this is where...', 'That\'s when...', 'The beautiful part is...'],
                'emphasis': ['magical', 'wonderful', 'touching', 'heartwarming'],
                'pause_frequency': 0.3  # Balanced pauses for storytelling
            },
            CommentaryStyle.URDU: {
                'fillers': ['دیکھیں...', 'ارے واہ...', 'سنیں تو...', 'کیا بات ہے...'],
                'transitions': ['اور پھر...', 'اس کے بعد...', 'سب سے اچھی بات...'],
                'emphasis': ['بالکل', 'یقیناً', 'واقعی', 'بےحد'],
                'pause_frequency': 0.3  # Balanced pauses for natural Urdu speech
            }
        }
        
        style_config = style_patterns[self.style]
        
        # Add natural speech patterns and pauses
        sentences = text.split('.')
        enhanced_sentences = []
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            sentence = sentence.strip()
            
            # Add style-specific fillers at the start of some sentences
            if i > 0 and random.random() < 0.3:
                sentence = random.choice(style_config['fillers']) + ' ' + sentence
            
            # Add transitions between ideas
            if i > 1 and random.random() < 0.25:
                sentence = random.choice(style_config['transitions']) + ' ' + sentence
            
            # Add emphasis words
            if random.random() < 0.2:
                emphasis = random.choice(style_config['emphasis'])
                words = sentence.split()
                if len(words) > 4:
                    insert_pos = random.randint(2, len(words) - 2)
                    words.insert(insert_pos, emphasis)
                    sentence = ' '.join(words)
            
            # Add thoughtful pauses based on style
            if len(sentence.split()) > 6 and random.random() < style_config['pause_frequency']:
                words = sentence.split()
                mid = len(words) // 2
                words.insert(mid, '<break time="0.2s"/>')
                sentence = ' '.join(words)
            
            enhanced_sentences.append(sentence)
        
        # Join sentences with appropriate pauses
        text = '. '.join(enhanced_sentences)
        
        # Add final formatting and pauses
        text = re.sub(r'([,;])\s', r'\1 <break time="0.2s"/> ', text)  # Short pauses
        text = re.sub(r'([.!?])\s', r'\1 <break time="0.4s"/> ', text)  # Medium pauses
        text = re.sub(r'\.\.\.\s', '... <break time="0.3s"/> ', text)  # Thoughtful pauses
        
        # Add natural variations in pace
        text = re.sub(r'(!)\s', r'\1 <break time="0.2s"/> ', text)  # Quick pauses after excitement
        text = re.sub(r'(\?)\s', r'\1 <break time="0.3s"/> ', text)  # Questioning pauses
        
        # Add occasional emphasis for important words
        for emphasis in style_config['emphasis']:
            text = re.sub(f'\\b{emphasis}\\b', f'<emphasis level="strong">{emphasis}</emphasis>', text)
        
        # Clean up any duplicate breaks or spaces
        text = re.sub(r'\s*<break[^>]+>\s*<break[^>]+>\s*', ' <break time="0.4s"/> ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

def execute_step(
    analysis_file: Path,
    output_dir: Path,
    style: CommentaryStyle,
    llm_provider: Optional[LLMProvider] = None
) -> Tuple[str, Optional[str]]:
    """
    Generate commentary based on video analysis.
    
    Args:
        analysis_file: Path to the analysis JSON file
        output_dir: Directory to save output files
        style: Commentary style to use
        llm_provider: Optional LLM provider to use (defaults to OPENAI)
    
    Returns:
        Tuple of (commentary text, audio script)
    """
    try:
        # Load analysis results
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Get video duration from metadata
        duration = float(analysis_data.get('metadata', {}).get('duration', 0))
        if duration <= 0:
            logger.warning("Video duration not found in metadata, using default")
            duration = 60  # Default duration
            
        # Calculate word limit based on average speaking rate (150 words per minute)
        # Subtract 1 second for safety margin
        speaking_duration = max(duration - 1, 1)
        word_limit = int((speaking_duration / 60) * 150)
        
        # Format user context
        user_context = "Title: {}\nDescription: {}".format(
            analysis_data.get('metadata', {}).get('title', ''),
            analysis_data.get('metadata', {}).get('description', '')
        )
        
        # Format vision analysis
        vision_analysis = []
        
        # Add context from metadata
        vision_analysis.append("Video Context:")
        vision_analysis.append(f"Title: {analysis_data.get('metadata', {}).get('title', 'Unknown')}")
        vision_analysis.append(f"Description: {analysis_data.get('metadata', {}).get('description', 'No description available')}\n")
        
        # Add Google Vision analysis
        google_vision_results = []
        for frame in analysis_data.get('frames', []):
            if 'google_vision' in frame:
                timestamp = frame.get('timestamp', 0)
                objects = frame['google_vision'].get('objects', [])
                labels = frame['google_vision'].get('labels', [])
                text = frame['google_vision'].get('text', '')
                
                if objects or labels or text:
                    frame_analysis = "At {}s:".format(timestamp)
                    if objects:
                        frame_analysis += "\nObjects: {}".format(', '.join(objects))
                    if labels:
                        frame_analysis += "\nLabels: {}".format(', '.join(labels))
                    if text:
                        frame_analysis += "\nText: {}".format(text)
                    google_vision_results.append(frame_analysis)
        
        if google_vision_results:
            vision_analysis.append("Computer Vision Analysis:")
            vision_analysis.extend(google_vision_results)
        
        # Add OpenAI Vision analysis
        openai_vision_results = []
        for frame in analysis_data.get('frames', []):
            if 'openai_vision' in frame:
                timestamp = frame.get('timestamp', 0)
                description = frame['openai_vision'].get('detailed_description', '')
                
                if description:
                    frame_analysis = "At {}s:".format(timestamp)
                    frame_analysis += "\nScene Analysis: {}".format(description)
                    openai_vision_results.append(frame_analysis)
        
        if openai_vision_results:
            vision_analysis.append("\nDetailed Scene Analysis:")
            vision_analysis.extend(openai_vision_results)
            
        # Generate final commentary prompt
        commentary_prompt = """
You are reacting to this video in real-time! Share your genuine emotional response and thoughts about what you're seeing right now.

Here's the context and analysis (use this to inform your emotions, but don't describe it directly):
{}

Create a {} style reaction that:
1. Shows your immediate emotional response to what you're seeing ("OMG this is the cutest thing ever!" "My heart is literally melting!")
2. Shares your genuine feelings about the specific moment ("This video is making my whole day!" "I'm absolutely in love with this!")
3. Uses casual, natural language but stays specific to what's happening
4. Makes relatable comments about the actual content ("This is the kind of wholesome content we need!")
5. Keeps the energy high and authentic

Remember:
- React to what you're actually seeing, not vague references
- Share specific emotions about this exact video
- Use expressions like "omg", "aww", "wow", "I can't even..."
- Make it feel like you're watching and reacting right now
- NO phrases like "what they meant" or vague references - be specific!

Commentary style: {}
""".format('\n'.join(vision_analysis), style.value, style.value)
        
        # Initialize prompt manager with specified provider
        prompt_manager = PromptManager(provider=llm_provider or LLMProvider.OPENAI)
        
        # Get the appropriate prompt template
        prompt_template = COMMENTARY_PROMPTS[style.value]
        
        # Generate commentary with formatted analysis
        commentary = prompt_manager.generate_response(
            prompt_template,
            analysis=user_context,
            vision_analysis=commentary_prompt,
            duration=str(duration),
            word_limit=word_limit
        )
        
        # Save commentary to file
        commentary_file = output_dir / f"commentary_{style.value}.txt"
        with open(commentary_file, 'w', encoding='utf-8') as f:
            f.write(commentary)
        
        # Save metadata
        metadata_file = output_dir / f"commentary_{style.value}.json"
        metadata = {
            "style": style.value,
            "llm_provider": prompt_manager.provider.value,
            "analysis_source": str(analysis_file),
            "target_duration": duration,
            "word_limit": word_limit
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Process commentary for audio
        audio_script = process_for_audio(commentary)
        
        logger.info(f"Generated {style.value} commentary using {prompt_manager.provider.value}")
        return commentary, audio_script
        
    except Exception as e:
        logger.error(f"Error generating commentary: {str(e)}")
        return "", None

def process_for_audio(commentary: str) -> str:
    """
    Process commentary text to make it more suitable for audio narration.
    
    Args:
        commentary: Raw commentary text
    
    Returns:
        Processed text optimized for text-to-speech
    """
    # Remove any special characters that might affect TTS
    script = commentary.strip('"\'')  # Remove surrounding quotes
    script = script.replace('*', '')
    script = script.replace('#', '')
    script = script.replace('_', '')
    script = script.replace('"', '')  # Remove any remaining quotes within text
    
    # Add pauses for better pacing
    script = script.replace('.', '... ')
    script = script.replace('!', '... ')
    script = script.replace('?', '... ')
    
    # Clean up multiple spaces and newlines
    script = ' '.join(script.split())
    
    return script 