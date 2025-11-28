FROM harbor.gwdg.de/decice/decice-ai-scheduler-base:py3.12

ENV PYTHONUNBUFFERED=1 \
    SCHEDULER_HOST=0.0.0.0 \
    ENVIRONMENT="production" \
    PYTHONPATH="/usr/local/lib/python3.12/site-packages"

# Copy only the necessary files
COPY src/ /app/src/
WORKDIR /app/src

EXPOSE 8030

CMD ["python", "main.py"]
