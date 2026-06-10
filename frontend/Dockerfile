FROM node:22-slim AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

ENV PORT=8080
CMD ["sh", "-c", "sed -i \"s/listen 8080/listen ${PORT}/\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]

