#!/usr/bin/env python3
"""
VHDL Testbench Generator with AI

Generates comprehensive VHDL testbenches for validated designs using AI.
Two-stage process: corner case identification → testbench generation.

Features:
- Corner case identification
- Self-checking testbench generation
- GHDL validation of testbenches
- Dual-stage dataset creation
- Supports multiple prompt variations

Usage:
    export DEEPSEEK_API_KEY="your_key_here"
    python3 vhdl_testbench_generator.py --input valid_designs.jsonl --output testbench_dataset.jsonl
"""

import os
import re
import json
import argparse
import subprocess
import tempfile
import random
from pathlib import Path
from typing import Tuple, Optional, Dict
from tqdm import tqdm
import requests


class TestbenchGenerator:
    """AI-powered VHDL testbench generator."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/v1/chat/completions",
                 model: str = "deepseek-chat", std: str = "08"):
        """
        Initialize testbench generator.
        
        Args:
            api_key: API key for AI service
            api_url: API endpoint URL
            model: Model name
            std: VHDL standard
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.std = std
        self.timeout = 60
        
        # Prompt variations for diversity
        self.corner_case_prompts = [
            "Generate a structured list of corner cases for the VHDL design {entity}.",
            "Functional corner cases that may break {entity}.",
            "List all possible edge-case scenarios for {entity}.",
            "Enumerate abnormal signal transitions and boundary conditions for {entity}.",
            "Provide comprehensive corner case coverage for {entity}.",
        ]
        
        self.testbench_prompts = [
            "Generate a VHDL-2008 self-checking testbench for {entity}.",
            "Create a scenario-driven VHDL testbench for {entity} that covers all listed corner cases.",
            "Write a comprehensive functional testbench with assertions for {entity}.",
            "Develop a simulation testbench for {entity} covering edge cases.",
        ]
    
    def call_ai(self, prompt: str, max_tokens: int = 8192) -> Optional[str]:
        """Call AI API with retry logic."""
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
                    return None
                
            except Exception:
                pass
        
        return None
    
    def extract_entity_name(self, vhdl_code: str) -> Optional[str]:
        """Extract entity name from VHDL code."""
        match = re.search(r'\bentity\s+(\w+)\s+is', vhdl_code, re.IGNORECASE)
        return match.group(1) if match else None
    
    def extract_corner_cases(self, response: str) -> Optional[str]:
        """Extract corner cases from AI response."""
        patterns = [
            r"--CORNER CASES START\s*\n(.*?)\n--CORNER CASES END",
            r"Corner Cases?:\s*\n(.*?)(?:\n\n|\Z)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Return whole response if no markers
        return response.strip()
    
    def extract_testbench(self, response: str) -> Optional[str]:
        """Extract testbench code from AI response."""
        patterns = [
            r"--VHDL TESTBENCH START\s*\n(.*?)\n--VHDL TESTBENCH END",
            r"```vhdl\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def validate_vhdl(self, vhdl_code: str, entity_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate VHDL with GHDL.
        
        Args:
            vhdl_code: VHDL source code
            entity_name: Optional entity name for elaboration
            
        Returns:
            Tuple of (success, error_message)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vhd', delete=False) as f:
            f.write(vhdl_code)
            temp_file = f.name
        
        try:
            # Analyze
            result = subprocess.run(
                ["ghdl", "-a", f"--std={self.std}", temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, (result.stdout + result.stderr).strip()
            
            # Elaborate if entity name provided
            if entity_name:
                result = subprocess.run(
                    ["ghdl", "-e", f"--std={self.std}", entity_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return False, (result.stdout + result.stderr).strip()
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def generate_corner_cases(self, vhdl_code: str, entity_name: str) -> Optional[str]:
        """Generate corner cases for design."""
        prompt_template = random.choice(self.corner_case_prompts)
        prompt = f"""{prompt_template.format(entity=entity_name)}

VHDL Design:
```vhdl
{vhdl_code}
```

Provide a comprehensive list of corner cases to verify this design.
Wrap your response with:
--CORNER CASES START
...
--CORNER CASES END"""
        
        response = self.call_ai(prompt)
        if not response:
            return None
        
        return self.extract_corner_cases(response)
    
    def generate_testbench(self, vhdl_code: str, corner_cases: str, entity_name: str) -> Optional[str]:
        """Generate testbench for design."""
        prompt_template = random.choice(self.testbench_prompts)
        prompt = f"""{prompt_template.format(entity=entity_name)}

Design to Test:
```vhdl
{vhdl_code}
```

Corner Cases to Cover:
{corner_cases}

Requirements:
1. Use VHDL-2008 standard
2. Create self-checking testbench with assertions
3. Cover ALL listed corner cases
4. Use meaningful signal names and comments

Wrap your testbench with:
--VHDL TESTBENCH START
...
--VHDL TESTBENCH END"""
        
        response = self.call_ai(prompt, max_tokens=12000)
        if not response:
            return None
        
        return self.extract_testbench(response)
    
    def process_designs(self, input_file: str, output_file: str):
        """
        Process designs and generate testbenches.
        
        Creates dual-stage dataset:
        - Stage 1: DUT → Corner Cases
        - Stage 2: DUT + Corner Cases → Testbench
        """
        stats = {"total": 0, "stage1_success": 0, "stage2_success": 0, "failed": 0}
        
        with open(input_file, 'r', encoding='utf-8') as fin:
            entries = [json.loads(line) for line in fin]
        
        with open(output_file, 'w', encoding='utf-8') as fout:
            for entry in tqdm(entries, desc="Generating testbenches"):
                stats["total"] += 1
                
                vhdl_code = entry.get("prompt", entry.get("vhdl_code", ""))
                if not vhdl_code:
                    stats["failed"] += 1
                    continue
                
                entity_name = self.extract_entity_name(vhdl_code)
                if not entity_name:
                    stats["failed"] += 1
                    continue
                
                # Stage 1: Generate corner cases
                corner_cases = self.generate_corner_cases(vhdl_code, entity_name)
                if not corner_cases:
                    stats["failed"] += 1
                    continue
                
                stats["stage1_success"] += 1
                
                # Write Stage 1 entry
                stage1_entry = {
                    "stage": 1,
                    "entity": entity_name,
                    "messages": [
                        {"role": "user", "content": f"{entity_name} VHDL Design:\n{vhdl_code}"},
                        {"role": "assistant", "content": corner_cases}
                    ]
                }
                fout.write(json.dumps(stage1_entry) + "\n")
                fout.flush()
                
                # Stage 2: Generate testbench
                testbench = self.generate_testbench(vhdl_code, corner_cases, entity_name)
                if not testbench:
                    continue
                
                # Validate testbench
                tb_entity = self.extract_entity_name(testbench)
                if not tb_entity:
                    continue
                
                # First validate design, then testbench
                design_ok, _ = self.validate_vhdl(vhdl_code, entity_name)
                if not design_ok:
                    continue
                
                tb_ok, _ = self.validate_vhdl(testbench, tb_entity)
                if not tb_ok:
                    continue
                
                stats["stage2_success"] += 1
                
                # Write Stage 2 entry
                stage2_entry = {
                    "stage": 2,
                    "entity": entity_name,
                    "testbench_entity": tb_entity,
                    "messages": [
                        {"role": "user", "content": f"{entity_name} VHDL Design:\n{vhdl_code}\n\nCorner Cases:\n{corner_cases}"},
                        {"role": "assistant", "content": testbench}
                    ]
                }
                fout.write(json.dumps(stage2_entry) + "\n")
                fout.flush()
        
        # Print statistics
        print(f"\n{'='*60}")
        print(f"Testbench Generation Results")
        print(f"{'='*60}")
        print(f"Total designs:         {stats['total']:>6}")
        print(f"Stage 1 (corner cases): {stats['stage1_success']:>6} ({stats['stage1_success']/stats['total']*100:.1f}%)")
        print(f"Stage 2 (testbenches):  {stats['stage2_success']:>6} ({stats['stage2_success']/stats['total']*100:.1f}%)")
        print(f"Failed:                {stats['failed']:>6}")
        print(f"{'='*60}")
        print(f"✅ Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="AI-powered VHDL testbench generator")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file with validated designs")
    parser.add_argument("--output", "-o", required=True, help="Output JSONL file with dual-stage dataset")
    parser.add_argument("--api-key", help="API key (or set DEEPSEEK_API_KEY env var)")
    parser.add_argument("--api-url", default="https://api.deepseek.com/v1/chat/completions", 
                       help="API endpoint URL")
    parser.add_argument("--model", default="deepseek-chat", help="Model name")
    parser.add_argument("--std", default="08", choices=["93", "02", "08"], help="VHDL standard")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("API key required: use --api-key or set DEEPSEEK_API_KEY environment variable")
    
    generator = TestbenchGenerator(
        api_key=api_key,
        api_url=args.api_url,
        model=args.model,
        std=args.std
    )
    
    generator.process_designs(args.input, args.output)


if __name__ == "__main__":
    main()
