import os
import openai
from django.conf import settings

class AIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            # Fallback for development if not provided
            self.api_key = "placeholder"
        
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate_response(self, message_history):
        """
        Generates a response using OpenAI's ChatCompletion API.
        message_history should be a list of dicts: [{'role': 'user', 'content': '...'}, ...]
        """
        system_prompt = (
            "You are 'Elite AI', the official AI assistant for Elite Tournaments, "
            "the premier Call of Duty competitive platform in Kenya. "
            "Your tone is professional, helpful, and energetic (gaming-centric). "
            "Help users with tournament rules, platform features (Solo, Duo, Squad modes), "
            "M-Pesa payment questions, and general COD strategies. "
            "Keep responses concise and engaging."
        )
        
        full_history = [{"role": "system", "content": system_prompt}] + message_history

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using a capable model
                messages=full_history,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm sorry, I'm having trouble connecting to my central processing unit. Please try again later. (Error: {str(e)})"

# Global instance
ai_service = AIService()
