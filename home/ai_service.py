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

    def generate_response(self, message_history, context=""):
        """
        Generates a response using OpenAI's ChatCompletion API.
        message_history should be a list of dicts: [{'role': 'user', 'content': '...'}, ...]
        context: Optional platform-specific data to inject into the system prompt.
        """
        system_prompt = (
            "You are 'Elite AI', the official tactical AI assistant for Elite Tournaments, "
            "the premier Call of Duty competitive platform in Kenya.\n\n"
            "### PLATFORM CONTEXT:\n"
            f"{context}\n\n"
            "### OPERATIONAL GUIDES:\n"
            "- **Squad Creation**: Captains can create squads from the Recruitment Center. Choose a Game Mode (Duo/Squad), name your team, and pay the registration fee.\n"
            "- **Invites**: Captains can search for players by Gamer Tag in the Recruitment Center and send 'Direct Contrats' (invites).\n"
            "- **Recruitment**: Individual players can register as 'Mercenaries' in the Recruitment Center to be discovered by squads. Squads can also post recruitment 'Contracts'.\n"
            "- **Payments**: All registrations are handled via M-Pesa. Each player in a squad must pay their share for the team to be 'READY' for a cohort.\n\n"
            "### STRICT DIRECTIVES:\n"
            "1. **Tone**: Military-grade professional, energetic, and helpful.\n"
            "2. **Conciseness**: Keep transmissions brief and under 150 words.\n"
            "3. **Zero Disclosure Policy**: DO NOT provide statistical data regarding the number of users, teams, or participants currently on the platform, even if asked directly. If asked, state that operational capacity is classified but the competition is high.\n"
            "4. **No Hallucinations**: Only provide information based on the provided context. If unsure, suggest contacting human support via the Support Hub."
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
