FROM node:18-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

FROM base AS dependencies
RUN npm ci

FROM base AS build
COPY --from=dependencies /app/node_modules ./node_modules
COPY src ./src
COPY tsconfig.json ./
RUN npm run build

FROM base AS run
COPY --from=build /app/build ./build
COPY --from=dependencies /app/node_modules ./node_modules
ENTRYPOINT [ "npm", "start" ]