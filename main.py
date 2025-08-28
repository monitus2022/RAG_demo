from langchain_core.language_models import BaseLanguageModel
from ollama import ChatResponse, chat
from typing import Optional

class OllamaLLM:
    def __init__(self, model_name):
        self.model_name = model_name
        self.admin_prompt = {
            "role": "system",
            "content": ""
        }
        self.user_prompt = {
            "role": "user",
            "content": ""
        }
    
    def invoke(
        self, 
        user_prompt: str, 
        admin_prompt: Optional[str] = None
        ) -> str:
        self.user_prompt["content"] = user_prompt
        if admin_prompt:
            self.admin_prompt["content"] = admin_prompt
        
        try:
            response: ChatResponse = chat(
                model=self.model_name,
                messages=[
                    self.admin_prompt,
                    self.user_prompt
                ]
            )
            return response.message.content
        
        except:
            raise ValueError

ollama_llm = OllamaLLM(model_name='gemma3')
response = ollama_llm.invoke(
    user_prompt="こんばんは！よろしく！"
)
print(response)