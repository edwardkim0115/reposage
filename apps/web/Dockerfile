FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
COPY apps/web/package.json /app/apps/web/package.json
RUN npm install

COPY . /app

RUN npm run build --workspace @reposage/web

EXPOSE 3000

CMD ["npm", "run", "start", "--workspace", "@reposage/web"]

