FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（ffmpeg + 音频库 + 中文字体，报告 PDF 必需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 下载 jieba 词典（首次启动会慢，提前下载）
RUN python -c "import jieba; jieba.initialize()"

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p uploads uploads/results

EXPOSE 8090

CMD ["python", "main.py"]
