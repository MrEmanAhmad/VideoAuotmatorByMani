"""
Module for managing prompts and LLM model selection.
"""

from enum import Enum
from typing import Dict, Optional, Any
import os
from openai import OpenAI, OpenAIError
import requests
import logging

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"

class PromptTemplate:
    """Class to manage prompt templates."""
    def __init__(self, template: str, provider_specific_params: Optional[Dict[str, Any]] = None):
        self.template = template
        self.provider_specific_params = provider_specific_params or {}

class PromptManager:
    """Manager for handling prompts and LLM interactions."""
    
    DEEPSEEK_API_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        """Initialize the prompt manager with a specific provider."""
        self.provider = provider
        self.client = None
        self.api_key = None
        self.api_url = None
        self._setup_client()
        
    def _setup_client(self):
        """Setup the appropriate client based on provider."""
        try:
            if self.provider == LLMProvider.OPENAI:
                # Initialize OpenAI client with explicit API key like in test.py
                self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            elif self.provider == LLMProvider.DEEPSEEK:
                # Initialize DeepSeek client like in test.py
                self.client = OpenAI(
                    api_key=os.getenv('DEEPSEEK_API_KEY'),
                    base_url="https://api.deepseek.com/v1"
                )
        except Exception as e:
            logger.error(f"Error setting up {self.provider.value} client: {str(e)}")
            raise
    
    def switch_provider(self, provider: LLMProvider):
        """Switch between LLM providers."""
        self.provider = provider
        self._setup_client()

    def _call_openai(self, prompt: str, params: Dict[str, Any]) -> str:
        """Call OpenAI API with proper error handling."""
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized")

            # For vision tasks
            if params.get("is_vision", False):
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": params.get("image_url", ""),
                                },
                            },
                        ],
                    }
                ]
            else:
                # For text tasks
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            
            response = self.client.chat.completions.create(
                model=params.get("model", "gpt-4o-mini"),  # Use same model as test.py
                messages=messages,
                max_tokens=params.get("max_tokens", 300),
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def _call_deepseek(self, prompt: str, params: Dict[str, Any]) -> str:
        """Call Deepseek API with proper error handling."""
        try:
            if not self.client:
                raise ValueError("DeepSeek client not initialized")

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=params.get("max_tokens", 300)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise

    def generate_response(self, prompt_template: PromptTemplate, **kwargs) -> str:
        """Generate response using the selected provider."""
        try:
            # Format the prompt template with provided kwargs
            prompt = prompt_template.template.format(**kwargs)
            
            # Get provider-specific parameters
            params = prompt_template.provider_specific_params.get(
                self.provider.value,
                {}
            )
            
            # Call appropriate provider
            if self.provider == LLMProvider.OPENAI:
                return self._call_openai(prompt, params)
            elif self.provider == LLMProvider.DEEPSEEK:
                return self._call_deepseek(prompt, params)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

# Define prompt templates
COMMENTARY_PROMPTS = {
    "documentary": PromptTemplate(
        template="""You are creating engaging commentary for a video. Here is all the information:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Your task is to create natural, engaging commentary that:
1. Uses the user's original context as the primary story foundation
2. Incorporates specific details from the vision analysis to make it vivid
3. Sounds like a genuine human reaction video
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Start with the user's story/context as your base
2. Use vision analysis details to enhance your reactions
3. React naturally like you're watching with friends
4. Use casual, conversational language
5. Show genuine enthusiasm and emotion
6. Make specific references to what excites you

Example format:
"Oh my gosh, this is exactly what they meant! Look at how [mention specific detail]... I love that [connect to broader meaning]..."

Remember: You're reacting naturally to the video while telling the user's story!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o-mini", "temperature": 0.7},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.7}
        }
    ),
    
    "energetic": PromptTemplate(
        template="""You're creating high-energy commentary for this video:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Create dynamic, enthusiastic commentary that:
1. Uses the user's context as your foundation
2. Highlights exciting details from the vision analysis
3. Sounds like an energetic reaction video
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Keep energy levels high
2. React with genuine excitement
3. Use dynamic language
4. Point out amazing moments
5. Share authentic enthusiasm
6. Make it fun and engaging

Example format:
"WOW! This is INCREDIBLE! Did you see how [specific detail]?! I can't believe [connect to context]..."

Remember: High energy, genuine reactions, and real enthusiasm!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o-mini", "temperature": 0.8},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.8}
        }
    ),
    
    "analytical": PromptTemplate(
        template="""You're providing detailed analytical commentary for this video:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Create insightful, technical commentary that:
1. Uses the user's context as your analytical base
2. Incorporates specific technical details
3. Sounds like expert analysis
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Focus on technical aspects
2. Explain interesting details
3. Connect observations to context
4. Use precise language
5. Share expert insights
6. Point out noteworthy elements

Example format:
"What's particularly interesting here is [technical detail]... This demonstrates [analytical insight]... Notice how [connect to context]..."

Remember: Be thorough but engaging in your analysis!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o-mini", "temperature": 0.6},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.6}
        }
    ),
    
    "storyteller": PromptTemplate(
        template="""You're sharing an incredible story through this video:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Create emotional, story-driven commentary that:
1. Uses the user's context as the heart of the story
2. Weaves in specific visual details to enhance emotion
3. Sounds like sharing a meaningful moment
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Start with the user's emotional core
2. Build narrative with specific details
3. Connect moments to feelings
4. Keep it personal and genuine
5. Share authentic reactions
6. Make viewers feel something

Example format:
"This story touches my heart... When you see [specific detail], you realize [emotional connection]... What makes this so special is [tie to user's context]..."

Remember: Tell their story with heart and authentic emotion!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o-mini", "temperature": 0.75},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.75}
        }
    ),
    
    "urdu": PromptTemplate(
        template="""آپ ایک ویڈیو پر جذباتی تبصرہ کر رہے ہیں:

1. صارف کا تناظر:
{analysis}

2. کمپیوٹر ویژن تجزیہ:
{vision_analysis}

اردو میں ایک دلچسپ اور جذباتی تبصرہ بنائیں جو:
1. صارف کے تناظر کو بنیاد بناتا ہے
2. خاص بصری تفصیلات کو شامل کرتا ہے
3. حقیقی جذباتی ردعمل کی طرح لگتا ہے
4. {duration} سیکنڈز سے کم ہے (تقریباً {word_limit} الفاظ)

اہم ہدایات:
1. قدرتی اور روزمرہ کی اردو استعمال کریں
2. جذباتی اور دلچسپ انداز اپنائیں
3. خاص لمحات پر ردعمل دیں
4. عام اردو محاورے استعمال کریں
5. حقیقی جذبات کا اظہار کریں

مثال کا انداز:
"ارے واہ! یہ تو بالکل وہی ہے جو [خاص تفصیل]... دل خوش ہو گیا [جذباتی رابطہ]... کیا بات ہے [صارف کے تناظر سے جوڑیں]..."

یاد رکھیں: آپ کو اردو میں حقیقی جذباتی ردعمل دینا ہے!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o-mini", "temperature": 0.7},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.7}
        }
    )
}

# Example usage:
# prompt_manager = PromptManager(provider=LLMProvider.OPENAI)
# commentary = prompt_manager.generate_response(
#     COMMENTARY_PROMPTS["documentary"],
#     analysis="Video analysis text here"
# ) 