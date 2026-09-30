# HemaNet frontend — local development image (Vite dev server).
# A production static build/serve stage is added with deployment work (E21).
FROM docker.io/library/node:22-alpine

WORKDIR /app
# Vite writes temp files next to its config, so the app dir belongs to the
# unprivileged `node` user that runs the server.
RUN chown node:node /app
USER node

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY --chown=node:node . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
