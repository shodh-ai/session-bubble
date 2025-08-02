#!/bin/bash

# Aurora Agent Docker Runner with Environment Variables
# Make sure to set your actual Google OAuth credentials

docker run -it \
  -p 8000:8000 \
  -p 6901:6901 \
  -p 8765:8765 \
  -e GOOGLE_CLIENT_ID="your_google_client_id_here" \
  -e GOOGLE_CLIENT_SECRET="your_google_client_secret_here" \
  --rm \
  session-bubble:1.2
