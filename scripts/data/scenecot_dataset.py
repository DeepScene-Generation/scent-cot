"""Script to prepare code datasets for training and testing.

This script processes code problem datasets into a standardized format for training
and testing models. It loads problems from various code datasets (APPS, CodeForces,
LiveCodeBench etc.), adds appropriate instruction prompts, and saves the processed
data as parquet files.
"""
import argparse
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import json 

from rllm.data.dataset_types import TestDataset, TrainDataset
from rllm.data.utils import load_dataset

def make_map_fn(split: str):
    """Create a mapping function to process dataset examples.

    Args:
        split: Dataset split name ('train' or 'test')

    Returns:
        Function that processes individual dataset examples
    """
    def process_fn(example: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
        question = example["input"]
        instruction = "You FIRST think about the reasoning process as an internal monologue and then provide the final answer. The reasoning process MUST BE enclosed within <think> </think> tags. The final answer MUST BE put in <answer> </answer>."
        
        question = f"{question} {instruction}"

        reason = example["reason"]
        
        answer = example["answer"]

        filter_positions = ['west_wall', 'east_wall', 'north_wall', 'south_wall', 'middle of the room', 'ceiling']
        final_answer = list(filter(
            lambda x: x['new_object_id'] not in filter_positions,
            answer
        ))
        
        final_answer = json.dumps(final_answer, ensure_ascii=False)
        


        data = {
            "prompt": [{
                "role": "user",
                "content": question
            }],
            "ability": "scene_generation",
            "reward_model": {
                "style": "rule",
                "ground_truth": f"<think>{reason}</think>\n<answer>{final_answer}</answer>"
            },
            "extra_info": {
                'split': split,
                'index': idx,
            }
        }
        
        return data
    
    return process_fn

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process SCENECOT dataset')
    parser.add_argument('--local_dir', default=os.path.expanduser('/wuhu_uni_ai/limingsheng/rllm/rllm/data'),
                       help='Local directory to save processed datasets')
    args = parser.parse_args()

    local_dir = args.local_dir
    print(f"Local_dir:{local_dir}")
    
    # Load train and test data
    train_data = load_dataset(TrainDataset.Scene.SCENECOT)
    test_data = load_dataset(TestDataset.Scene.SCENECOT)
    
    # Process training data
    print(f"Train dataset: {len(train_data)} examples")
    train_dataset = []
    process_fn = make_map_fn('train')
    
    for idx, example in enumerate(train_data):
        processed_example = process_fn(example, idx)
        if processed_example is not None:
            train_dataset.append(processed_example)
    

    # Save training data
    train_df = pd.DataFrame.from_records(train_dataset)
    train_df.to_parquet(os.path.join(local_dir, 'train_scenecot.parquet'))

    # Process test data
    print(f"Test dataset: {len(test_data)} examples")
    test_dataset = []
    process_fn = make_map_fn('test')
    
    for idx, example in enumerate(test_data):
        processed_example = process_fn(example, idx)
        if processed_example is not None:
            test_dataset.append(processed_example)
    
    # Save test data
    test_df = pd.DataFrame.from_records(test_dataset)
    test_df.to_parquet(os.path.join(local_dir, 'test_scenecot.parquet'))
