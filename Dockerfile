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
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir /.paddleocr && chmod -R 777 /.paddleocr
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appgroup /app /.paddleocr


USER appuser


# Make port 80 available to the world outside this container
EXPOSE 7860

# Run the FastAPI app with uvicorn
CMD ["python", "app.py"]
