# 
import requests
import os
import json
# kt-api lib
from datetime import datetime
import hmac, hashlib
from pytz import timezone
from PIL import Image
# naver-api lib
import uuid
import time
#yolov8
from ultralytics import YOLO
# from django.core.exceptions import ImproperlyConfigured

def get_secret(setting, secrets_file):
    try:
        with open(secret_file) as f:
            secrets = json.loads(f.read())
        return secrets[setting]
    except KeyError:
        error_msg = "Set the {} environment variable".format(setting)

# pillow 사용 이미지 사이즈 조절 - 수정 요망
# ===============================================================
def img_size_pillow(img_path):
    image = Image.open(img_path)
    # print("Before :",image.size)  # 이미지의 크기 출력 (너비, 높이)
    if image.size[0] > image.size[1]:
        resized_image = image.resize((1440, 1440))
        resized_image.save(img_path)
    elif image.size[1] > image.size[0]:
        resized_image = image.resize((1440, 1440))
        resized_image.save(img_path)
    else:
        resized_image = image.resize((1440, 1440))
        resized_image.save(img_path)
# ===============================================================

def food_api(img_path,secret_file):
    # 음식 객체 탐지 위치 저장 리스트
    point_list = []
    # timestamp 생성
    timestamp = datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d%H%M%S%f")[:-3]
    # API키 분리
    # Django - setting.py에서 사용
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 
    client_id = get_secret("kt_client_id",secret_file)
    client_secret = get_secret("kt_client_secret",secret_file)

    # HMAC 기반 signature 생성
    signature = hmac.new(
        key=client_secret.encode("UTF-8"), msg= f"{client_id}:{timestamp}".encode("UTF-8"), digestmod=hashlib.sha256
    ).hexdigest()

    # api서버 연결 및 api 사용 준비
    url = "https://aiapi.genielabs.ai/kt/vision/food"
    client_key = get_secret("kt_client_key",secret_file)
    signature = signature
    timestamp = timestamp

    headers = {
        "Accept": "*/*",
        "x-client-key": client_key,
        "x-client-signature": signature,
        "x-auth-timestamp": timestamp
    }

    fields = {
        "flag": "ALL" # or "UNSELECTED" or "CALORIE" or "NATRIUM"
    }
    # 이미지 사이즈 조절 and 전처리 코드 구간 - 함수 제작
    #------------------------------------------------
    img_size_pillow(img_path)
    #------------------------------------------------

    img = open(img_path, "rb")

    obj =  {'metadata': json.dumps(fields), 'media': img} # or "false"

    response = requests.post(url, headers=headers, files=obj)

    if response.ok:
        json_data = json.loads(response.text)
        code = json_data['code']
        data = json_data['data']
        print(f"Code: {code}")
        #.json 형식 출력
        # print(f"Data: {data}")
        for region_num in data[0]:
            # BP.ipynb 파일 확인하여 .json 으로 전송하는 코드 필요
            #----------------------------------------------------
            print(data[0][region_num]['prediction_top1']) # 수정 요망
            #----------------------------------------------------
    else:
        # BP.ipynb 파일 확인하여 서버통신 코드 확인 하는 코드 필요
        #------------------------------------------------------------
        print(f"Error: {response.status_code} - {response.text}") # 수정 요망
        #------------------------------------------------------------
        
    # yolov 학습 모델
    # ===========================================================================
    print('====='*10)

    model = YOLO("../BP/BP_OB_Model/runs/detect/train2/weights/best.pt")
    result = model.predict(img_path)
    boxes = result[0].boxes
    if len(boxes.conf) > 0:
        # 신뢰도가 가장 높은 객체를 찾음
        max_conf_index = boxes.conf.argmax()
        highest_confidence = boxes.conf[max_conf_index].item()
        class_id = boxes.cls[max_conf_index].item()

        # 클래스 ID를 사용하여 음식 이름 찾기
        food_name = result[0].names[class_id]

        print(f"가장 높은 신뢰도를 가진 음식: {food_name}, 신뢰도: {highest_confidence:.2f}")
    else:
        print("탐지된 객체가 없습니다.")
    # =============================================================================

def OCR_api(img_path,secret_file):
    api_url = get_secret('CLOVA_OCR_Invoke_URL',secret_file)
    secret_key = get_secret('naver_secret_key',secret_file)

    request_json = {
        'images': [
            {
                'format': 'jpg',
                'name': 'demo'
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
    ('file', open(img_path,'rb'))
    ]
    headers = {
    'X-OCR-SECRET': secret_key
    }

    response = requests.request("POST", api_url, headers=headers, data = payload, files = files)

    # print(response.text.encode('utf8'))

    result = response.json()
    #
    return result

# 나중에 이미지 위치나 받아온 이미지 링크로 변경해야함
# ====================================================
BASE_DIR = "../BP/BP_Api_File/"
img_path = '/data/BP/BP_OB_Model/img/구이/갈비구이/Img_000_0021.jpg'
# img_path = os.path.join(BASE_DIR,"test_img/img_test_last1.jpg")
# ====================================================
# API키 연결 .json 파일
# =====================================================
secret_file = os.path.join(BASE_DIR, 'secrets.json')
# ====================================================
    
result = OCR_api(img_path=img_path,secret_file=secret_file)

if result['images'][0]['inferResult'] == 'ERROR':
    print("OCR_result :",result['images'][0]['inferResult'])
    food_api(img_path=img_path,secret_file=secret_file)
else:
    text = ""
    #Traceback (most recent call last):
    #File "/data/BP/BP_Api_File/Food_OD.py", line 174, in <module>
    #for field in result['images'][0]['receipt']['result']['subResults'][0]['items']:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
    #IndexError: list index out of range
    #음식 이미지에 있는 글자는 len(result['images'][0]['receipt']['result']['subResults']) <= 0 로 판단 하면 될 듯
    for field in result['images'][0]['receipt']['result']['subResults'][0]['items']:
        text += field['name']['text']
    print(text)