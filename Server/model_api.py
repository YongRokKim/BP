import io
import json
from flask import Flask, request
from flask import make_response
from PIL import Image
from ultralytics import YOLO
import requests
import os
# kt-api lib
from datetime import datetime
import hmac, hashlib
from pytz import timezone
# naver-api lib
import uuid
import time
# json-image-decodeing
import base64

app = Flask(__name__)

def get_secret(setting, secret_file):
    try:
        with open(secret_file) as f:
            secrets = json.loads(f.read())
        return secrets[setting]
    except KeyError:
        print("Set the {} environment variable".format(setting))

# pillow 사용 이미지 사이즈 조절
def img_resize(img):
    try:
        # 이미지를 열고 크기 가져오기
        with Image.open(io.BytesIO(img)) as img:
            width, height = img.size
            print("@hello14 :", width, height)

            # 최소 및 최대 크기 정의
            minWidth, maxWidth = (720, 2560) if width > height else (720, 1440)
            minHeight, maxHeight = (1080, 1440) if width > height else (1080, 2560)
            print("@hello14 :", minWidth, minHeight, maxWidth, maxHeight)

            if minWidth <= width <= maxWidth and minHeight <= height <= maxHeight:
                print("Image meets size requirements. No resizing needed.")
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                return img_byte_arr.getvalue()

            # 이미지 크기 조정
            newWidth, newHeight = width, height
            if width < minWidth or height < minHeight:
                # 이미지 확대
                if width / height > 1:
                    # 넓은 이미지
                    newHeight = max(height, minHeight)
                    newWidth = round(newHeight * (width / height))
                    if newWidth < minWidth:
                        newWidth = minWidth
                        newHeight = round(newWidth / (width / height))
                else:
                    # 높은 이미지
                    newWidth = max(width, minWidth)
                    newHeight = round(newWidth / (width / height))
                    if newHeight < minHeight:
                        newHeight = minHeight
                        newWidth = round(newHeight * (width / height))
            elif width > maxWidth or height > maxHeight:
                # 이미지 축소
                if width / height > 1:
                    # 넓은 이미지
                    newWidth = min(width, maxWidth)
                    newHeight = round(newWidth / (width / height))
                    if newHeight > maxHeight:
                        newHeight = maxHeight
                        newWidth = round(newHeight * (width / height))
                else:
                    # 높은 이미지
                    newHeight = min(height, maxHeight)
                    newWidth = round(newHeight / (width / height))
                    if newWidth > maxWidth:
                        newWidth = maxWidth
                        newHeight = round(newWidth / (width / height))

            # 조정된 크기 출력 및 이미지 크기 조정
            print("@hello15 : Resized Image Size:", newWidth, newHeight)
            resized_img = img.resize((newWidth, newHeight))
            img_byte_arr = io.BytesIO()
            resized_img.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
    except Exception as error:
        print("Error resizing image:", error)
        return None

def food_api(img,secret_file):
    # timestamp 생성
    timestamp = datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d%H%M%S%f")[:-3]
 
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
    
    img_file = io.BytesIO(img)
    print("@hello8",img_file)
    obj =  {'metadata': json.dumps(fields), 'media': img_file}

    response = requests.post(url, headers=headers, files=obj)

    if response.ok:
        json_data = json.loads(response.text)
        print("@hello13 :",json_data)
        # code = json_data['code']
        data = json_data['data']
        # print(f"Code: {code}")
        return data
        #.json 형식 출력
        # print(f"Data: {data}")
        # for region_num in data[0]:
        #     # BP.ipynb 파일 확인하여 .json 으로 전송하는 코드 필요
        #     #----------------------------------------------------
        #     return data[0][region_num]['prediction_top1'] # 수정 요망
        #     #----------------------------------------------------
    else:
        # BP.ipynb 파일 확인하여 서버통신 코드 확인 하는 코드 필요
        #------------------------------------------------------------
        print(f"Error: {response.status_code} - {response.text}") # 수정 요망
        #------------------------------------------------------------
        
