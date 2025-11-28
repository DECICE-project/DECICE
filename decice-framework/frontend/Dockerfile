# Use the official Node.js image as the base
FROM node:18-slim

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application files
COPY . .

# Expose the port that Vite runs on (default 5173 for dev server)
EXPOSE 5173

# Run the Vite app with the host flag
CMD ["npm", "run", "dev", "--", "--host"]
