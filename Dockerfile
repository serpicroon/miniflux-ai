FROM python:3.11-alpine AS builder
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --prefix="/deps" -r requirements.txt

FROM python:3.11-alpine
LABEL authors="serpicroon"
WORKDIR /app
RUN apk add --no-cache libxml2 libxslt
COPY --from=builder /deps /usr/local
COPY . .
CMD [ "python3","-u","main.py" ]