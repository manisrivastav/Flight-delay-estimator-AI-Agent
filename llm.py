#ENABLED to use with Ollama in LOCAL

# from langchain_community.chat_models import ChatOllama
 
# llm = ChatOllama(model="mistral")
 
 
# def assess_delay(flight, weather):
#     """
#     Use LLM to estimate delay probability.
#     Weather is already fetched via MCP.
#     """
#     print("In assess_delay")
#     prompt = f"""
# You are an aviation operations analyst.
 
# Observed facts:
# - Callsign: {flight['callsign']}
# - Departure window: {flight['window']}
# - Ground speed: {flight['speed_kt']} kt
 
# Weather:
# {weather}
 
# Estimate the probability of departure delay (0–1).
# Return JSON only with:
# - delay_probability
# - primary_factors
# """
 
#     response = llm.invoke(prompt)
#     print("Flight: "+str(flight)+"\nResponse: "+str(response.content))
#     return response.content


# Use this with groq API key (Faster predictions)
# import os
# from typing import List
# from pydantic import BaseModel, Field
# from langchain_groq import ChatGroq

# from dotenv import load_dotenv

# # This looks for the .env file and loads the variables
# load_dotenv()

# # 1. Define the expected JSON structure
# class DelayAssessment(BaseModel):
#     delay_probability: float = Field(description="Probability of delay between 0 and 1")
#     primary_factors: List[str] = Field(description="List of weather or operational factors causing delay")

# # 2. Initialize the LLM (Fast & Free via Groq)
# # Models like llama-3.3-70b offer excellent reasoning for free
# llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
#     temperature=0,
#     api_key=os.environ.get("GROQ_API_KEY")
# )

# # Bind the structured output to the LLM
# structured_llm = llm.with_structured_output(DelayAssessment)

# def assess_delay(flight, weather):
#     # """
#     # Estimates delay probability using hosted LLM with guaranteed JSON output.
#     # """
#     # prompt = f"""
#     # You are an aviation operations analyst.
    
#     # Observed facts:
#     # - Callsign: {flight.get('callsign', 'Unknown')}
#     # - Departure window: {flight.get('window', 'Unknown')}
#     # - Ground speed: {flight.get('speed_kt', 0)} kt
    
#     # Weather:
#     # {weather}
    
#     # Estimate the probability of departure delay (0–1) along with primary factors of delay in two to three lines.
#     # """
    
#     """
#     Use LLM to estimate delay probability.
#     Weather is already fetched via MCP.
#     """
#     print("In assess_delay")
#     prompt = f"""
# You are an aviation operations analyst.
 
# Observed facts:
# - Callsign: {flight['callsign']}
# - Departure window: {flight['window']}
# - Ground speed: {flight['speed_kt']} kt
 
# Weather:
# {weather}
 
# Estimate the probability of departure delay (0–1).
# Return JSON only with:
# - delay_probability
# - detailed two liner on primary_factors
# """
#     # Returns a DelayAssessment object directly (no manual parsing needed!)
#     response = structured_llm.invoke(prompt)
    
#     print(f"Flight: {flight['callsign']} | Probability: {response.delay_probability} | RESPONSE: {response}")
#     return response.dict()

# =============================================================================
# Hugging Face LLM integration (ACTIVE)
#
# Uses Qwen/Qwen2.5-7B-Instruct via the Hugging Face Inference API.
# Requires HUGGINGFACEHUB_API_TOKEN in .env.
#
# To switch providers, comment out this section and uncomment one of the
# alternatives above (Ollama for local, Groq for cloud).
# =============================================================================

import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

# Load environment variables from .env (expects HUGGINGFACEHUB_API_TOKEN)
load_dotenv()

# 1. Expanded Schema for richer data
class DelayAssessment(BaseModel):
    delay_probability: float = Field(description="Probability of departure delay (0.0 to 1.0)")
    primary_factors: str = Field(description="A technical breakdown of weather/operational impacts")
    risk_level: str = Field(description="Low, Moderate, High, or Critical")

def assess_delay(flight, weather):
    """
    Detailed flight delay assessment using Qwen 2.5.
    Forces the LLM to provide technical reasoning based on METAR/TAF data.
    """
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    # We stay with Qwen 2.5 7B as it's currently the most stable on the 2026 router
    client = InferenceClient(
        model="Qwen/Qwen2.5-7B-Instruct", 
        token=hf_token
    )

    # 2. Expert-Level System Prompt
    system_message = (
        "You are an expert Aviation Operations Center (AOC) analyst. "
        "Analyze METAR/TAF weather against flight parameters. "
        "Provide a technical, multi-factor analysis of why a delay might occur. "
        "Include specifics like visibility (SM), ceiling height (ft), and wind gusts if relevant. "
        "Return ONLY a JSON object."
    )

    # 3. Data-Heavy User Prompt
    user_message = (
        f"ASSESS DELAY RISK:\n"
        f"Flight: {flight.get('callsign')} | Speed: {flight.get('speed_kt')}kt | Window: {flight.get('window')}\n\n"
        f"RAW WEATHER DATA:\n{weather}\n\n"
        f"Provide JSON with 'delay_probability' (float), 'risk_level' (string), "
        f"and 'primary_factors' (detailed 3-line technical explanation)."
    )

    print(f"--- Technical Analysis for {flight.get('callsign')} ---")

    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300, # Increased tokens for more detail
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        content = content.strip().replace("```json", "").replace("```", "").strip()
        
        result = json.loads(content)
        
        # Log the detailed factors to your console for debugging
        print(f"FACTORS: {result.get('primary_factors')}")
        return result

    except Exception as e:
        print(f"Analysis Error: {e}")
        return {
            "delay_probability": 0.0, 
            "primary_factors": "Technical analysis unavailable.",
            "risk_level": "Unknown"
        }