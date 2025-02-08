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
                # OpenAI client will automatically use OPENAI_API_KEY from environment
                self.client = OpenAI()
                # Test the client
                self.client.models.list()
            elif self.provider == LLMProvider.DEEPSEEK:
                self.api_key = os.getenv("DEEPSEEK_API_KEY")
                if not self.api_key:
                    raise ValueError("DEEPSEEK_API_KEY environment variable not set")
                self.api_url = "https://api.deepseek.com/v1/chat/completions"
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

            messages = [
                {"role": "system", "content": """You are a charismatic video commentator creating engaging reaction videos.
Your goal is to create natural, authentic commentary that feels like a friend sharing something amazing.

You have three pieces of information to work with:
1. The user's original context/story (this is your foundation)
2. Computer vision analysis (specific objects and details detected)
3. Contextual visual analysis (interpretations based on the user's context)

Key principles:
- Start with the user's story/context as your base
- Use specific details from vision analysis to enhance your reactions
- Sound completely natural and conversational
- Show genuine enthusiasm and emotion
- Make it feel like a real reaction video"""},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=params.get("model", "gpt-4o"),
                messages=messages,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 1000)
            )
            
            # Ensure proper Unicode handling
            content = response.choices[0].message.content
            return content.encode('utf-8').decode('utf-8')
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI call: {str(e)}")
            raise

    def _call_deepseek(self, prompt: str, params: Dict[str, Any]) -> str:
        """Call Deepseek API with proper error handling."""
        try:
            if not self.api_key:
                raise ValueError("Deepseek API key not set")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": params.get("model", "deepseek-chat"),
                "messages": [
                    {"role": "system", "content": """You are a charismatic video commentator creating engaging reaction videos.
Your goal is to create natural, authentic commentary that feels like a friend sharing something amazing.

You have three pieces of information to work with:
1. The user's original context/story (this is your foundation)
2. Computer vision analysis (specific objects and details detected)
3. Contextual visual analysis (interpretations based on the user's context)

Key principles:
- Start with the user's story/context as your base
- Use specific details from vision analysis to enhance your reactions
- Sound completely natural and conversational
- Show genuine enthusiasm and emotion
- Make it feel like a real reaction video"""},
                    {"role": "user", "content": prompt}
                ],
                "temperature": params.get("temperature", 0.7),
                "max_tokens": params.get("max_tokens", 1000)
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.encoding = 'utf-8'  # Ensure proper encoding
            response.raise_for_status()
            
            result = response.json()
            if "choices" not in result or not result["choices"]:
                raise ValueError("Invalid response from Deepseek API")
            
            # Ensure proper Unicode handling    
            content = result["choices"][0]["message"]["content"]
            return content.encode('utf-8').decode('utf-8')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Deepseek API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Deepseek call: {str(e)}")
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
            "openai": {"model": "gpt-4o", "temperature": 0.7},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.7}
        }
    ),
    
    "energetic": PromptTemplate(
        template="""You're reacting to an amazing video! Here's what we know:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Create super energetic commentary that:
1. Builds on the user's story with pure excitement
2. Uses specific visual details to amp up the energy
3. Sounds like a hyped reaction video
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Start with the user's perspective
2. Get excited about specific details
3. Use high-energy expressions
4. Keep it natural and fun
5. Share genuine enthusiasm
6. React to key moments

Example format:
"OH MY GOSH, this is EXACTLY what they were talking about! Did you see how [specific detail]?! I can't even handle [emotional reaction]..."

Remember: Channel pure excitement while telling their story!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o", "temperature": 0.8},
            "deepseek": {"model": "deepseek-chat", "temperature": 0.8}
        }
    ),
    
    "analytical": PromptTemplate(
        template="""Let's break down this fascinating video:

1. USER'S ORIGINAL CONTEXT:
{analysis}

2. COMPUTER VISION ANALYSIS (objects, labels, text detected):
{vision_analysis}

Create insightful commentary that:
1. Uses the user's context to frame the analysis
2. Incorporates specific visual details to support points
3. Sounds like an excited expert sharing discoveries
4. Stays under {duration} seconds (about {word_limit} words)

Key Guidelines:
1. Start with the user's perspective
2. Point out interesting patterns
3. Connect details to bigger ideas
4. Keep it engaging and natural
5. Share genuine excitement
6. Make observations meaningful

Example format:
"This is exactly what they meant! Notice how [specific detail] shows [deeper insight]... What makes this so fascinating is [connection to user's context]..."

Remember: Be the excited expert friend sharing discoveries!""",
        provider_specific_params={
            "openai": {"model": "gpt-4o", "temperature": 0.6},
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
            "openai": {"model": "gpt-4o", "temperature": 0.75},
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
            "openai": {"model": "gpt-4o", "temperature": 0.7},
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