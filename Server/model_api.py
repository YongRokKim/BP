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
# ensemble lib
from ensemble_boxes import *
import torch
from collections import defaultdict

app = Flask(__name__)

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

def get_secret(setting):
    secret_file = "secrets.json"
    try:
        with open(secret_file) as f:
            secrets = json.loads(f.read())
        return secrets[setting]
    except KeyError:
        print("Set the {} environment variable".format(setting))

def food_api(img):
    point_list = []
    food_api_result = {}
    # timestamp 생성
    timestamp = datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d%H%M%S%f")[:-3]
    # API키 분리

    client_id = get_secret("kt_client_id")
    client_secret = get_secret("kt_client_secret")

    # HMAC 기반 signature 생성
    signature = hmac.new(
        key=client_secret.encode("UTF-8"), msg= f"{client_id}:{timestamp}".encode("UTF-8"), digestmod=hashlib.sha256
    ).hexdigest()


    url = "https://aiapi.genielabs.ai/kt/vision/food"
    client_key = get_secret("kt_client_key")
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

    print("--------------",type(img))
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
            print(data[0][region_num]['prediction_top1'])
            food_api_result[region_num] = data[0][region_num]['prediction_top1']
            for point in data[0][region_num]['position']:
                if point['location_type'] == 'LEFT_TOP':
                    left_top = (int(point['x'].split('.')[0]), int(point['y'].split('.')[0]))
                else:
                    right_bottom = (int(point['x'].split('.')[0]), int(point['y'].split('.')[0]))

            point_list.append([left_top[0],left_top[1],right_bottom[0],right_bottom[1],data[0][region_num]['prediction_top1']['food_name'],data[0][region_num]['prediction_top1']['confidence']])
        return [food_api_result,point_list]
    else:
        print(f"Error: {response.status_code} - {response.text}")
        
def OCR_api(img):
    api_url = get_secret('CLOVA_OCR_Invoke_URL')
    secret_key = get_secret('naver_secret_key')

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

def get_prediction_wbf(img, model_list):
    boxes_list = []
    scores_list = []
    labels_list = []

    resized_img = Image.open(io.BytesIO(img))
    # 초기 라벨 매핑 (이 예시에서는 비어있음)
    label_mapping = {}
    # kt 에서 찾은 음식이 이미 라벨링 되어 있을 경우를 상정
    key_mapping = {}

    img_width, img_height = resized_img.size
    food_api_result,point_list = food_api(img)  # Ensure food_api is correctly defined
    # Collect boxes, scores, and labels from each model
    for model in model_list:
        result = model.predict(resized_img)
        print("@hello-result",result)
        boxes = result[0].boxes
        print("@hello-2",boxes)
        if len(boxes.conf) > 0:
            print("@hello3")
            model_boxes = []
            model_scores = []
            model_labels = []
            print("@hello4",boxes)
            for i, box in enumerate(boxes.xyxy):
                print("@hello4")
                x_min, y_min, x_max, y_max = box
                conf = boxes.conf[i]
                cls_name = result[0].names[int(boxes.cls[i])]
                cls = int(boxes.cls[i])

                # 새로운 라벨을 매핑에 추가
                if cls_name not in label_mapping:
                    label_mapping[cls] = cls_name
                    key_mapping[cls_name] = cls

                model_boxes.append([x_min, y_min, x_max, y_max])
                model_scores.append(conf)
                model_labels.append(cls)
            
            boxes_list.append(model_boxes)
            scores_list.append(model_scores)
            labels_list.append(model_labels)
            print("@@@@ labels_list :",labels_list)

    # Add labels from point_list to the mapping
    additional_labels = 150  # Start number for labels added from food_api
    api_model_boxes = []
    api_model_scores = []
    api_model_labels = []
    for item in point_list:
        x_min, y_min, x_max, y_max, food_name, confidence = item
        if food_name not in key_mapping:
            label_mapping[additional_labels] = food_name
            api_model_labels.append(additional_labels)
            additional_labels += 1
        else:
            api_model_labels.append(key_mapping[food_name])
            additional_labels += 1
        # Add the box to the last model's list
        api_model_boxes.append([x_min, y_min, x_max, y_max])
        api_model_scores.append(confidence)
    boxes_list.append(api_model_boxes)
    scores_list.append(api_model_scores)
    labels_list.append(api_model_labels)
    print("@@@@ labels_list :",labels_list)

    # Normalize box coordinates and ensure consistency
    for i in range(len(boxes_list)):
        model_boxes = boxes_list[i]
        model_scores = scores_list[i]
        model_labels = labels_list[i]

        if len(model_boxes) != len(model_scores) or len(model_boxes) != len(model_labels):
            print(f"Error in model {i}: Length of boxes, scores, and labels do not match.")
            print(f"Boxes: {len(model_boxes)}, Scores: {len(model_scores)}, Labels: {len(model_labels)}")
            continue

        # Normalize boxes and move to CPU if necessary
        normalized_boxes = []
        for box in model_boxes:
            box = [b.cpu() if isinstance(b, torch.Tensor) else b for b in box]  # Move to CPU if tensor
            x_min, y_min, x_max, y_max = box
            normalized_boxes.append([x_min / img_width, y_min / img_height, x_max / img_width, y_max / img_height])
        boxes_list[i] = normalized_boxes

    # Apply Weighted Boxes Fusion
    try:
        pred_list = []
        _, wbf_scores, wbf_labels = weighted_boxes_fusion(
            boxes_list, scores_list, labels_list, iou_thr=0.55, skip_box_thr=0.20, conf_type='max'
        )
        for index, scores in enumerate(wbf_scores):
            if (scores >= 0.4) and (label_mapping[wbf_labels[index]] not in pred_list):
                pred_list.append(label_mapping[wbf_labels[index]])
        return [food_api_result,pred_list]
    except Exception as e:
        print("Error during Weighted Boxes Fusion:", e)


@app.route('/predict', methods=['POST'])
def predict():
    # json 전송 format
    if request.method == 'POST':
        file = request.files['food_image']
        print("@files-type",file)
        img = file.read()

        res = {
            # 0 : OCR , 1 : KT & OD
            "inferResult": 0,
            # mealType 
            "mealType" : "",
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
    # 학습 모델 리스트
    model_list = []
    model_weights=[
        "../weights/yolov8m_train.pt",
        "../weights/yolov5mu_train.pt"
        # "../BP_OB_Model/runs/detect/train9/weights/best.pt",
        # "../BP_OB_Model/runs/detect/train2/weights/best.pt",
        # "../BP_OB_Model/runs/detect/train13/weights/best.pt"
        ]
    
    for model_weight in model_weights:
        model_yolov = YOLO(model_weight)
        model_list.append(model_yolov)

        try:
            ocr_api_result = OCR_api(img)
            print("@hello-1",ocr_api_result)
            if (ocr_api_result['images'][0]['inferResult'] == 'ERROR') or (len(ocr_api_result['images'][0]['receipt']['result']['subResults']) == 0):
                resized_img = img_resize(img)
                food_api_result,od_result = get_prediction_wbf(resized_img,model_list=model_list)
                res['inferResult'] = 1
                res['predict']['ktFoodsInfo'] = food_api_result
                res['predict']['foodNames'] = od_result

            else:
                for field in ocr_api_result['images'][0]['receipt']['result']['subResults'][0]['items']:
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
        
        res = make_response(json.dumps(res, ensure_ascii=False))
        res.headers['Content-Type'] = 'application/json'
        
        return res
    
if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True)
