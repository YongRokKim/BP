from ultralytics import YOLO

model = YOLO('yolov8m.pt')
model.to('cuda')

import mlflow
import re,os
# Databricks MLflow 추적 서버 URI 설정
databricks_uri = "databricks"  # Databricks 워크스페이스의 MLflow URI
# mlflow.set_tracking_uri(databricks_uri)
os.environ['MLFLOW_TRACKING_URI'] = databricks_uri
# # Set the experiment path
mlflow.set_experiment("/Users/20182562@oasis.inje.ac.kr/Yolov")

def on_fit_epoch_end(trainer):
    if mlflow:
        metrics_dict = {f"{re.sub('[()]', '', k)}": float(v) for k, v in trainer.metrics.items()}
        mlflow.log_metrics(metrics=metrics_dict, step=trainer.epoch)

# 실험 세션 생성
try: 
     with mlflow.start_run():
          model.add_callback("on_fit_epoch_end",on_fit_epoch_end)
          result = model.train(data='../BP_OB_Model/Food_OD.yaml', epochs=100, patience=30, batch=32, imgsz=416)
          mlflow.pytorch.log_model(result.model, "model")
	
except mlflow.exceptions.MlflowException as e:
    print(f"An Mlflow error occurred: {str(e)}")