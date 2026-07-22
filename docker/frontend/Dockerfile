# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY apps/frontend/ .
RUN npm ci
RUN npm run build

# Stage 2: Runtime
FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
