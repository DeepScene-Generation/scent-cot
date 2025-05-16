set -x
wandb off

# Set default model path if not provided
if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH="Qwen/Qwen2.5-7B-Instruct"
fi


torchrun --standalone --nnodes=1 --nproc_per_node=8 \
    -m verl.trainer.fsdp_sft_trainer \
    data.train_files=data/train_scenecot_sft.parquet \
    data.val_files=test_scenecot.parquet \
    data.prompt_key=prompt \
    data.response_key=reward_model \
    +data.use_system_prompt=scene_cot \
    optim.lr=1e-5 \
    data.max_length=24576 \
    +data.prompt_dict_keys=['content'] \
    +data.response_dict_keys=['ground_truth'] \
    data.train_batch_size=8 \
    data.micro_batch_size=8 \
    model.partial_pretrain=$MODEL_PATH \
    trainer.default_local_dir=checkpoints/deepscene \
    trainer.project_name=deepscene-sft \
    trainer.experiment_name=deepscene-qwen-instruct-7b-3epoch \
    trainer.logger=['console'] \
    trainer.total_epochs=3 \
    +ulysses_sequence_parallel_size=1 \
    +use_remove_padding=true \
    trainer.default_hdfs_dir=null $@
