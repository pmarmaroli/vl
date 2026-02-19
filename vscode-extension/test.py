# Import necessary libraries for ML training pipeline
import os
import json
import yaml
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import librosa
import soundfile as sf
from datasets import Dataset
from transformers import (
    Wav2Vec2Processor, 
    Wav2Vec2ForCTC, 
    TrainingArguments, 
    Trainer
)
from peft import LoraConfig, get_peft_model
import evaluate
import argparse

"""
Complete training pipeline for French phonemizer fine-tuning
Fine-tunes Wav2Vec2 model using DoRA for improved phoneme recognition
"""

@dataclass
class DataCollatorCTCWithPadding:
    """
    Data collator that will dynamically pad the inputs received.
    Handles variable-length audio sequences for CTC training.
    """
    processor: Wav2Vec2Processor
    padding: bool = True
    
    def __call__(self, features: List[Dict]) -> Dict:
        # Extract input features (audio data) from batch
        input_features = [{'input_values': feature['input_values']} for feature in features]
        
        # Extract label features (phoneme sequences) from batch
        label_features = [{'input_ids': feature['labels']} for feature in features]
        
        # Pad input sequences to same length within batch
        batch = self.processor.pad(input_features, padding=self.padding, return_tensors="pt")
        
        # Pad label sequences to same length within batch
        labels_batch = self.processor.pad(label_features, padding=self.padding, return_tensors="pt")
        
        # Mask padded positions in labels with -100 (ignored by loss function)
        labels = labels_batch['input_ids'].masked_fill(labels_batch.attention_mask.ne(1), -100)
        
        # Add labels to the batch
        batch['labels'] = labels
        return batch


