import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import torch
import os
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

# We'll use the Qwen 1.5B instruct model
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
OUTPUT_DIR = "./finetuning/hvac_finetuned_model"

def finetune():
    print("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    
    device_map = "auto" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=True
    )
    
    # LoRA config - train only ~1% of parameters
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load dataset
    print("Loading dataset...")
    dataset = load_dataset("json", data_files="finetuning/hvac_dataset.jsonl", split="train")
    
    # Format the dataset for chat template
    def format_chat_template(example):
        return {"text": tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)}
        
    dataset = dataset.map(format_chat_template)
    
    # Training arguments
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        learning_rate=2e-4,
        fp16=torch.cuda.is_available(),
        logging_steps=10,
        save_steps=100,
        report_to="none",
        dataset_text_field="text"
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset
    )
    
    print("Starting fine-tuning... (this may take a while depending on hardware)")
    trainer.train()
    
    print("Saving fine-tuned model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"✅ Fine-tuning complete! Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    finetune()
