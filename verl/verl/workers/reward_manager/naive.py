# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, Any

from verl import DataProto
from verl.utils.reward_score import _default_compute_score
import torch
from render_utils.retrieve import Retrieval

class NaiveRewardManager:
    """The reward manager.
    """

    def __init__(self, tokenizer, num_examine, compute_score=None) -> None:
        self.tokenizer = tokenizer
        self.num_examine = num_examine  # the number of batches of decoded responses to print to the console
        self.retrieval = Retrieval()
        
        self.compute_score = compute_score or _default_compute_score
        

    def __call__(self, data: DataProto):
        """We will expand this function gradually based on the available datasets"""

        # If there is rm score, we directly return rm score. Otherwise, we compute via rm_score_fn
        if 'rm_scores' in data.batch.keys():
            return data.batch['rm_scores']

        reward_tensor = torch.zeros_like(data.batch['responses'], dtype=torch.float32)

        already_print_data_sources = {}

        # Thread-safe dict for tracking printed data sources
        print_lock = threading.Lock()

        def process_row(args):
            i, data_item, already_print_data_sources = args

            prompt_ids = data_item.batch['prompts']

            prompt_length = prompt_ids.shape[-1]
            
            valid_prompt_length = data_item.batch['attention_mask'][:prompt_length].sum()
            valid_prompt_ids = prompt_ids[-valid_prompt_length:]

            response_ids = data_item.batch['responses'] 
            valid_response_length = data_item.batch['attention_mask'][prompt_length:].sum()
            
            valid_response_ids = response_ids[:valid_response_length]

            # decode
            prompt_str = self.tokenizer.decode(valid_prompt_ids, skip_special_tokens=True)
            response_str = self.tokenizer.decode(valid_response_ids, skip_special_tokens=True)

            # sequences = torch.cat((valid_prompt_ids, valid_response_ids))
            # sequences_str = self.tokenizer.decode(sequences, skip_special_tokens=True)

            
            
            # select rm_score
            data_source = data_item.non_tensor_batch['data_source']
            # data_source = data_item.non_tensor_batch['data_source'] if 'data_source' in data_item.non_tensor_batch.keys() else 'scene_cot'
            
            extra_info = data_item.non_tensor_batch.get('extra_info', None)

            
            
            
            score = self.compute_score(
                data_source=data_source,
                solution_str=response_str,
                extra_info=extra_info,
                retrieval=self.retrieval
            )
            
            with print_lock:
                if data_source not in already_print_data_sources:
                    already_print_data_sources[data_source] = 0

                if already_print_data_sources[data_source] < self.num_examine:
                    already_print_data_sources[data_source] += 1
                    print("--------------------------------")
                    print("prompt", prompt_str)
                    print("response", response_str)
                    print("score", score)
                    print("--------------------------------")
                    
            return i, score, valid_response_length

        # Process items in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            args = [(i, data[i], already_print_data_sources) for i in range(len(data))]
            results = list(executor.map(process_row, args))

        # Fill reward tensor with results
        for i, score, valid_response_length in results:
            reward_tensor[i, valid_response_length - 1] = score

        return reward_tensor
