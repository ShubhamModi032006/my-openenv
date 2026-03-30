FROM python:3.10-slim

# Set up a new user named "user" with ID 1000 (Required by Hugging Face)
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy everything giving owner permissions to our new user
COPY --chown=user . $HOME/app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
