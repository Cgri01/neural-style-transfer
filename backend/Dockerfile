FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p models && \
    wget -q -O models/Starry_Night_512.pth "https://huggingface.co/cgri/nst-models/resolve/main/Starry_Night_512.pth" && \
    wget -q -O models/candy.pth "https://huggingface.co/cgri/nst-models/resolve/main/candy.pth" && \
    wget -q -O models/mosaic.pth "https://huggingface.co/cgri/nst-models/resolve/main/mosaic.pth" && \
    wget -q -O models/rain_princess.pth "https://huggingface.co/cgri/nst-models/resolve/main/rain_princess.pth" && \
    wget -q -O models/udnie.pth "https://huggingface.co/cgri/nst-models/resolve/main/udnie.pth"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]