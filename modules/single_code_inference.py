# python single_code_inference.py  test_code_fixed/test_code_1.cpp         
# python single_code_inference.py  test_code_fixed/test_code_fixed_1_1.cpp         

#!/usr/bin/env python3

"""
Single Code Vulnerability Detection

A simplified interface for detecting vulnerabilities in a single piece of code.
"""

import logging
import torch
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from modules.mask import preprocess_and_mask
from modules.vulnerability_detector import (
    ModelConfig, VulnerabilityDetector, VulnerabilityModel, 
    ModelLoader, CodePreprocessor, MetricsCalculator
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SingleCodeResult:
    """Result for single code vulnerability detection."""
    prediction: int
    confidence: float
    probabilities: Dict[int, float]
    processed_code: str
    vulnerability_type: str


class SingleCodeDetector:
    """Simplified detector for single code snippets."""
    
    # Vulnerability type mapping (adjust based on your model's classes)
    VULNERABILITY_TYPES = {
        0: "Safe",
        1: "CWE-119", 
        2: "CWE-120",
        3: "CWE-190"
    }
    
    def __init__(self, 
                 model_name_or_path: str = "microsoft/codebert-base",
                 checkpoint_path: Optional[str] = None,
                 model_type: str = "roberta",
                 num_labels: int = 4,
                 device: Optional[str] = None):
        """
        Initialize single code detector.
        
        Args:
            model_name_or_path: HuggingFace model name or local path
            checkpoint_path: Path to trained model checkpoint
            model_type: Type of model architecture
            num_labels: Number of vulnerability classes
            device: Device to run on ('cpu', 'cuda', or None for auto)
        """
        self.config = ModelConfig(
            model_name_or_path=model_name_or_path,
            checkpoint_path=checkpoint_path,
            model_type=model_type,
            num_labels=num_labels,
            device=device,
            batch_size=1,  # Single inference
            block_size=512
        )
        
        self.device = torch.device(self.config.device)
        self.preprocessor = CodePreprocessor()
        
        # Load model and tokenizer
        self.tokenizer, self.model = self._load_model()
        
        logger.info(f"Single code detector initialized on {self.device}")
    
    def _load_model(self) -> Tuple:
        """Load model and tokenizer."""
        model_loader = ModelLoader(self.config)
        model_config, tokenizer, base_model = model_loader.load_tokenizer_and_base_model()
        
        # Build classifier model
        model = VulnerabilityModel(base_model, self.config, tokenizer)
        
        # Load checkpoint if provided
        if self.config.checkpoint_path:
            logger.info(f"Loading checkpoint from {self.config.checkpoint_path}")
            state_dict = torch.load(self.config.checkpoint_path, map_location='cpu')
            model.load_state_dict(state_dict, strict=False)
        
        model.to(self.device)
        model.eval()
        
        return tokenizer, model
    
    def predict(self, code: str, language: str = 'cpp') -> SingleCodeResult:
        """
        Predict vulnerability for a single code snippet.
        
        Args:
            code: Source code to analyze
            language: Programming language (cpp, c, java, js, etc.)
            
        Returns:
            SingleCodeResult with prediction details
        """
        try:
            # Preprocess the code
            processed_code = self._preprocess_code(code, language)
            
            # Tokenize
            input_ids = self._tokenize_code(processed_code)
            
            # Run inference
            with torch.no_grad():
                logits = self.model(input_ids)
                probabilities = torch.softmax(logits, dim=-1)
                prediction = torch.argmax(logits, dim=-1).item()
                confidence = probabilities.max().item()
                
                # Convert probabilities to dict
                prob_dict = {
                    i: probabilities[0][i].item() 
                    for i in range(self.config.num_labels)
                }
            
            vulnerability_type = self.VULNERABILITY_TYPES.get(prediction, f"Class_{prediction}")
            
            return SingleCodeResult(
                prediction=prediction,
                confidence=confidence,
                probabilities=prob_dict,
                processed_code=processed_code,
                vulnerability_type=vulnerability_type
            )
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise
    
    def _preprocess_code(self, code: str, language: str) -> str:
        """Preprocess code using masking."""
        try:
            # Use the mask module for preprocessing
            masked, _ = preprocess_and_mask(
                code,
                language=language,
                remove_whitespace='normalize'
            )
            return masked
        except Exception as e:
            logger.warning(f"Masking failed, using simple preprocessing: {e}")
            # Fallback to simple preprocessing
            return self.preprocessor.preprocess_code(code, language)
    
    def _tokenize_code(self, code: str) -> torch.Tensor:
        """Tokenize code for the model."""
        if self.config.model_type in ["codet5", "t5", "codegen", "codellama"]:
            # Generative models
            input_ids = self.tokenizer.encode(
                code,
                max_length=self.config.block_size,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
        else:
            # Encoder models (BERT, RoBERTa, etc.)
            tokens = self.tokenizer.tokenize(code)
            tokens = tokens[:self.config.block_size - 2]
            
            # Add special tokens
            source_tokens = [self.tokenizer.cls_token] + tokens + [self.tokenizer.sep_token]
            source_ids = self.tokenizer.convert_tokens_to_ids(source_tokens)
            
            # Add padding
            padding_length = self.config.block_size - len(source_ids)
            source_ids += [self.tokenizer.pad_token_id] * padding_length
            
            input_ids = torch.tensor([source_ids], dtype=torch.long)
        
        return input_ids.to(self.device)
    
    def predict_batch(self, codes: list, language: str = 'cpp') -> list:
        """
        Predict vulnerabilities for multiple code snippets.
        
        Args:
            codes: List of source code strings
            language: Programming language
            
        Returns:
            List of SingleCodeResult objects
        """
        results = []
        for code in codes:
            result = self.predict(code, language)
            results.append(result)
        return results


def get_user_code():
    """Get C code input from user via command line."""
    print("=== C Code Vulnerability Detector ===")
    print("Enter your C code (end with EOF: Ctrl+D on Linux/Mac, Ctrl+Z on Windows):")
    print("Or type 'QUIT' to exit")
    print("-" * 50)
    
    lines = []
    try:
        while True:
            line = input()
            if line.strip().upper() == 'QUIT':
                return None
            lines.append(line)
    except EOFError:
        # User pressed Ctrl+D (Linux/Mac) or Ctrl+Z (Windows)
        pass
    
    return '\n'.join(lines)


def interactive_mode():
    """Interactive mode for continuous C code analysis."""
    print("=== Interactive C Code Vulnerability Detection ===")
    print("Commands:")
    print("  'help' - Show this help")
    print("  'quit' - Exit the program")
    print("  'example' - Show example vulnerable code")
    print("  Just paste your C code and press Enter twice")
    print()
    
    # Initialize detector
    detector = SingleCodeDetector(
        model_name_or_path="microsoft/codebert-base",
        checkpoint_path="models/checkpoints/model_etri_demo.bin",  # Optional
        model_type="roberta",
        num_labels=4
    )
    
    while True:
        print("-" * 50)
        print("Enter C code (press Enter twice to analyze, or type a command):")
        
        lines = []
        empty_lines = 0
        
        while True:
            try:
                line = input()
                
                # Handle commands
                if not lines and line.strip().lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    return
                elif not lines and line.strip().lower() == 'help':
                    print("Commands:")
                    print("  'help' - Show this help")
                    print("  'quit' - Exit the program") 
                    print("  'example' - Show example vulnerable code")
                    print("  Just paste your C code and press Enter twice")
                    break
                elif not lines and line.strip().lower() == 'example':
                    show_example_code()
                    break
                
                if line.strip() == "":
                    empty_lines += 1
                    if empty_lines >= 2 and lines:
                        # Two empty lines - analyze the code
                        break
                else:
                    empty_lines = 0
                
                lines.append(line)
                
            except EOFError:
                if lines:
                    break
                else:
                    print("\\nGoodbye!")
                    return
            except KeyboardInterrupt:
                print("\\nGoodbye!")
                return
        
        if lines:
            code = '\\n'.join(lines)
            analyze_code(detector, code)


def show_example_code():
    """Show example vulnerable C code."""
    example = """#include <stdio.h>
#include <string.h>

int main() {
    char buffer[10];
    printf("Enter your name: ");
    gets(buffer);  // Dangerous: no bounds checking
    printf("Hello, %s!\\n", buffer);
    return 0;
}"""
    print("Example vulnerable C code (Buffer Overflow):")
    print(example)


def analyze_code(detector, code):
    """Analyze a single piece of C code."""
    try:
        # print("\\nAnalyzing code...")
        # print("=" * 40)
        
        result = detector.predict(code.strip(), language='c')
        
        # Determine risk level and color
        # if result.confidence > 0.8:
        #     risk_level = "HIGH RISK"
        # elif result.confidence > 0.5:
        #     risk_level = "MEDIUM RISK" 
        # else:
        #     risk_level = "LOW RISK"
        
        lines = []
        lines.append(f"RESULT: {result.vulnerability_type}\n")
        lines.append(f"CONFIDENCE: {result.confidence:.3f}\n")
        # print(f"RISK LEVEL: {risk_level}")

        # output_path = "result.txt"
        # with open(output_path, "w", encoding="utf-8") as f:
        #     f.write(f"-{result.vulnerability_type}")

        lines.append("Detailed Probabilities:\n")
        sorted_probs = sorted(result.probabilities.items(), key=lambda x: x[1], reverse=True)
        for class_id, prob in sorted_probs:
            vuln_type = detector.VULNERABILITY_TYPES.get(class_id, f"Class_{class_id}")
            bar_length = int(prob * 20)  # Simple text bar
            bar = "█" * bar_length + "░" * (20 - bar_length)
            # result.append(f"  {vuln_type:20} {bar} {prob:.3f}\n")
            lines.append(f"  {vuln_type:20} {prob:.3f}\n")
        
        # print("=" * 40)
        
        return result.vulnerability_type, "".join(lines)
        
    except Exception as e:
        print(f"Error analyzing code: {e}")


def main():
    # import pdb; pdb.set_trace()
    """Main function with different modes."""
    import sys
    
    if len(sys.argv) > 1:
        # File mode - read from file
        filename = sys.argv[1]
        try:
            with open(filename, 'r') as f:
                code = f.read()
            
            detector = SingleCodeDetector(
                model_name_or_path="microsoft/codebert-base",
                checkpoint_path="models/checkpoints/model_etri_demo.bin",  # Optional
                model_type="roberta",
                num_labels=4
            )
            
            print(f"Analyzing file: {filename}")
            vul_type, lines = analyze_code(detector, code)
            print(vul_type)
            print(lines)
            
        except FileNotFoundError:
            print(f"File not found: {filename}")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
