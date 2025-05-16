"""Utility functions for loading and processing datasets."""

import json
import os
from typing import Any, Dict, List, Union

from rllm.data.dataset_types import TrainDataset, TestDataset

def load_dataset(dataset_enum: Union[TrainDataset.Scene, TestDataset.Scene]) -> List[Dict[str, Any]]:
    """
    Load dataset by reading txt, md and json files from all subdirectories.

    Args:
        dataset_enum: Dataset enumeration type used to determine dataset path

    Returns:
        List[Dict[str, Any]]: List of data items, each formatted as:
        {
            "content": "<input>txt content</input><think>md content</think><answer>json content</answer>",
            "folder_name": "subdirectory name"
        }
    """
    dataset_name = dataset_enum.value.lower()
    data_dir = 'train' if dataset_enum.__class__ in [TrainDataset.Scene] else 'test'
    
    # Build data directory path
    current_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(current_dir, data_dir, dataset_name)
    
    if not os.path.exists(data_dir_path):
        raise ValueError(f"Dataset directory not found: {data_dir_path}")

    data = []
    # Get all subdirectories
    subdirs = [d for d in os.listdir(data_dir_path) if os.path.isdir(os.path.join(data_dir_path, d))]
    
    for subdir in subdirs:
        subdir_path = os.path.join(data_dir_path, subdir)
        
        # Initialize file contents
        input_data = reason_data = ""
        answer_data = []
        
        
        # Read txt file
        txt_files = [f for f in os.listdir(subdir_path) if f.endswith('.txt')]
        if txt_files:
            with open(os.path.join(subdir_path, txt_files[0]), 'r', encoding='utf-8') as f:
                input_data = f.read().strip()
        
        # Read md file
        md_files = [f for f in os.listdir(subdir_path) if f.endswith('.md')]
        if md_files:
            with open(os.path.join(subdir_path, md_files[0]), 'r', encoding='utf-8') as f:
                reason_data = f.read().strip()
        
        # Read json file
        json_files = [f for f in os.listdir(subdir_path) if f.endswith('.json')]
        if json_files:
            with open(os.path.join(subdir_path, json_files[0]), 'r', encoding='utf-8') as f:
                json_content = json.load(f)
                
        
        structural_elements = {
            'ceiling', 'floor', 'south_wall', 'north_wall', 
            'west_wall', 'east_wall', 'middle of the room'
        }
        answer_data = [
            scene for scene in json_content 
            if scene.get("new_object_id") not in structural_elements
        ]

        
        
        # Format content only if at least one file exists
        if any([input_data, reason_data, answer_data]):
            data.append({
                "input": input_data,
                "reason": reason_data,
                "answer": answer_data
            })
    
    return data



if __name__ == '__main__':
    # Example usage
    scenecot_data = load_dataset(TrainDataset.Scene.SCENECOT)
    print(f"Loaded {len(scenecot_data)} Scenecot training problems")
    
    scenecot_data = load_dataset(TestDataset.Scene.SCENECOT) 
    print(f"Loaded {len(scenecot_data)} Scenecot test problems")