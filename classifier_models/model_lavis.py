from PIL import Image
from lavis.models import load_model_and_preprocess
from lavis.processors.blip_processors import BlipCaptionProcessor
import torch
import en_core_web_sm
nlp = en_core_web_sm.load()
from fastapi import FastAPI, File, UploadFile
import io

class_names = [
    # "buildings": [
        "trafficlight", 'skyscrapers', 'houses', 'bridges', 'stadiums', 'museums', 'churches', 'schools', 'airports', 'shopping_malls', 'factories',
        # ],
    
    # "food": [
        "banana", "apple", "sandwich", "orange", "carrot", "hotdog", "pizza", "cake", "wineglass", "cup", "knife", "spoon", "bowl", "meat", "egg",
    # ],
    
    # "human": [
        "people", "man", "boy", "girl", "woman", "crowd", "child",
            #   ],
    
    # "nature": [
        'forests', 'mountains', 'beaches', 'deserts', 'rivers', 'lakes', 'waterfalls', 'islands', 'grassland'
            #    ],

    # "animals" : [
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
        # ],
    
    # "tech": [
        "laptop", "mouse", "remote", "keyboard", "cellphone", "book", "television", "clock",
        # ],
    
    # "vehicles": 
        "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "skateboard", "surfboard"
]



# setup device to use
device = torch.device("cpu")

# Class definitions for the models

class ImageClassificationModel(object):
    '''
        The blackbox image classification model (LAVIS).
        Given an image path, it generates the required number of top classes.
    '''

    def __init__(self):
        self.model, self.vis_processors, _ = load_model_and_preprocess(
            "blip_feature_extractor", model_type="base", is_eval=True, device=device)
        self.cls_names = class_names
        self.text_processor = BlipCaptionProcessor(prompt="A picture of ")
        self.cls_prompt = [self.text_processor(
            cls_nm) for cls_nm in self.cls_names]
        self.app = FastAPI(title="Image Classification API")
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.post("/predict_img")
        async def predict(file: UploadFile = File(...)):
            content = await file.read()
            return await self.analyze_image(content)
        
    async def analyze_image(self, image_bytes: bytes):
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image = self.vis_processors["eval"](image).unsqueeze(0).to(device)
        sample = {"image": image, "text_input": self.cls_prompt}
        image_features = self.model.extract_features(
            sample, mode="image").image_embeds_proj[:, 0]
        text_features = self.model.extract_features(
            sample, mode="text").text_embeds_proj[:, 0]
        sims = (image_features @ text_features.t())[0] / self.model.temp
        probs = torch.nn.Softmax(dim=0)(sims).tolist()
        res = []
        for i in range(0, len(self.cls_names)):
            res.append((probs[i], self.cls_names[i]))  
        res = sorted(res, reverse=True)
        return {"Top 5 predicted classes": res[0:5]}
    
    def serve_model(self, host, port):
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
    
