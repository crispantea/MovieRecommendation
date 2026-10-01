# ref: https://hub.docker.com/_/node
FROM node:26-alpine3.23

WORKDIR /app

COPY . .

RUN npm install
RUN npm run build

EXPOSE 5173

CMD ["npm", "run", "start"]