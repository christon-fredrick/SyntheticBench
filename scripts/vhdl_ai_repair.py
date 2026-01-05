#!/usr/bin/env python3
"""
AI-Assisted VHDL Repair with GHDL Validation

Repairs failed VHDL designs using AI (DeepSeek or OpenAI compatible APIs).
Validates repairs with GHDL and retries up to max attempts.

Features:
- Automatic VHDL error repair using AI
- Hierarchical design flattening
- GHDL validation loop
- Checkpoint/resume support
- Configurable API endpoints

Usage:
    export DEEPSEEK_API_KEY="your_key_here"
    python3 vhdl_ai_repair.py --input failed.jsonl --output repaired.jsonl --still-failed still_failed.jsonl
"""

import os
import re
import json
import argparse
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional
from tqdm import tqdm
import requests


class VHDLRepair:
    """AI-assisted VHDL repair with validation."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/v1/chat/completions",
                 model: str = "deepseek-chat", max_retries: int = 3, std: str = "08"):
        """
        Initialize repair engine.
        
        Args:
            api_key: API key for AI service
            api_url: API endpoint URL
            model: Model name
            max_retries: Maximum repair attempts per design
            std: VHDL standard (93, 02, 08)
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.max_retries = max_retries
        self.std = std
        self.timeout = 60
    
    def call_ai(self, prompt: str, max_tokens: int = 8192) -> Optional[str]:
        """
        Call AI API with retry logic.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum response tokens
            
        Returns:
            AI response text or None on failure
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        for attempt in range(3):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status_code == 402:
                    return None  # Out of credits
                
                time.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == 2:
                    return None
                time.sleep(2 ** attempt)
        
        return None
    
    def extract_vhdl(self, text: str) -> str:
        """Extract VHDL code from AI response."""
        # Try to find code between markers
        patterns = [
            r"--\s*1\.\s*VHDL\s+design\s+START\s*\n(.*?)\n--\s*END\s+of\s+VHDL\s+Design",
            r"```vhdl\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Return trimmed text if no markers found
        return text.strip()
    
    def validate_vhdl(self, vhdl_code: str) -> Tuple[bool, str]:
        """
        Validate VHDL with GHDL.
        
        Args:
            vhdl_code: VHDL source code
            
        Returns:
            Tuple of (success, error_message)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vhd', delete=False) as f:
            f.write(vhdl_code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ["ghdl", "-a", f"--std={self.std}", temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            success = result.returncode == 0
            error_msg = (result.stdout + result.stderr).strip()
            
            return success, error_msg
            
        except Exception as e:
            return False, str(e)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def repair_design(self, vhdl_code: str, error_log: str) -> Optional[str]:
        """
        Attempt to repair VHDL design.
        
        Args:
            vhdl_code: Original VHDL code
            error_log: GHDL error message
            
        Returns:
            Repaired VHDL code or None on failure
        """
        prompt = f"""You are a VHDL repair expert. Fix this VHDL code to compile with GHDL VHDL-2008.

Requirements:
1. Fix all syntax and compilation errors
2. If the design uses multiple entities/components (hierarchical), flatten it into a single entity
3. Preserve functionality
4. Return ONLY the corrected VHDL code, no explanations

Original VHDL:
```vhdl
{vhdl_code}
```

GHDL Error:
{error_log}

Return the corrected VHDL code:"""
        
        response = self.call_ai(prompt)
        if not response:
            return None
        
        return self.extract_vhdl(response)
    
    def process_failed_designs(self, input_file: str, output_repaired: str, 
                               output_failed: str, checkpoint_file: str = "repair_checkpoint.json"):
        """
        Process failed designs and attempt repairs.
        
        Args:
            input_file: JSONL file with failed designs
            output_repaired: Output file for successfully repaired designs
            output_failed: Output file for still-failed designs
            checkpoint_file: Checkpoint file for resume capability
        """
        # Load checkpoint
        processed_indices = set()
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                processed_indices = set(checkpoint.get("processed_indices", []))
        
        stats = {"total": 0, "repaired": 0, "still_failed": 0, "api_errors": 0}
        
        # Load all entries
        with open(input_file, 'r', encoding='utf-8') as f:
            entries = [json.loads(line) for line in f]
        
        with open(output_repaired, 'a', encoding='utf-8') as f_repaired, \
             open(output_failed, 'a', encoding='utf-8') as f_failed:
            
            for idx, entry in enumerate(tqdm(entries, desc="Repairing VHDL")):
                if idx in processed_indices:
                    continue
                
                stats["total"] += 1
                
                original_code = entry.get("prompt", entry.get("vhdl_code", ""))
                original_error = entry.get("error", "")
                
                vhdl_code = self.extract_vhdl(original_code)
                
                # Attempt repairs
                repaired = False
                for attempt in range(self.max_retries):
                    repaired_code = self.repair_design(vhdl_code, original_error)
                    
                    if not repaired_code:
                        stats["api_errors"] += 1
                        break
                    
                    # Validate repaired code
                    success, new_error = self.validate_vhdl(repaired_code)
                    
                    if success:
                        stats["repaired"] += 1
                        entry["original_code"] = original_code
                        entry["original_error"] = original_error
                        entry["repaired_code"] = repaired_code
                        entry["repair_attempts"] = attempt + 1
                        f_repaired.write(json.dumps(entry) + "\n")
                        f_repaired.flush()
                        repaired = True
                        break
                    
                    # Update for next attempt
                    vhdl_code = repaired_code
                    original_error = new_error
                
                if not repaired:
                    stats["still_failed"] += 1
                    entry["repair_failed"] = True
                    entry["final_error"] = original_error
                    f_failed.write(json.dumps(entry) + "\n")
                    f_failed.flush()
                
                # Save checkpoint
                processed_indices.add(idx)
                with open(checkpoint_file, 'w') as f:
                    json.dump({"processed_indices": list(processed_indices)}, f)
        
        # Print statistics
        print(f"\n{'='*60}")
        print(f"VHDL Repair Results")
        print(f"{'='*60}")
        print(f"Total attempted:   {stats['total']:>6}")
        print(f"Successfully repaired: {stats['repaired']:>6} ({stats['repaired']/stats['total']*100:.1f}%)")
        print(f"Still failed:      {stats['still_failed']:>6} ({stats['still_failed']/stats['total']*100:.1f}%)")
        print(f"API errors:        {stats['api_errors']:>6}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="AI-assisted VHDL repair with GHDL validation")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file with failed designs")
    parser.add_argument("--output", "-o", required=True, help="Output file for repaired designs")
    parser.add_argument("--still-failed", "-f", required=True, help="Output file for still-failed designs")
    parser.add_argument("--api-key", help="API key (or set DEEPSEEK_API_KEY env var)")
    parser.add_argument("--api-url", default="https://api.deepseek.com/v1/chat/completions", 
                       help="API endpoint URL")
    parser.add_argument("--model", default="deepseek-chat", help="Model name")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum repair attempts")
    parser.add_argument("--std", default="08", choices=["93", "02", "08"], help="VHDL standard")
    parser.add_argument("--checkpoint", default="repair_checkpoint.json", help="Checkpoint file")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("API key required: use --api-key or set DEEPSEEK_API_KEY environment variable")
    
    repair = VHDLRepair(
        api_key=api_key,
        api_url=args.api_url,
        model=args.model,
        max_retries=args.max_retries,
        std=args.std
    )
    
    repair.process_failed_designs(args.input, args.output, args.still_failed, args.checkpoint)


if __name__ == "__main__":
    main()
