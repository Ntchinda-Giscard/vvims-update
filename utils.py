import os
from paddleocr import PaddleOCR
import spacy
from ultralytics import YOLO
from PIL import Image
import boto3
import time
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from colorthief import ColorThief


load_dotenv()

ocr_model = PaddleOCR(lang='en')
nlp_ner = spacy.load("output/model-best")
detector = YOLO('best.pt')
vehicle = YOLO('yolov8x.pt')

aws_access_key_id=os.getenv('AWS_ACESS_KEY')
aws_secret_access_key = os.getenv('AWS_SECRET_KEY')
bucket_name='vvims'

# Function to upload a file to S3
def upload_to_s3(
        file_path, 
        bucket_name=bucket_name, 
        # aws_access_key_id=aws_access_key_id, 
        # aws_secret_access_key=aws_secret_access_key,
        region_name='eu-north-1'):
    # Create an S3 client
    s3 = boto3.client('s3', 
                    #   aws_access_key_id=aws_access_key_id,
                    #   aws_secret_access_key=aws_secret_access_key,
                      region_name=region_name)
    
    # Get the current timestamp
    timestamp = int(time.time())
    
    # Extract the file name from the file path
    file_name = file_path.split("/")[-1]
    
    # Concatenate the timestamp with the file name
    unique_file_name = f"{timestamp}_{file_name}"
    
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

def licence_dect(img: str) -> list:
    image = Image.open(img)
    results = detector(img)
    names = detector.names
    color_thief = ColorThief(img)
    dominant_color = color_thief.get_color(quality=1)


    detections = []
    for result in results:
        boxes = result.boxes.xyxy
        for box in boxes.numpy():
            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
        # confidence = float(confidence)
            cropped_image = image.crop((x1, y1, x2, y2))

            cropped_image.save(os.path.join('license', 'carplate.jpg'))

            txt = read_text_img('license/carplate.jpg')

            detections.append({"matricule":txt, "color" :dominant_color})
    
    return detections


def vehicle_dect(img: str) -> any:
    image = Image.open(img)

    results = vehicle(source=img, cls=['car', 'bus', 'truck', 'motorcycle'], conf=0.7)
    names = vehicle.names
    classes=[]
    colors = []
    final = []
    for result in results:
        boxes = result.boxes.xyxy
        print("Classes",result.boxes.cls)
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
            colors.append((dominant_color, num_plate))
    for i in range(len(classes)):
        final.append({ "type": classes[i], "color" : colors[i]})

    return final



res = licence_dect("cars.jpg")
print(res)

