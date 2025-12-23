FROM node:18-alpine

WORKDIR /app

# Run as non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy package files
COPY --chown=nodejs:nodejs package*.json ./

# Install dependencies
RUN npm install --production

# Copy application code
COPY --chown=nodejs:nodejs server.js ./

# Expose ports
EXPOSE 3000 3001

# Switch to non-root user
USER nodejs

# Start server
CMD ["node", "server.js"]
