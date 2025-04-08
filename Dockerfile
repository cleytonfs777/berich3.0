FROM python:3.9-slim-buster

# Instala as ferramentas de compilação e o Git
RUN apt-get update && \
    apt-get install -y gcc g++ make git && \
    apt-get clean

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os requisitos e instala as dependências
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf iqoptionapi && \
    git clone https://github.com/iqoptionapi/iqoptionapi.git && \
    cd iqoptionapi && \
    pip install .

# Copia o restante da aplicação
COPY . .

# Expõe uma porta (caso venha a ser usada no futuro, opcional)
EXPOSE 8000

# CMD padrão (pode ser sobrescrito no docker-compose)
CMD ["python", "bot.py"]
