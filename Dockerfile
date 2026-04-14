FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Add HF-required non-root user (uid 1000)
RUN useradd -m -u 1000 user

# Set up virtual environment under user home
ENV UV_PROJECT_ENVIRONMENT=/home/user/venv
ENV PATH="/home/user/venv/bin:${PATH}"
ENV PYTHONPATH=/home/user/app/src

# Set working directory
WORKDIR /home/user/app

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv lock
RUN uv sync --frozen

# Copy rest of application
COPY src ./src

# Fix ownership before switching user
RUN chown -R user:user /home/user/app /home/user/venv

# Switch to non-root user
USER user

# Expose Gradio port
EXPOSE 7860

# Run application
CMD ["python", "src/prism/main.py"]
