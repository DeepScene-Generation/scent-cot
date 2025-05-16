"""Script to prepare code datasets for training and testing.

This script processes code problem datasets into a standardized format for training
and testing models. It loads problems from various code datasets (APPS, CodeForces,
LiveCodeBench etc.), adds appropriate instruction prompts, and saves the processed
data as parquet files.
"""
import argparse
import json
import os
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import json 
import enum

class TrainDataset:
    class Scene(enum.Enum):
        SCENECOT = "SCENECOT"



def load_dataset(dataset_enum: Union[TrainDataset.Scene]) -> List[Dict[str, Any]]:
    """
    加载数据集，从指定路径读取json文件并处理数据。

    Args:
        dataset_enum: 数据集枚举类型，用于确定数据集路径

    Returns:
        List[Dict[str, Any]]: 数据项列表，每个数据项格式为：
        {
            "input": "用户输入内容",
            "reason": None,
            "answer": None
        }
    """
    # 定义数据列表
    data = []
    
    # 读取json文件
    json_path = "/wuhu_uni_ai/limingsheng/rllm/data_rl/train/scenecot.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 遍历json数据
    for item in json_data:
        # 获取user_input的内容
        input_data = item.get("user_input", "")
        
        # 添加到数据列表
        data.append({
            "input": input_data,
            "reason": None,
            "answer": None
        })
    
    return data



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

        


        data = {
            "prompt": [{
                "role": "user",
                "content": question
            }],
            "ability": "scene_generation",
            "reward_model": {
                "style": "rule",
                "ground_truth": None
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
    # test_data = load_dataset(TestDataset.Scene.SCENECOT)
    
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
    train_df.to_parquet(os.path.join(local_dir, 'train_scenecot_rl.parquet'))

    # # Process test data
    # print(f"Test dataset: {len(test_data)} examples")
    # test_dataset = []
    # process_fn = make_map_fn('test')
    
    # for idx, example in enumerate(test_data):
    #     processed_example = process_fn(example, idx)
    #     if processed_example is not None:
    #         test_dataset.append(processed_example)
    
    # # Save test data
    # test_df = pd.DataFrame.from_records(test_dataset)
    # test_df.to_parquet(os.path.join(local_dir, 'test_scenecot.parquet'))
