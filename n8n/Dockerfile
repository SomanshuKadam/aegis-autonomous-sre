FROM docker:29-cli AS docker-cli

FROM n8nio/n8n:latest

USER root
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
RUN npm install --global @openai/codex \
    && mkdir -p /home/node/.codex /opt/aegis/state \
    && chown -R node:node /home/node/.codex /opt/aegis
USER node
