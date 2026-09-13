# ref: https://hub.docker.com/_/node
FROM node:26-alpine3.23

WORKDIR /app

# env variables (should be passed as arguments to this image)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# IMPORTANT: When building this image, the context should point to the frontend application directory
COPY . .

RUN npm install

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]