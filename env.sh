conda create -n nips_2025 python==3.10
conda activate nips_2025
pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124 -i https://pypi.doubanio.com/simple/
pip3 install flash-attn --no-build-isolation
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple/


pip install -e ./verl -i https://pypi.doubanio.com/simple/



export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download --repo-type model --resume-download Qwen/Qwen3-4B --local-dir ./ckpt/Qwen/Qwen3-4B


huggingface-cli download --repo-type model --resume-download openai/clip-vit-large-patch14 --local-dir ./ckpt/openai/clip-vit-large-patch14



gpustat -i 0.5

pip install vllm -i https://pypi.tuna.tsinghua.edu.cn/simple/

pip install transformers==4.47.1 -i https://pypi.tuna.tsinghua.edu.cn/simple/
#old version: 4.47.1