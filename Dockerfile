# ----------- Build Stage -----------
FROM python:3.13-slim AS build

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --upgrade pip && pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Export requirements and install globally
RUN uv export --frozen --format requirements.txt -o requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# ----------- Production Stage -----------
FROM python:3.13-slim AS prod

WORKDIR /app

# Install runtime dependencies (if any system deps needed, add here)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy installed packages and app from build stage
COPY --from=build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /app /app

# Ensure /app is in PATH
ENV PATH="/app:$PATH"

# Run the bot
CMD ["python", "-m", "stockbot"]