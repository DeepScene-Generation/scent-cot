import json
import re, os
import networkx as nx


import torch

import transformers
import threading
import multiprocessing
import sys
import pandas as pd
from torch.nn import functional as F
import objaverse
import trimesh
import certifi
import ssl
import shutil
import argparse
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['SSL_CERT_FILE'] = certifi.where()

LOCALS_PATH = os.path.abspath(os.path.dirname(__file__))
DESIGNER_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))



def extract_list_from_json(input_json, key):
    if key in input_json and isinstance(input_json[key], list): 
        return input_json[key]
    return None

def get_room_priors(room_dimensions):
    x_mid = room_dimensions[0] / 2
    y_mid = room_dimensions[1] / 2
    z_mid = room_dimensions[2] / 2

    room_priors = [
        {"new_object_id": "south_wall", "itemType": "wall", "position": {"x": x_mid, "y": 0, "z": z_mid}, "size_in_meters": {"length": room_dimensions[0], "width": 0.0, "height": room_dimensions[2]}, "rotation": {"z_angle": 0.0}},
        {"new_object_id": "north_wall", "itemType": "wall", "position": {"x": x_mid, "y": room_dimensions[1], "z": z_mid}, "size_in_meters": {"length": room_dimensions[0], "width": 0.0, "height": room_dimensions[2]}, "rotation": {"z_angle": 180.0}},
        {"new_object_id": "east_wall", "itemType": "wall", "position": {"x": room_dimensions[0], "y": y_mid, "z": z_mid}, "size_in_meters": {"length": room_dimensions[1], "width": 0.0, "height": room_dimensions[2]}, "rotation": {"z_angle": 270.0}},
        {"new_object_id": "west_wall", "itemType": "wall", "position": {"x": 0, "y": y_mid, "z": z_mid}, "size_in_meters": {"length": room_dimensions[1], "width": 0.0, "height": room_dimensions[2]}, "rotation": {"z_angle": 90.0}},
        {"new_object_id": "middle of the room", "itemType": "floor", "position": {"x": x_mid, "y": y_mid, "z": 0}, "size_in_meters": {"length": room_dimensions[0], "width": room_dimensions[1], "height": 0.0}, "rotation": {"z_angle": 0.0}},
        {"new_object_id": "ceiling", "itemType": "ceiling", "position": {"x": x_mid, "y": y_mid, "z": room_dimensions[2]}, "size_in_meters": {"length": room_dimensions[0], "width": room_dimensions[1], "height": 0.0}, "rotation": {"z_angle": 0.0}}
    ]

    return room_priors

