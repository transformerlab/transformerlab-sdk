#!/usr/bin/env python3
"""
Test script using HuggingFace SFTTrainer to demonstrate automatic wandb URL detection
when wandb is initialized within ML frameworks like TRL.
"""

import os
from datetime import datetime
from time import sleep

from lab import lab


def train_with_trl():
    """Training function using HuggingFace SFTTrainer with automatic wandb detection"""
    
    # Training configuration
    training_config = {
        "experiment_name": "trl-wandb-test",
        "model_name": "HuggingFaceTB/SmolLM-135M-Instruct",
        "dataset": "Trelis/touch-rugby-rules",
        "template_name": "trl-wandb-demo",
        "output_dir": "./output",
        "log_to_wandb": True,
        "_config": {
            "dataset_name": "Trelis/touch-rugby-rules",
            "lr": 2e-5,
            "num_train_epochs": 1,
            "batch_size": 2,  # Small batch size for testing
            "gradient_accumulation_steps": 1,
            "warmup_ratio": 0.03,
            "weight_decay": 0.01,
            "max_seq_length": 512,
            "logging_steps": 1,
            "save_steps": 100,
            "eval_steps": 100,
            "report_to": ["wandb"],  # Enable wandb reporting in SFTTrainer
        },
    }

    try:
        # Initialize lab with default/simple API
        lab.init()
        lab.set_config(training_config)

        # Log start time
        start_time = datetime.now()
        lab.log(f"Training started at {start_time}")

        # Create output directory if it doesn't exist
        os.makedirs(training_config["output_dir"], exist_ok=True)

        # Load dataset
        lab.log("Loading dataset...")
        try:
            from datasets import load_dataset
            dataset = load_dataset(training_config["dataset"])
            lab.log(f"Loaded dataset with {len(dataset['train'])} examples")
        except Exception as e:
            lab.log(f"Error loading dataset: {e}")
            # Create a small fake dataset for testing
            from datasets import Dataset
            dataset = {
                "train": Dataset.from_list([
                    {"text": "What are the rules of touch rugby?"},
                    {"text": "How many players are on a touch rugby team?"},
                    {"text": "What is the objective of touch rugby?"},
                ])
            }
            lab.log("Using fake dataset for testing")

        lab.update_progress(20)

        # Load model and tokenizer
        lab.log("Loading model and tokenizer...")
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            model_name = training_config["model_name"]
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Add pad token if it doesn't exist
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            lab.log(f"Loaded model: {model_name}")
            
        except ImportError:
            lab.log("⚠️  Transformers not available, skipping real training")
            lab.finish("Training skipped - transformers not available")
            return {"status": "skipped", "reason": "transformers not available"}
        except Exception as e:
            lab.log(f"Error loading model: {e}")
            lab.finish("Training failed - model loading error")
            return {"status": "error", "error": str(e)}

        lab.update_progress(40)

        # Set up SFTTrainer with wandb integration
        lab.log("Setting up SFTTrainer with wandb integration...")
        try:
            from trl import SFTTrainer, SFTConfig
            
            # SFTConfig with wandb reporting
            training_args = SFTConfig(
                output_dir=training_config["output_dir"],
                num_train_epochs=training_config["_config"]["num_train_epochs"],
                per_device_train_batch_size=training_config["_config"]["batch_size"],
                gradient_accumulation_steps=training_config["_config"]["gradient_accumulation_steps"],
                learning_rate=training_config["_config"]["lr"],
                warmup_ratio=training_config["_config"]["warmup_ratio"],
                weight_decay=training_config["_config"]["weight_decay"],
                max_seq_length=training_config["_config"]["max_seq_length"],
                logging_steps=training_config["_config"]["logging_steps"],
                save_steps=training_config["_config"]["save_steps"],
                eval_steps=training_config["_config"]["eval_steps"],
                report_to=training_config["_config"]["report_to"],
                run_name=f"trl-test-{lab.job.id}",
                logging_dir=f"{training_config['output_dir']}/logs",
                remove_unused_columns=False,
                push_to_hub=False,
            )
            
            # Create SFTTrainer - this will initialize wandb if report_to includes "wandb"
            trainer = SFTTrainer(
                model=model,
                args=training_args,
                train_dataset=dataset["train"],
                tokenizer=tokenizer,
                dataset_text_field="text",
            )
            
            lab.log("✅ SFTTrainer created - wandb should be initialized automatically!")
            lab.log("🔍 Checking for wandb URL detection...")
            
        except ImportError:
            lab.log("⚠️  TRL not available, using basic training simulation")
            # Simulate wandb initialization for testing
            try:
                import wandb
                if wandb.run is None:
                    wandb.init(
                        project="transformerlab-trl-test",
                        name=f"trl-sim-{lab.job.id}",
                        config=training_config["_config"]
                    )
                    lab.log("✅ Simulated wandb initialization for testing")
            except Exception:
                pass
        except Exception as e:
            lab.log(f"Error setting up SFTTrainer: {e}")
            lab.finish("Training failed - trainer setup error")
            return {"status": "error", "error": str(e)}

        lab.update_progress(60)

        # Start training - this is where wandb will be initialized if using SFTTrainer
        lab.log("Starting training with SFTTrainer...")
        try:
            if 'trainer' in locals():
                # Real training with SFTTrainer
                trainer.train()
                lab.log("✅ Training completed with SFTTrainer")
            else:
                # Simulate training
                lab.log("Simulating training...")
                for i in range(3):
                    sleep(1)
                    lab.log(f"Training step {i + 1}/3")
                    lab.update_progress(60 + (i + 1) * 10)
                    
                    # Log some fake metrics to wandb if available
                    try:
                        import wandb
                        if wandb.run is not None:
                            fake_loss = 0.5 - (i + 1) * 0.1
                            fake_accuracy = 0.6 + (i + 1) * 0.1
                            wandb.log({
                                "train/loss": fake_loss,
                                "train/accuracy": fake_accuracy,
                                "step": i + 1
                            })
                            lab.log(f"📈 Logged metrics to wandb: loss={fake_loss:.3f}, accuracy={fake_accuracy:.3f}")
                    except Exception:
                        pass
                        
        except Exception as e:
            lab.log(f"Error during training: {e}")
            # Continue to check for wandb URL even if training fails

        lab.update_progress(90)

        # Calculate training time
        end_time = datetime.now()
        training_duration = end_time - start_time
        lab.log(f"Training completed in {training_duration}")
        
        # Get the captured wandb URL from job data for reporting
        job_data = lab.job.get_job_data()
        captured_wandb_url = job_data.get("wandb_run_url", "None")
        lab.log(f"📋 Final wandb URL stored in job data: {captured_wandb_url}")
        
        # Finish wandb run if it was initialized
        try:
            import wandb
            if wandb.run is not None:
                wandb.finish()
                lab.log("✅ Wandb run finished")
        except Exception:
            pass
        
        print("Complete")

        # Complete the job in TransformerLab via facade
        lab.finish("Training completed successfully with SFTTrainer")

        return {
            "status": "success",
            "job_id": lab.job.id,
            "duration": str(training_duration),
            "output_dir": training_config["output_dir"],
            "wandb_url": captured_wandb_url,
            "trainer_type": "SFTTrainer" if 'trainer' in locals() else "simulated",
        }

    except KeyboardInterrupt:
        lab.error("Stopped by user or remotely")
        return {"status": "stopped", "job_id": lab.job.id}

    except Exception as e:
        error_msg = str(e)
        print(f"Training failed: {error_msg}")

        import traceback
        traceback.print_exc()
        lab.error(error_msg)
        return {"status": "error", "job_id": lab.job.id, "error": error_msg}


if __name__ == "__main__":
    result = train_with_trl()
    print("Training result:", result)
