# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update \
  && apt-get install -y --no-install-recommends --no-install-suggests \
  && pip3 install --no-cache-dir --upgrade pip
RUN apt-get install libgomp1
RUN python -m pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install https://huggingface.co/Ntchinda-Giscard/en_pipeline/resolve/main/en_pipeline-any-py3-none-any.whl
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# Create the directory where PaddleOCR wants to write
# RUN mkdir /.paddleocr /app/uploads /app/license && chmod -R 777 /.paddleocr /app/uploads /app/license
# Create the necessary directories and set permissions
RUN mkdir -p /.paddleocr /app/uploads /app/license && chmod -R 777 /.paddleocr /app/uploads /app/license

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Change ownership of the application directory and the newly created directories
RUN chown -R appuser:appgroup /app

# Switch to the new user
USER appuser

COPY . .


# Make port 80 available to the world outside this container
EXPOSE 7860

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]