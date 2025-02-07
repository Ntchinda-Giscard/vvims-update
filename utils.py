import os
import uuid
from fastapi import File
from paddleocr import PaddleOCR
import spacy
from ultralytics import YOLO
from PIL import Image
import boto3
import time
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from colorthief import ColorThief
import logging

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
)


# Create a logger
logger = logging.getLogger(__name__)


load_dotenv()

ocr_model = PaddleOCR(lang='en')
nlp_ner = spacy.load("en_pipeline")
detector = YOLO('best.pt')
vehicle = YOLO('yolov8x.pt')

aws_access_key_id=os.getenv('AWS_ACCESS_KEY')
aws_secret_access_key = os.getenv('AWS_SECRET_KEY')
bucket_name='vvims'

# Function to upload a file to S3
def upload_to_s3(
        file_path, 
        bucket_name=bucket_name, 
        aws_access_key_id=aws_access_key_id, 
        aws_secret_access_key=aws_secret_access_key,
        region_name='eu-north-1'):
    # Create an S3 client
    s3 = boto3.client('s3', 
                      aws_access_key_id=aws_access_key_id,
                      aws_secret_access_key=aws_secret_access_key,
                      region_name=region_name)
    
    # Get the current timestamp
    timestamp = int(time.time())
    
    # Extract the file name from the file path
    file_name = file_path.split("/")[-1]
    
    # Concatenate the timestamp with the file name
    unique_file_name = f"{str(uuid.uuid4())}-{file_name}"

    print(f"[*] ---- File path ====> {file_path}")
    
    try:
        # Upload the file
        s3.upload_file(file_path, bucket_name, unique_file_name)
        
        # Construct the file URL
        file_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{unique_file_name}"
        
        return file_url
    
    except FileNotFoundError:
        print("The file was not found")
        return None
    
    except NoCredentialsError:
        print("Credentials not available")
        return None


def ner_recog(text:str) -> dict:
    """
        Extract entities from text using SpaCy and return them as JSON.

        Args:
        - text: The input text.

        Returns:
        - dict: A dictionary containing the extracted entities in JSON format.
    """
    # Load SpaCy model
    # Process the text
    doc = nlp_ner(text)

    # Extract entities and format them as JSON
    entities = [{ent.label_ : ent.text} for ent in doc.ents]

    return {"entities": entities}


def read_text_img(img_path:str) -> str:
    """
        Read text from images

        Args:
        - img_path: Path to the images in which the text will be extracted

        Returns:
        - text: The extracted text
    """

    result = ocr_model.ocr(img_path)
    text = ''
    if result[0]:
        for res in result[0]:
            text += res[1][0] + ' '
    return text
def detect_licensePlate(img: str) -> dict:
    image = Image.open(img)
    results = vehicle(source=img, cls=['car', 'bus', 'truck', 'motorcycle'], conf=0.7)
    names = vehicle.names
    classes=[]
    data=[]
    final = []

    print("Results from car detetctions,:", results)

    if len(results[0]) >= 1:
        
        for result in results:
            for c in result.boxes.cls.numpy():
                classes.append(names[int(c)])
            boxes = result.boxes.xyxy
            for box in boxes.numpy():
                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                cropped_image = image.crop((x1, y1, x2, y2))

                img_path = os.path.join('license', 'cars.jpg')
                cropped_image.save(img_path)
                num_plate = licence_dect(img_path)

                color_thief = ColorThief(img_path)
                dominant_color = color_thief.get_color(quality=1)
                data.append({"plate": num_plate, "color": dominant_color})
        for i in range(len(classes)):
            final.append({"type": classes[i], "info": data[i]})
    else:
        plate = licence_dect(img)
        color_thief = ColorThief(img)
        dominant_color = color_thief.get_color(quality=1)
        final = [
            {"type": "", "info": {"plate": plate, "color": dominant_color }}
        ]
    print(final)

    return final

    # if len(results > 1):
    #     for result in results:
    #         boxes = result.boxes.xyxy
    #         for box in boxes.numpy():
    #             x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
    #             cropped_image = image.crop((x1, y1, x2, y2))
    #             color = 




    return results


def licence_dect(img: str) -> list:
    image = Image.open(img)
    results = detector(img)
    names = detector.names
    color_thief = ColorThief(img)
    dominant_color = color_thief.get_color(quality=1)


    detections = []
    try:
        for result in results:
            boxes = result.boxes.xyxy
            for box in boxes.numpy():
                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
            # confidence = float(confidence)
                cropped_image = image.crop((x1, y1, x2, y2))

                cropped_image.save(os.path.join('license', 'carplate.jpg'))

                txt = read_text_img('license/carplate.jpg')

                detections.append(txt)
        
        return txt
    except Exception as e:
        pass


def lookup_user_metadata(index, encoder, serial):
    result = index.query(
        namespace="ns1",
        vector= encoder,
        top_k=2,
        include_values=True,
        include_metadata=True,
        filter={"serial": {"$eq": serial}}
    )
    result_data = {
        "matches": [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            }
            for match in result.matches
        ]
    }

    return result_data


def lookup_user(index, encoding_list):
    result = index.query(
            namespace="ns1",
            vector=encoding_list,
            top_k=1,
            include_metadata=True,
        )
    

        # Convert the QueryResponse to a serializable format
    result_data = {
        "matches": [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            }
            for match in result.matches
        ]
    }

    return result_data

def vehicle_dect(img: str) -> any:
    image = Image.open(img)

    results = vehicle(source=img, cls=['car', 'bus', 'truck', 'motorcycle'], conf=0.7)
    names = vehicle.names
    classes=[]
    colors = []
    final = []
    try:
        for result in results:
            boxes = result.boxes.xyxy
            logger.info(f"Classes {result.boxes.cls}")
            for c in result.boxes.cls.numpy():
                classes.append(names[int(c)])
            for box in boxes.numpy():
                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                cropped_image = image.crop((x1, y1, x2, y2))
                img_path = os.path.join('license', 'cars.jpg')
                cropped_image.save(img_path)

                num_plate = licence_dect(img_path)
                color_thief = ColorThief(img_path)
                dominant_color = color_thief.get_color(quality=1)
                colors = {"color": dominant_color, "plate": num_plate}
                logger.info("[*]---- Color detecttion : f{color}")

                logger.info("[*]---- Classes detecttion : f{classes}")
            
            # {'color': (70, 69, 74), 'plate': ['LT661HM CMR ']}
            # ['car', 'car']
            # {'color': (73, 82, 89), 'plate': []}
            # ['car', 'car']

        for i in range(len(classes)):
            final.append({ "type": classes[i], "car_data" : colors[i]})
        logger.info("[*]---- Final detecttion : f{final}")
        return final
    
    except Exception as e:
        # raise(e)
        pass

def write_to_upload( file, file_path, folder= "uploads"):
    path = os.path.join(folder, file_path)
    with open(path, "wb") as front_file:
        front_file.write( file.read())
    return path

# res = licence_dect("cars.jpg")
# print(res)

