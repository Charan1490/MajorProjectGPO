# Enhanced PowerShell Script Generation Requirements

# Install required packages for enhanced policy research
google-generativeai>=0.3.0

# Environment Variables Required:
# GEMINI_API_KEY=your_api_key_here

# Usage Instructions:
# 1. Get a free Gemini API key from https://makersuite.google.com/app/apikey
# 2. Set the GEMINI_API_KEY environment variable
# 3. The system will automatically research missing policy paths
# 4. Generated PowerShell scripts will include actual implementation details

# Fallback Behavior:
# - If Gemini API is not available, system uses heuristic research
# - Basic PowerShell script generation is still functional
# - Pre-loaded policy database provides common CIS policy paths