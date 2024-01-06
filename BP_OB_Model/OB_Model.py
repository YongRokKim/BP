from ultralytics import YOLO

model = YOLO('yolov8m.pt')
model.to('cuda')

model.train(data='../BP_OB_Model/Food_OD.yaml', epochs=100, patience=30, batch=32, imgsz=416)
