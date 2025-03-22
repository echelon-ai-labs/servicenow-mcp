FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install the package in development mode
RUN pip install -e .

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application using the provided CLI
CMD ["servicenow-mcp-sse", "--host=0.0.0.0", "--port=8080"] 