# import pandas as pd
# from transformers import AutoTokenizer
# import torch

# # 首先读取 parquet 文件
# print("Reading parquet file...")
# df = pd.read_parquet('/wuhu_uni_ai/limingsheng/rllm/rllm/data/train_scenecot.parquet')

# # 加载tokenizer
# print("Loading tokenizer...")
# tokenizer = AutoTokenizer.from_pretrained('/wuhu_uni_ai/limingsheng/ckpt/Qwen/Qwen2.5-7B-Instruct', trust_remote_code=True)

# # 初始化最大token数和对应的reason
# max_tokens = 0
# max_reason = ""

# # 遍历每个元素并统计token数量
# print("Processing reasons...")
# for idx, row in df.iterrows():
#     reason = row['extra_info']['reason'] + row['reward_model']['ground_truth']
#     tokens = tokenizer(reason, return_tensors='pt')
#     token_count = tokens.input_ids.size(1)
    
#     if token_count > max_tokens:
#         max_tokens = token_count
#         max_reason = reason

# print(f"\nMaximum token count: {max_tokens}")




# import pandas as pd
# from transformers import AutoTokenizer
# import torch
# import sys
# import os

# # 添加rllm目录到Python路径
# sys.path.append('/wuhu_uni_ai/limingsheng/rllm')
# from rllm.system_prompts import SCENECOT_SYSTEM_PROMPT

# # 加载tokenizer
# print("Loading tokenizer...")
# tokenizer = AutoTokenizer.from_pretrained('/wuhu_uni_ai/limingsheng/ckpt/Qwen/Qwen2.5-7B-Instruct', trust_remote_code=True)

# # 计算token数量
# tokens = tokenizer(SCENECOT_SYSTEM_PROMPT, return_tensors='pt')
# token_count = tokens.input_ids.size(1)

# print(f"\nSCENECOT_SYSTEM_PROMPT token count: {token_count}")




import pandas as pd

# 读取Parquet文件
df = pd.read_parquet('/wuhu_uni_ai/limingsheng/rllm/rllm/data/train_scenecot_sft.parquet')

# # 打印第一行数据
# print("第一行数据：")
# print(df.iloc[0])

# 如果需要更详细的显示，可以使用：
# print("\n详细信息：")
# print(df.iloc[0].to_dict())
print(len(df))