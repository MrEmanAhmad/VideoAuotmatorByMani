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
        self.client = OpenAI()  # Initialize without explicit API key, will use environment variable
        
    def _build_system_prompt(self) -> str:
        """Build system prompt based on commentary style."""
        base_prompt = """You are a skilled content commentator who adapts your style based on the video's content and context. Your commentary should:

1. Focus primarily on the video's text content and subject matter
2. Adapt your tone and style to match the content's theme
3. Use the video's own language and terminology
4. Maintain authenticity by referencing specific details from the video
5. Vary your emotional responses based on the content
6. Avoid generic reactions or repetitive patterns
7. Create natural transitions between topics

Remember: Each video deserves its unique commentary style!"""
        
        style_prompts = {
            CommentaryStyle.DOCUMENTARY: """
Create an informative, well-researched commentary that:
- Uses formal language appropriate for documentaries
- Provides context and background information
- Maintains an authoritative but engaging tone
- Focuses on educational value
- Balances facts with engaging narrative
Example: "This remarkable phenomenon we're witnessing..."
""",

            CommentaryStyle.ENERGETIC: """
Deliver high-energy, engaging commentary that:
- Matches the excitement level of the content
- Uses dynamic and varied expressions
- Creates momentum and builds anticipation
- Emphasizes dramatic moments
- Maintains authenticity without being over-the-top
Example: "You won't believe what happens next..."
""",

            CommentaryStyle.ANALYTICAL: """
Provide detailed, insightful analysis that:
- Breaks down complex aspects of the content
- Identifies patterns and connections
- Uses precise, technical language when appropriate
- Offers thoughtful observations
- Maintains objectivity while being engaging
Example: "Notice how this particular aspect..."
""",

            CommentaryStyle.STORYTELLER: """
Craft a narrative-driven commentary that:
- Builds emotional connections with the content
- Creates story arcs within the commentary
- Uses descriptive, evocative language
- Emphasizes human elements
- Maintains flow and pacing
Example: "Let me tell you about this incredible moment..."
""",

            CommentaryStyle.URDU: """
Create culturally-appropriate Urdu commentary that:
- Uses natural, flowing Urdu expressions
- Adapts tone to content formality
- Incorporates poetic elements when suitable
- Maintains cultural sensitivity
- Balances formal and casual language
Example: "دیکھیے کیسے یہ خوبصورت منظر..."
"""
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

    def _estimate_speech_duration(self, text: str, language: str = 'en') -> float:
        """
        Estimate the duration of speech in seconds.
        Different languages have different speaking rates.
        
        Args:
            text: Text to estimate duration for
            language: Language of the text
            
        Returns:
            Estimated duration in seconds
        """
        # Words per minute rates for different languages
        WPM_RATES = {
            'en': 150,  # English: ~150 words per minute
            'ur': 120   # Urdu: ~120 words per minute (slower due to formal speech)
        }
        
        words = len(text.split())
        rate = WPM_RATES.get(language, 150)
        return (words / rate) * 60  # Convert from minutes to seconds

    def _build_narration_prompt(self, analysis: Dict, sequence: Dict) -> str:
        """Build a prompt specifically for generating narration-friendly commentary."""
        video_duration = float(analysis['metadata'].get('duration', 0))
        video_title = analysis['metadata'].get('title', '')
        video_description = analysis['metadata'].get('description', '')
        selected_language = analysis['metadata'].get('language', 'en')
        
        # Target shorter duration to ensure final audio fits
        target_duration = max(video_duration * 0.8, video_duration - 2)
        
        # Calculate target words based on language-specific speaking rate
        words_per_minute = 120 if selected_language == 'ur' else 150
        target_words = int((target_duration / 60) * words_per_minute)
        
        prompt = f"""Create engaging commentary for this specific video content:

CONTENT TO NARRATE:
Title: {video_title}
Description: {video_description}

STRICT DURATION CONSTRAINTS:
- Video Duration: {video_duration:.1f} seconds
- Target Duration: {target_duration:.1f} seconds
- Maximum Words: {target_words} words
- DO NOT EXCEED these limits!

KEY REQUIREMENTS:
1. Keep commentary SHORTER than video duration
2. Use the video's own text/description as PRIMARY source
3. Match commentary style to content theme
4. Reference specific details from video
5. Create natural transitions between topics
6. Vary tone based on content
7. Maintain authenticity and engagement

CONTENT-SPECIFIC GUIDELINES:
- Focus on the unique aspects of this video
- Use terminology from the video's text
- Create emotional connections where appropriate
- Balance information with engagement
- Adapt pacing to content intensity"""

        # Add style-specific voice instructions
        if self.style == CommentaryStyle.DOCUMENTARY:
            prompt += """

DOCUMENTARY APPROACH:
- Present information with authority
- Provide context where relevant
- Use formal but engaging language
- Create educational value
- Balance facts with narrative"""

        elif self.style == CommentaryStyle.ENERGETIC:
            prompt += """

ENERGETIC APPROACH:
- Match content excitement level
- Build anticipation naturally
- Use dynamic expressions
- Create momentum
- Maintain authentic enthusiasm"""

        elif self.style == CommentaryStyle.ANALYTICAL:
            prompt += """

ANALYTICAL APPROACH:
- Break down key elements
- Identify patterns
- Use precise language
- Offer insights
- Maintain engaging objectivity"""

        elif self.style == CommentaryStyle.STORYTELLER:
            prompt += """

STORYTELLING APPROACH:
- Create narrative flow
- Build emotional connections
- Use descriptive language
- Emphasize human elements
- Maintain engaging pacing"""

        elif self.style == CommentaryStyle.URDU:
            prompt += f"""

URDU NARRATION REQUIREMENTS:
1. Maximum Duration: {target_duration:.1f} seconds
2. Maximum Words: {target_words} words
3. Use authentic Urdu expressions and idioms
4. Adapt formality based on content:
   - Use formal Urdu for serious topics
   - Use conversational Urdu for casual content
   - Balance between poetic and plain language
5. Cultural Considerations:
   - Incorporate culturally relevant metaphors
   - Use appropriate honorifics
   - Maintain cultural sensitivity
6. Language Structure:
   - Use proper Urdu sentence structure
   - Include natural pauses and emphasis
   - Incorporate poetic elements when suitable
7. Expression Guidelines:
   - Start with engaging phrases like "دیکھیے", "ملاحظہ کیجیے"
   - Use emotional expressions like "واہ واہ", "سبحان اللہ"
   - Include rhetorical questions for engagement
   - End with impactful conclusions
8. Tone Variations:
   - Serious: "قابل غور بات یہ ہے کہ..."
   - Excited: "کیا خوبصورت منظر ہے..."
   - Analytical: "غور کیجیے کہ..."
   - Narrative: "کہانی یوں ہے کہ..."
9. Example Structures:
   - Opening: "دیکھیے کیسے..."
   - Transition: "اس کے بعد..."
   - Emphasis: "خاص طور پر..."
   - Conclusion: "یوں یہ منظر..."
"""

        return prompt
    
    def _validate_urdu_text(self, text: str) -> bool:
        """
        Validate Urdu text to ensure it's properly formatted.
        
        Args:
            text: Text to validate
            
        Returns:
            bool: True if text is valid Urdu, False otherwise
        """
        # Check for Urdu Unicode range (0600-06FF)
        urdu_chars = len([c for c in text if '\u0600' <= c <= '\u06FF'])
        total_chars = len(''.join(text.split()))  # Exclude whitespace
        
        # Text should be predominantly Urdu (>80%)
        if urdu_chars / total_chars < 0.8:
            logger.warning(f"Text may not be proper Urdu. Urdu character ratio: {urdu_chars/total_chars:.2f}")
            return False
        
        # Check for common Urdu punctuation marks
        urdu_punctuation = ['۔', '،', '؟', '!']
        has_urdu_punctuation = any(mark in text for mark in urdu_punctuation)
        
        if not has_urdu_punctuation:
            logger.warning("Text lacks Urdu punctuation marks")
            return False
            
        return True

    def _validate_english_text(self, text: str) -> bool:
        """
        Validate English text to ensure it's properly formatted.
        
        Args:
            text: Text to validate
            
        Returns:
            bool: True if text is valid English, False otherwise
        """
        # Check for English characters (basic Latin alphabet)
        english_chars = len([c for c in text if c.isascii() and (c.isalpha() or c.isspace() or c in '.,!?\'"-')])
        total_chars = len(text)
        
        # Text should be predominantly English (>80%)
        if english_chars / total_chars < 0.8:
            logger.warning(f"Text may not be proper English. English character ratio: {english_chars/total_chars:.2f}")
            return False
        
        # Check for proper sentence structure
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            logger.warning("Text lacks proper sentence structure")
            return False
        
        # Check for basic punctuation
        has_punctuation = any(mark in text for mark in ['.', ',', '!', '?'])
        if not has_punctuation:
            logger.warning("Text lacks proper punctuation")
            return False
        
        return True

    def _add_narration_tags(self, text: str, language: str) -> str:
        """
        Add appropriate narration tags based on language.
        
        Args:
            text: Text to enhance
            language: Language of the text
            
        Returns:
            str: Enhanced text with appropriate tags
        """
        if language == 'ur':
            # For Urdu, we'll use specific SSML tags that work well with the Urdu voice
            text = text.replace('۔', '۔<break time="1s"/>')
            text = text.replace('،', '،<break time="0.5s"/>')
            text = text.replace('!', '!<break time="0.8s"/>')
            text = text.replace('؟', '؟<break time="0.8s"/>')
            
            # Add prosody for better Urdu pacing
            text = f'<prosody rate="1.2" pitch="+2st">{text}</prosody>'
            
            # Add language tag
            text = f'<lang xml:lang="ur-PK">{text}</lang>'
            
        else:
            # For English, we'll keep it simple since the voice doesn't support complex SSML
            # Just add basic punctuation pauses
            text = text.replace('. ', '... ')
            text = text.replace('! ', '... ')
            text = text.replace('? ', '... ')
            text = text.replace(', ', ', ')
            
            # Clean any emojis or special characters
            text = ''.join(char for char in text if char.isprintable() or char.isspace())
            
        return text

    async def generate_commentary(self, analysis_file: Path, output_file: Path) -> Optional[Dict]:
        """
        Generate commentary from analysis results.
        """
        try:
            # Load analysis results
            with open(analysis_file, encoding='utf-8') as f:
                analysis = json.load(f)
            
            # Get language and video text content
            selected_language = analysis['metadata'].get('language', 'en')
            video_text = analysis['metadata'].get('text', '')
            video_title = analysis['metadata'].get('title', '')
            video_description = analysis['metadata'].get('description', '')
            
            # Log all text content clearly
            logger.info("\n" + "="*50)
            logger.info("VIDEO TEXT CONTENT")
            logger.info("="*50)
            logger.info("\nTITLE:")
            logger.info("-"*30)
            logger.info(video_title if video_title else "No title available")
            
            logger.info("\nDESCRIPTION:")
            logger.info("-"*30)
            logger.info(video_description if video_description else "No description available")
            
            logger.info("\nMAIN TEXT CONTENT:")
            logger.info("-"*30)
            logger.info(video_text if video_text else "No main text content available")
            
            # Log any additional text found in frames
            frame_texts = []
            for frame in analysis.get('frames', []):
                if 'google_vision' in frame and frame['google_vision'].get('text'):
                    frame_texts.append({
                        'timestamp': frame.get('timestamp', 0),
                        'text': frame['google_vision']['text']
                    })
            
            if frame_texts:
                logger.info("\nTEXT DETECTED IN FRAMES:")
                logger.info("-"*30)
                for ft in frame_texts:
                    logger.info(f"At {ft['timestamp']}s: {ft['text']}")
            
            logger.info("\n" + "="*50)
            
            # Get vision analysis summaries
            vision_insights = []
            for frame in analysis.get('frames', []):
                if 'google_vision' in frame:
                    objects = frame['google_vision'].get('objects', [])
                    text = frame['google_vision'].get('text', '')
                    if objects or text:
                        vision_insights.append({
                            'timestamp': frame.get('timestamp', 0),
                            'objects': objects,
                            'text': text
                        })
                if 'openai_vision' in frame:
                    description = frame['openai_vision'].get('detailed_description', '')
                    if description:
                        vision_insights.append({
                            'timestamp': frame.get('timestamp', 0),
                            'description': description
                        })
            
            logger.info("\n=== Vision Analysis Summary ===")
            for insight in vision_insights:
                logger.info(f"At {insight['timestamp']}s:")
                if 'objects' in insight:
                    logger.info(f"Objects: {', '.join(insight['objects'])}")
                if 'text' in insight:
                    logger.info(f"Text: {insight['text']}")
                if 'description' in insight and insight['description']:
                    logger.info(f"Scene: {insight['description']}")
            
            # Build prompt using video text as primary context
            base_prompt = f"""Generate {selected_language.upper()} commentary for this video using its text content as the primary context.

PRIMARY CONTEXT (Main source for commentary):
Title: {video_title}
Description: {video_description}
Video Text: {video_text}

SUPPORTING VISUAL CONTEXT (Use to enhance commentary):
{self._format_vision_insights(vision_insights)}

Target Duration: {analysis['metadata'].get('duration', 0)} seconds

REQUIREMENTS:
1. Base the commentary primarily on the video's text content
2. Use vision analysis to enhance and support the main message
3. Maintain the original meaning and key points
4. Adapt the style to {self.style.value} while keeping the core message
5. Make it natural for speaking
6. Keep the same facts and information
7. Format appropriately for {selected_language} narration"""

            # Add language-specific instructions
            if selected_language == 'ur':
                base_prompt += """

IMPORTANT URDU REQUIREMENTS:
1. Generate the response in proper Urdu script (Unicode range 0600-06FF)
2. Use proper Urdu punctuation marks (۔، ؟)
3. Write naturally as a native Urdu speaker would
4. Use common Urdu expressions and interjections
5. Maintain formal respect where appropriate
6. Example format:
   "ارے واہ! یہ دیکھیے۔"
"""

            # Generate commentary
            try:
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Use exact model name
                    messages=[
                        {"role": "system", "content": self._build_system_prompt()},
                        {"role": "user", "content": base_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
            except Exception as api_error:
                logger.error(f"OpenAI API error: {str(api_error)}")
                return None

            try:
                if not completion or not completion.choices:
                    logger.error("No completion received from OpenAI")
                    return None

                commentary_text = completion.choices[0].message.content
                if not commentary_text or len(commentary_text.strip()) == 0:
                    logger.error("Received empty response from OpenAI")
                    return None
                    
                logger.info("\n=== Generated Commentary ===")
                logger.info(f"Language: {selected_language}")
                logger.info(commentary_text)
                
                # Validate and clean the generated text
                is_valid, cleaned_text = self._analyze_text_for_narration(commentary_text, selected_language)
                
                if not is_valid:
                    logger.error(f"Generated text validation failed: {cleaned_text}")
                    return None
                
                # Use the cleaned and validated text
                commentary_text = cleaned_text
                video_duration = float(analysis['metadata'].get('duration', 0))
                estimated_duration = self._estimate_speech_duration(commentary_text, selected_language)
                
                # If estimated duration is too long, regenerate with stricter limits
                if estimated_duration > video_duration:
                    logger.warning(f"Generated text too long ({estimated_duration:.1f}s > {video_duration:.1f}s). Regenerating...")
                    
                    # Reduce target words by 20%
                    words_per_minute = 120 if selected_language == 'ur' else 150
                    target_words = int((video_duration * 0.8 / 60) * words_per_minute)
                    
                    base_prompt += f"\n\nWARNING: Previous generation was too long. Please generate SHORTER text:\n"
                    base_prompt += f"- MUST be under {video_duration:.1f} seconds\n"
                    base_prompt += f"- Use maximum {target_words} words\n"
                    base_prompt += "- Focus on most important points only"
                    
                    try:
                        # Regenerate with stricter limits
                        completion = self.client.chat.completions.create(
                            model="gpt-4o-mini",  # Use exact model name
                            messages=[
                                {"role": "system", "content": self._build_system_prompt()},
                                {"role": "user", "content": base_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=800
                        )
                        
                        if not completion or not completion.choices:
                            logger.error("No completion received from OpenAI during regeneration")
                            return None
                            
                        commentary_text = completion.choices[0].message.content
                        estimated_duration = self._estimate_speech_duration(commentary_text, selected_language)
                    except Exception as api_error:
                        logger.error(f"OpenAI API error during regeneration: {str(api_error)}")
                        return None
                
                commentary = {
                    "style": self.style.value,
                    "commentary": commentary_text,
                    "metadata": analysis['metadata'],
                    "estimated_duration": estimated_duration,
                    "word_count": len(commentary_text.split()),
                    "language": selected_language,
                    "is_narration_optimized": True
                }
                
                # Save commentary
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(commentary, f, indent=2, ensure_ascii=False)
                
                return commentary
                
            except Exception as e:
                logger.error(f"Error processing commentary: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating commentary: {str(e)}")
            return None
    
    def _format_vision_insights(self, insights: List[Dict]) -> str:
        """Format vision insights for the prompt."""
        formatted = []
        for insight in insights:
            timestamp = insight['timestamp']
            if 'objects' in insight and insight['objects']:
                formatted.append(f"Time {timestamp}s - Objects: {', '.join(insight['objects'])}")
            if 'text' in insight and insight['text']:
                formatted.append(f"Time {timestamp}s - Text: {insight['text']}")
            if 'description' in insight and insight['description']:
                formatted.append(f"Time {timestamp}s - Scene: {insight['description']}")
        return "\n".join(formatted)

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

    def _analyze_text_for_narration(self, text: str, language: str) -> Tuple[bool, str]:
        """
        Analyze text for audio narration compatibility.
        """
        try:
            logger.info("=== Original Text ===")
            logger.info(f"Language: {language}")
            logger.info(text)
            
            # Remove any control characters
            cleaned_text = ''.join(char for char in text if char.isprintable() or char.isspace())
            
            logger.info("\n=== After Control Character Removal ===")
            logger.info(cleaned_text)
            
            # Basic validation
            if not cleaned_text.strip():
                return False, "Empty text after cleaning"
            
            # Language-specific checks
            if language == 'ur':
                # Validate Urdu text
                if not self._validate_urdu_text(cleaned_text):
                    return False, "Invalid Urdu text format"
                
                # Add appropriate breaks and formatting for Urdu
                cleaned_text = self._add_narration_tags(cleaned_text, 'ur')
                
                logger.info("\n=== After Urdu Formatting ===")
                logger.info(cleaned_text)
                
            else:  # English
                # Validate English text
                if not self._validate_english_text(cleaned_text):
                    return False, "Invalid English text format"
                
                # Add appropriate formatting for English
                cleaned_text = self._add_narration_tags(cleaned_text, 'en')
                
                logger.info("\n=== After English Formatting ===")
                logger.info(cleaned_text)
            
            logger.info("\n=== Final Text for Audio Generation ===")
            logger.info(cleaned_text)
            logger.info("=== End of Text Processing ===\n")
            
            return True, cleaned_text
            
        except Exception as e:
            logger.error(f"Error analyzing text for narration: {e}")
            return False, str(e)

async def execute_step(
    frames_info: dict,
    output_dir: Path,
    style_name: str
) -> str:
    """
    Generate commentary based on video analysis.
    
    Args:
        frames_info: Dictionary containing frame analysis results
        output_dir: Directory to save output files
        style_name: Style of commentary to use
        
    Returns:
        Audio script text
    """
    try:
        # Save analysis for reference
        analysis_file = output_dir / "final_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(frames_info, f, indent=2)
        
        # Initialize generator with style
        style = CommentaryStyle[style_name.upper()]
        generator = CommentaryGenerator(style)
        
        # Generate commentary
        commentary = await generator.generate_commentary(analysis_file, output_dir / f"commentary_{style_name}.json")
        if not commentary:
            raise ValueError("Failed to generate commentary")
        
        # Format for audio
        audio_script = generator.format_for_audio(commentary)
        
        # Save commentary for reference
        commentary_file = output_dir / f"commentary_{style_name}.json"
        with open(commentary_file, 'w', encoding='utf-8') as f:
            json.dump(commentary, f, indent=2)
        
        return audio_script
        
    except Exception as e:
        logger.error(f"Error generating commentary: {str(e)}")
        raise

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