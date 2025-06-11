import os
from openai import OpenAI
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class LLMHandler:
    def __init__(self, model: str = "gpt-3.5-turbo", system_prompt: str = "You are a helpful assistant who provides concise, direct, and to-the-point responses. Aim to be clear and informative while using the minimum number of words necessary. Keep your answers succinct and avoid unnecessary elaboration."):
        self.model = model
        self.system_prompt = system_prompt
        self.client = OpenAI()
        self.conversation_history = []
        
        if self.system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })
    
    def add_user_message(self, message: str):
        """Add a user message to conversation history"""
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
    
    def get_llm_response(self) -> Optional[str]:
        """Get response from LLM based on conversation history"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            llm_response = response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": llm_response
            })
            return llm_response
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            return None
    
    def clear_history(self):
        """Clear conversation history while keeping system prompt"""
        self.conversation_history = [msg for msg in self.conversation_history if msg["role"] == "system"]