class Retrieval:
    def __init__(self, room_dimensions=[5.0, 5.0, 3.0]):
        
        self.room_dimensions = room_dimensions
        self.room_priors = get_room_priors(self.room_dimensions)


        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        meta = json.load(
            open('/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/embeddings/objaverse_meta.json')
        )
        self.meta = {x['u']: x for x in meta['entries']}

        deser = torch.load('/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/embeddings/objaverse.pt')
        self.us = deser['us']
        self.feats = deser['feats']

        local_assets = pd.read_excel("/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/assets/copy.xlsx", skiprows=2)
        captions = local_assets["caption_clip"].tolist()

        file_paths = []
        bbx_values = []
        for index, row in local_assets.iterrows():
            model_name = row['name_en']
            model_path = os.path.join("/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/assets/lvm_2032fbx", f"{model_name}.fbx")
            file_paths.append(model_path)
            bbx_values.append(row['bbx'])

        self.caption_to_file = [
            {
                "caption": caption,
                "file_path": path,
                "bbx": bbx
            }
            for caption, path, bbx in zip(captions, file_paths, bbx_values)
        ]

        self.clip_model, self.clip_prep = transformers.CLIPModel.from_pretrained(
            "/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/ckpts/CLIP-ViT-bigG-14-laion2B-39B-b160k",
            low_cpu_mem_usage=True, torch_dtype=torch.float16,
            offload_state_dict=True,
        ), transformers.CLIPProcessor.from_pretrained("/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/ckpts/CLIP-ViT-bigG-14-laion2B-39B-b160k")
        
        
        # # self.clip_model = self.clip_model.cpu()
        # self.clip_model = self.clip_model.to("cuda:7")
        # self.device = self.clip_model.device

        self.local_embeddings = torch.load("/wuhu_uni_ai/limingsheng/ckpt/MSheng-Lee/code/embeddings/local.pt")

    def retrieve_assets(self, answer_json, room_name):
        
        # with threading.Lock():
            
        self.clip_model = self.clip_model.cpu()
        
        torch.set_grad_enabled(False)
        
        def preprocess(input_string):
            wo_numericals = re.sub(r'\d', '', input_string)
            output = wo_numericals.replace("_", " ")
            return output

        def retrieve_local(query_embedding, top=1, sim_th=0.5):
            query_embedding = F.normalize(query_embedding.detach().cpu(), dim=-1).squeeze()
            sims = []
            for embedding in torch.split(self.local_embeddings, 10240):
                sims.append(query_embedding @ F.normalize(embedding.float(), dim=-1).T)
            sims = torch.cat(sims)
            sims, indices = torch.sort(sims, descending=True)
            results = []
            for i, sim in zip(indices, sims):
                if sim > sim_th:
                    results.append({
                        "caption": self.caption_to_file[i]["caption"],
                        "file_path": self.caption_to_file[i]["file_path"],
                        "bbx": self.caption_to_file[i]["bbx"],
                        "sim": sim.item()
                    })
                    if len(results) >= top:
                        break
            return results

        def retrieve(embedding, top=1, sim_th=0.1, filter_fn=None):
            sims = []
            embedding = F.normalize(embedding.detach().cpu(), dim=-1).squeeze()
            for chunk in torch.split(self.feats, 10240):
                sims.append(embedding @ F.normalize(chunk.float(), dim=-1).T)
            sims = torch.cat(sims)
            sims, idx = torch.sort(sims, descending=True)
            sim_mask = sims > sim_th
            sims = sims[sim_mask]
            idx = idx[sim_mask]
            results = []
            for i, sim in zip(idx, sims):
                if self.us[i] in self.meta:
                    if filter_fn is None or filter_fn(self.meta[self.us[i]]):
                        results.append(dict(self.meta[self.us[i]], sim=sim))
                        if len(results) >= top:
                            break
            return results

        def get_filter_fn():
            face_min = 0
            face_max = 34985808
            anim_min = 0
            anim_max = 563
            anim_n = not (anim_min > 0 or anim_max < 563)
            face_n = not (face_min > 0 or face_max < 34985808)
            filter_fn = lambda x: (
                (anim_n or anim_min <= x['anims'] <= anim_max)
                and (face_n or face_min <= x['faces'] <= face_max)
            )
            return filter_fn            

        def get_model_dimensions(file_path):
            mesh = trimesh.load(file_path)
            bounding_box = mesh.bounding_box.extents
            length = bounding_box[0] / 100
            width = bounding_box[2] / 100
            height = bounding_box[1] / 100
            return length, width, height

        # Extract objects from designer_response
        for obj in answer_json:
            new_object_id = obj.get('new_object_id', '')
            material = obj.get('material', '')
            style = obj.get('style', '')
            
            if not new_object_id:
                continue
            else:
                if material and style:
                    text = preprocess("A high-poly " + new_object_id + f" with {material} material and in {style} style, high quality")
                elif material:
                    text = preprocess("A high-poly " + new_object_id + f" with {material} material, high quality")
                elif style:             
                    text = preprocess("A high-poly " + new_object_id + f" in {style} style, high quality")
                else:
                    text = preprocess("A high-poly " + new_object_id)
            
            # 使用cuda:0设备
            tn = self.clip_prep(
                text=[text], return_tensors='pt', truncation=True, max_length=64
            ).to(self.clip_model.device)
            enc = self.clip_model.get_text_features(**tn).float()

            retrieved_local = retrieve_local(enc, top=1, sim_th=0.5)
            if retrieved_local:
                retrieved_obj = retrieved_local[0]
                print("Retrieved object: ", retrieved_obj["file_path"])

                destination_folder = os.path.join(DESIGNER_PATH, f"Assets/{room_name}")
                
                os.makedirs(destination_folder, exist_ok=True)
                source_file = retrieved_obj["file_path"]
                
                file_extension = os.path.splitext(source_file)[1]
                destination_path = os.path.join(destination_folder, f"{obj['new_object_id']}{file_extension}")
                shutil.copy(source_file, destination_path)
                print(f"File moved to {destination_path}")

                if retrieved_obj["sim"] > 0.5:
                    length, width, height = map(float, retrieved_obj["bbx"].split(','))
                    del obj['size_in_meters']
                    obj['size_in_meters'] = {'length': length, 'width': width, 'height': height}
            else:
                retrieved_obj = retrieve(enc, top=1, sim_th=0.1, filter_fn=get_filter_fn())[0]
                print(f"Retrieved object from Objaverse: {retrieved_obj['u']}")
                processes = multiprocessing.cpu_count()
                objaverse_objects = objaverse.load_objects(
                    uids=[retrieved_obj['u']],
                    download_processes=processes
                )
                destination_folder = os.path.join(DESIGNER_PATH, f"Assets/{room_name}")
                os.makedirs(destination_folder, exist_ok=True)
                for item_id, file_path in objaverse_objects.items():
                    destination_path = f"{destination_folder}{obj['new_object_id']}.glb"
                    shutil.move(file_path, destination_path)
                    print(f"File {item_id} moved from {file_path} to {destination_path}")

                    if retrieved_obj["sim"] > 0.18:
                        
                        length, width, height = get_model_dimensions(destination_path)
                        del obj['size_in_meters']
                        obj['size_in_meters'] = {'length': length, 'width': width, 'height': height}

        answer_json.extend(self.room_priors)
        with open(os.path.join(DESIGNER_PATH, f"Assets/{room_name}/answer_json.json"), "w") as f:
            json.dump(answer_json, f)
        return answer_json

        
if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Retrieve assets for a room')
    # parser.add_argument('--answer_json', type=str, required=True, help='Path to the answer JSON file')
    # parser.add_argument('--room_name', type=str, required=True, help='Name of the room')
    # args = parser.parse_args()

    retrieval = Retrieval()
    
    answer_json = json.load(open("/wuhu_uni_ai/limingsheng/rllm/Assets_old/room_99/answer_json.json", "r"))
    answer_json = retrieval.retrieve_assets(answer_json, "room_99")

    # from render import render_blender
    # render_blender(answer_json, "living_room")

    # os.system(f'python /wuhu_uni_ai/limingsheng/rllm/utils/render.py --answer_json {answer_json} --room_name "living_room"')
    
