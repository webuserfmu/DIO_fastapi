# Usa uma imagem base Python
FROM python:3.9-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de dependências e instala-as
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que o FastAPI vai rodar
EXPOSE 8000

# Comando para iniciar a aplicação (será sobrescrito pelo docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]