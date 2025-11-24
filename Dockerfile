FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Default port for many hosting platforms; can be overridden by env.
ENV PORT=8080

EXPOSE ${PORT}

# Run Streamlit
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0"]
