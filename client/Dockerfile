FROM node:alpine

WORKDIR /app

ENV PATH /app/node_modules/.bin:$PATH

# install app dependencies
COPY package.json ./
COPY package-lock.json ./

RUN npm install --silent -g && npx browserslist@latest --update-db

# add app
COPY public src ./

# start app
CMD ["npm", "start"]
