FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
EXPOSE 5173
# Vite dev server bound to 0.0.0.0 so the browser on the host can reach it.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
