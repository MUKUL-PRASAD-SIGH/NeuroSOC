FROM node:20-bullseye AS build

WORKDIR /app

COPY package*.json ./

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

# Alpine uses apk (THIS is where apk is correct)
RUN apk add --no-cache python3 make g++

RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
