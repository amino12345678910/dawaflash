import os
from dotenv import load_dotenv

# Load environmental variables from our secret.env file
load_dotenv()

# Set up mock parameters to test with
from app.services.agents import run_ai_claim_agent

print("🚀 Initiating BimaSME AI Agent Integration Test...")

policy_id = "POL-TUNIS-123"
user_message = "I need to file a claim for crop damage. My loss is estimated at $1500."

# Run our AI agent
response = run_ai_claim_agent(policy_id, user_message)

print("\n🤖 CLAUDE'S RESPONSE:")
print(response)