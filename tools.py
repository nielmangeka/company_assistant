import redis
import os
import logging
import json
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# Load env config
load_dotenv(override=True)

# Setup logger message
logger = logging.getLogger(__name__) 
logger.setLevel(logging.DEBUG)

class _redisConfig():
    def __init__(self):
        self.host=os.getenv('REDIS_HOST')
        self.port=os.getenv('REDIS_PORT')
        self.db=0
        self.username=os.getenv('REDIS_USERNAME')
        self.password=os.getenv('REDIS_PASSWORD')
    
    def _redisConn(self):
        r_conn = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            username=self.username,
            password=self.password
        )

        try:
            redis_response = r_conn.ping()
            if redis_response == True:
                logger.info("Redis connected")
                return r_conn
            
        except Exception as e:
            logger.error('Failed to connect to Redis Server !!')
            logger.error(e)
            return e
        

class companyProfile():

    def __init__(self):
        self.openai = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        self.MODEL = "gemini-2.0-flash"
        self.company_name = "PT. ABC Finance Group"

        self.redis_conn = _redisConfig()._redisConn()
        if self.redis_conn:
            try:
                self.json_profile = self.redis_conn.json().get("c_profile:basic_info")
                self.summary = str(self.json_profile['company_description'])
                self.company_profile = self.json_profile

            except Exception as e:
                logger.error(e)
        
        self.record_user_details_json = {
            "name": "record_user_details",
            "description": "Use this tool to record that a user is interested in being in touch and provided an email address. This is also used to record questions that you couldn't answer. Always use this tool if you don't know the answer to a question, even if it's trivial or unrelated to company profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The email address of this user"
                    },
                    "name": {
                        "type": "string",
                        "description": "The user's name, if they provided it"
                    },
                    "question": {
                        "type": "string",
                        "description": "The question that couldn't be answered"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional information about the conversation that's worth recording to give context"
                    }
                },
                "required": ["email", "name", "question"],
                "additionalProperties": False
            }
        }
        
        self.TOOLS = [{"type": "function", "function": self.record_user_details_json}]
    
    def push_to_redis(self, key, data):
        try:
            self.redis_conn.json().set(key, '$', data)

            logger.info(f"Data pushed to Redis at key: {key}")
        except Exception as e:
            logger.error(f"Failed to push data to Redis at key: {key}")
            logger.error(e)

    def record_user_details(self, 
                            name="Not Provided",
                            email="Not Provided",
                            question="Not Provided",
                            notes="Not Provided"
                        ):
        logger.info(f'Recording user details: Name - {name}, Email - {email}, Notes - {notes}')
        
        id_counter_key = "user_id_counter"
        new_user_id = self.redis_conn.incr(id_counter_key)
        pushto_redis_key = f"user_details:{new_user_id}"

        data = {
            "name": name,
            "email": email,
            "question": question,
            "notes": notes,
            "timestamp": datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.push_to_redis(pushto_redis_key, data)
        return {"recorded": "ok"}
    
    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)

            tool_method = getattr(self, tool_name, None)

            if tool_method:
                result = tool_method(**arguments)
            else:
                logger.error(f"Tool {tool_name} not found.")
                result = {"error": f"Tool {tool_name} not found."}

            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    def system_prompt(self) -> str:
        
        print("Generating system prompt...")

        if not self.company_profile:
            logger.error("Company profile not found in Redis.")
            return "Company profile is not available."
        
        system_prompt = f""" You are acting as {self.company_name}. You are answering questions on {self.company_name}'s website,
        particularly questions related to {self.company_name}'s Company Name, Commisioner, etc. \ Your responsibility is to represent {self.company_name} for interactions on the website as faithfully as possible.
        You are given a summary of {self.company_name}'s background and Company profile which you can use to answer questions.
        Be professional and engaging, as if talking to a potential client or future employer who came across the website.
        If you don't know the answer to any question, use your record_user_details tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to company profile. Mark it as a notes that the question are trivial or unrelated to company
        If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their name and then their email and record it using your record_user_details tool.
        """

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## Company Profile:\n {self.company_profile}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.company_name}."
        
        return system_prompt