import io
from torchvision import models
import json
from flask import Flask, jsonify, request
from flask import make_response
import torchvision.transforms as transforms
from PIL import Image
from ultralytics import YOLO

app = Flask(__name__)
    

# 이미 학습된 가중치를 사용하기 위해 `pretrained` 에 `True` 값을 전달
model = YOLO("../weights/best.pt")

# 모델을 추론에만 사용할 것이므로, `eval` 모드로 변경

def get_prediction(img):
    result = model.predict(img)
    boxes = result[0].boxes
    pred_list = []
    if len(boxes.conf) > 0:
        for box in boxes:
            # 신뢰도가 가장 높은 객체를 찾음
            max_conf_index = box.conf.argmax()
            highest_confidence = box.conf[max_conf_index].item()
            class_id = box.cls[max_conf_index].item()

            # 클래스 ID를 사용하여 음식 이름 찾기
            food_name = result[0].names[class_id]
            pred_list.append([food_name,highest_confidence])
            print(f"가장 높은 신뢰도를 가진 음식: {food_name}, 신뢰도: {highest_confidence:.2f}")
            
    else:
        print("탐지된 객체가 없습니다.")
    return pred_list
    


@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        # 전달받은 request에서 이미지 데이터 받고 byte로 변환
        file = request.files['food_image']
        
        img = file.read()
        # 이미지를 PIL Image 객체로 변환
        img = Image.open(io.BytesIO(img))
        
        res = {}
        # 추론값 생성
        for index, pred in enumerate(get_prediction(img)):
            food_name, highest_confidence = pred
            res[f"item{index + 1}"] = {
                'Food_name': food_name,
                'highest_confidence': highest_confidence
            }
        
        # 주의!! #
        # jsonify를 사용하면 json.dump()와 똑같이 ascii 인코딩을 사용하기 때문에 한글 깨짐
        # return jsonify({'class_id': class_id, 'class_name': class_name})
        
        res = make_response(json.dumps(res, ensure_ascii=False))
        res.headers['Content-Type'] = 'application/json'
        
        return res
    
if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True)