def OCR_api(img,secret_file):
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

    img_file = {'file': ('image.jpg', io.BytesIO(img), 'image/jpeg')}
    
    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
    ('file', img)
    ]
    headers = {
    'X-OCR-SECRET': secret_key
    }

    response = requests.request("POST", api_url, headers=headers, data = payload, files = img_file)
    result = response.json()
    return result

def get_prediction(img):
    img = Image.open(io.BytesIO(img))
    result = model.predict(img)
    boxes = result[0].boxes
    pred_list = {}
    if len(boxes.conf) > 0:
        for index,box in enumerate(boxes):
            # 신뢰도가 가장 높은 객체를 찾음
            max_conf_index = box.conf.argmax()
            highest_confidence = box.conf[max_conf_index].item()
            class_id = box.cls[max_conf_index].item()

            # 클래스 ID를 사용하여 음식 이름 찾기
            food_name = result[0].names[class_id]
            pred_list[f'item{index}']={"Food_name" : food_name,
                                     "highest_confidence":highest_confidence}
            return pred_list       
    else:
        print("탐지된 객체가 없습니다.")
    return pred_list
    
model = YOLO("../weights/yolov8m_train.pt")

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        file = request.files['food_image']
        print("files-type",file)
        img = file.read()
        res = {
            # 0 : OCR , 1 : KT & OD
            "inferResult": 0,
            # mealType 
            "mealType" : "",
            # image beatmap
            #dayTime send
            "dayTime" : "",
            # predict Result
            "predict": {
                # predict food name
                "foodNames": [],
                # kt predict food info
                "ktFoodsInfo": {} 
            },
            # "image":[file]
        }
        
        # API키 연결 .json 파일
        # =====================================================
        secret_file = "secrets.json"
        # ====================================================
        print("@hello2")
        try:
            print("@helloimg",type(img))
            resized_img = img_resize(img)
            ocr_result = OCR_api(img, secret_file)
            print("@hello10 :",ocr_result)
            print("@hello3")
            if ocr_result['images'][0]['inferResult'] == 'ERROR':
                print("@hello6",ocr_result['images'][0]['inferResult'] )
                print('@hello7')
                food_result = food_api(resized_img, secret_file)
                od_result = get_prediction(img)
                print('+++'*20)
                print(food_result)
                print("+++"*20)
                print(od_result)
                print('+++'*20)
                res['inferResult'] = 1
                # print("@hello3")
                # print("="*20)
                # print(food_result)
                # print("="*20)
                for region_num in food_result[0]:
                    # res['predict']['ktFoodsInfo'][region_num] = food_result[0][region_num]['prediction_top1']
                    # res['predict']['foodNames'].append(food_result[0][region_num]['prediction_top1']["food_name"])
                    if food_result[0][region_num]['prediction_top1']['confidence'] >=0.3:
                        res['predict']['ktFoodsInfo'][region_num] = food_result[0][region_num]['prediction_top1']
                        res['predict']['foodNames'].append(food_result[0][region_num]['prediction_top1']["food_name"])

                for item in od_result:
                    # res['predict']['foodNames'].append(od_result[item]['Food_name'])
                    if od_result[item]['highest_confidence'] >=0.5:
                        if od_result[item]['Food_name'] not in res['predict']['foodNames']:
                            res['predict']['foodNames'].append(od_result[item]['Food_name'])
            else:
                # print('@hello4')
                if ocr_result['images'][0]['receipt']['result']['subResults']:
                    for field in ocr_result['images'][0]['receipt']['result']['subResults'][0]['items']:
                        if field['name']['text'] not in res['predict']['foodNames']:
                            res['predict']['foodNames'].append(field['name']['text'])

            with open(f"../result.json", 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=4)

            print("JSON file has been saved.")
        except Exception as error:
            print("Error:", error)
            
        # 주의!! #
        # jsonify를 사용하면 json.dump()와 똑같이 ascii 인코딩을 사용하기 때문에 한글 깨짐
        # return jsonify({'class_id': class_id, 'class_name': class_name})
        
        print(res)
        res = make_response(json.dumps(res, ensure_ascii=False))
        res.headers['Content-Type'] = 'application/json'
        return res
    
if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True)
