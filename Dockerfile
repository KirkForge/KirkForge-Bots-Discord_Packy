# Gargoyle Packy V2.0.0 - Discord Bot
# Node.js Discord bot with Claude cognition integration
# For Python cognition microservice, see Dockerfile.cognition

FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code and data
COPY src/ ./src/
COPY data/lorebook/ ./data/lorebook/
COPY data/voice_profile/ ./data/voice_profile/

# Production environment
ENV NODE_ENV=production

# Bot is outbound-only to Discord API - no ports exposed
# Entry point runs the Discord bot
CMD ["node", "src/bot/index.js"]

# .dockerignore hints:
# - node_modules (installed fresh above)
# - .env files (use secrets management)
# - .git and .gitignore (unnecessary in image)
# - logs/ directory (use stdout/stderr)
# - data/pending_lore/ (work in progress, not needed in production)
# - All model weights and large binary files