class PhonemeTrainer:
    """Handles training of phoneme recognition model with LoRA fine-tuning"""
    
    def __init__(self, config_path: str):
        """
        Initialize trainer with configuration
        
        Args:
            config_path: Path to YAML training configuration file
        """
        # Load training configuration from YAML file
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Set random seed for reproducible results
        self._set_seed(self.config.get('seed', 42))

    def _set_seed(self, seed: int):
        """Set random seed across all random number generators for reproducibility"""
        torch.manual_seed(seed)  # PyTorch CPU
        np.random.seed(seed)     # NumPy
        
        # Set CUDA seeds if GPU is available
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)  # All CUDA devices

    def load_model(self):
        """Load base Wav2Vec2 model and apply LoRA for parameter-efficient fine-tuning"""
        print(f"Loading model: {self.config['model']['name']}")
        
        # Load pre-trained processor for audio feature extraction
        self.processor = Wav2Vec2Processor.from_pretrained(self.config['model']['name'])
        
        # Load pre-trained model for CTC (Connectionist Temporal Classification)
        self.model = Wav2Vec2ForCTC.from_pretrained(self.config['model']['name'])
        
        # Configure LoRA (Low-Rank Adaptation) for efficient fine-tuning
        lora_config = self.config['model']['lora']
        config = LoraConfig(
            r=lora_config['r'],                    # Rank of adaptation
            lora_alpha=lora_config['alpha'],       # Scaling parameter
            target_modules=lora_config['target_modules'],  # Modules to adapt
            lora_dropout=lora_config['dropout'],   # Dropout rate
            bias=lora_config['bias']               # Bias handling
        )
        
        # Apply LoRA to the model
        self.model = get_peft_model(self.model, config)
        
        print('Trainable parameters:')
        self.model.print_trainable_parameters()  # Show parameter efficiency

    def load_dataset(self, annotation_path: str):
        """
        Load dataset from JSON annotation files
        
        Args:
            annotation_path: Path to directory containing train.json, val.json, test.json
        """
        print(f"Loading dataset from: {annotation_path}")
        dataset_dict = {}
        
        # Load each split (train/validation/test)
        for split in ['train', 'val', 'test']:
            json_path = Path(annotation_path) / f"{split}.json"
            
            # Skip if split file doesn't exist
            if not json_path.exists():
                print(f"Warning: {json_path} not found, skipping {split} split")
                continue
            
            # Load annotations from JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create HuggingFace Dataset from annotations
            dataset_dict[split] = Dataset.from_dict({
                'audio': [item['audio_path'] for item in data],      # Audio file paths
                'phoneme': [item['phoneme'] for item in data],       # Phoneme transcriptions
                'speaker_id': [item['speaker_id'] for item in data]  # Speaker identifiers
            })
            
            print(f"Loaded {len(dataset_dict[split])} samples for {split}")
        
        self.dataset_dict = dataset_dict

    def preprocess_function(self, batch):
        """
        Preprocess audio files and phoneme labels for model input
        
        Args:
            batch: Batch of samples from dataset
            
        Returns:
            Preprocessed batch with input_values and labels
        """
        # Load and process audio files
        audio_arrays = [audio['array'] for audio in batch['audio']]
        
        # Extract audio features using Wav2Vec2 processor
        inputs = self.processor(
            audio_arrays, 
            sampling_rate=16000,  # Standard sampling rate for Wav2Vec2
            return_tensors="pt",
            padding=True
        )
        
        # Process phoneme labels into token IDs
        with self.processor.as_target_processor():
            labels = self.processor(batch['phoneme']).input_ids
        
        # Prepare batch for training
        batch['input_values'] = [val.squeeze() for val in inputs.input_values]
        batch['labels'] = labels
        
        return batch

    def prepare_dataset(self):
        """Apply preprocessing to all dataset splits"""
        print('Preparing dataset...')
        
        # Apply preprocessing function to each split
        for split in self.dataset_dict.keys():
            self.dataset_dict[split] = self.dataset_dict[split].map(
                self.preprocess_function,
                batched=True,
                num_proc=4,  # Use multiple processes for faster preprocessing
                remove_columns=['audio', 'phoneme', 'speaker_id']  # Remove raw data
            )

    def compute_metrics(self, eval_pred):
        """
        Compute evaluation metrics during training
        
        Args:
            eval_pred: Predictions and labels from evaluation
            
        Returns:
            Dictionary with computed metrics (PER - Phoneme Error Rate)
        """
        pred_logits = eval_pred.predictions
        pred_ids = np.argmax(pred_logits, axis=-1)  # Get predicted token IDs
        
        # Prepare label IDs (replace -100 with pad token for decoding)
        label_ids = eval_pred.label_ids.copy()
        label_ids[label_ids == -100] = self.processor.tokenizer.pad_token_id
        
        # Decode predictions and labels to text
        pred_str = self.processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = self.processor.batch_decode(label_ids, skip_special_tokens=True)
        
        # Compute Phoneme Error Rate (PER) - similar to Word Error Rate (WER)
        evaluator = evaluate.load("wer")  # Using WER as proxy for PER
        per = evaluator.compute(predictions=pred_str, references=label_str)
        
        return {'per': per}

    def train(self, output_dir=None):
        """
        Execute model training
        
        Args:
            output_dir: Directory to save training outputs and checkpoints
        """
        # Use config output dir if not specified
        if output_dir is None:
            output_dir = self.config['training']['output_dir']
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(output_dir) / f"phoneme_training_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Training output will be saved to: {output_dir}")
        
        # Configure training parameters
        training_config = self.config['training']
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=training_config['epochs'],
            per_device_train_batch_size=training_config['batch_size'],
            per_device_eval_batch_size=training_config['eval_batch_size'],
            learning_rate=training_config['learning_rate'],
            warmup_steps=training_config['warmup_steps'],
            logging_steps=training_config['logging_steps'],
            eval_steps=training_config['eval_steps'],
            save_steps=training_config['save_steps'],
            evaluation_strategy="steps",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="per",
            greater_is_better=False,  # Lower PER is better
            push_to_hub=False,
            dataloader_pin_memory=False,  # Disable for stability
        )
        
        # Initialize data collator for dynamic padding
        data_collator = DataCollatorCTCWithPadding(
            processor=self.processor,
            padding=True
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.dataset_dict['train'],
            eval_dataset=self.dataset_dict['val'],
            data_collator=data_collator,
            compute_metrics=self.compute_metrics,
            tokenizer=self.processor.feature_extractor,
        )
        
        # Save training configuration for reproducibility
        with open(output_dir / 'training_config.yaml', 'w') as f:
            yaml.dump(self.config, f)
        
        print('Starting training...')
        trainer.train()
        
        # Save final model and processor
        final_model_dir = output_dir / 'final_model'
        trainer.save_model(str(final_model_dir))
        self.processor.save_pretrained(str(final_model_dir))
        
        print(f"Training completed. Final model saved to: {final_model_dir}")
        
        return trainer


def main():
    """Main training script entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Train French phoneme recognition model")
    parser.add_argument('--config', required=True, help='Path to training config YAML file')
    parser.add_argument('--annotations', required=True, help='Path to annotation directory')
    parser.ad
    args = parser.parse_args()
    
    # Initialize trainer with configuration
    
    trainer = PhonemeTrainer(args.config)
    
    # Load pre-trained model and apply LoRA
    trainer.load_model()
    
    # Load and preprocess dataset
    trainer.load_dataset(args.annotations)
    trainer.prepare_dataset()
    
    # Execute training
    trainer.train(args.output_dir)


# Script entry point
if __name__ == '__main__':
    main()