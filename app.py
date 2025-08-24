from tools import _redisConfig, companyProfile
from dotenv import load_dotenv
import gradio as gr
import os
import logging

# Load environment variables
load_dotenv(override=True)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

agent_conn = companyProfile().system_prompt()

def chat(message, history):
    from openai import OpenAI
    openai = OpenAI(
        api_key=os.getenv("GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    """Function to handle chat messages and maintain conversation history.
    """
    logger.debug(f"Received message: {message}")

    messages = [{"role": "system", "content": agent_conn}] + history + [{"role": "user", "content": message}]

    done = False
    while not done:
        response = openai.chat.completions.create(model=companyProfile().MODEL, messages=messages, tools=companyProfile().TOOLS)
        if response.choices[0].finish_reason == "tool_calls":
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = companyProfile().handle_tool_call(tool_calls)
            messages.append(message)
            messages.extend(results)
        else:
            done = True
    
    return response.choices[0].message.content

if __name__ == "__main__":
    gr.ChatInterface(fn=chat, type="messages").launch(share=True)