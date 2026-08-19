FROM node:20-bookworm-slim

WORKDIR /app

RUN find /etc/apt -type f \( -name '*.sources' -o -name 'sources.list' \) -exec sed -i \
    -e 's|http://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' \
    -e 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' {} + \
  && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-noto-cjk \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
  && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm ci --omit=dev

COPY src ./src

EXPOSE 8091
CMD ["npm", "start"]
