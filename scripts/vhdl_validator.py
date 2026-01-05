#!/usr/bin/env python3
"""
Generic VHDL Validator with GHDL

Validates VHDL designs from JSONL files using GHDL compiler.
Extracts VHDL code, attempts compilation, and separates valid/failed entries.

Features:
- Supports VHDL-2008 standard
- Extracts VHDL from structured markers or raw text
- Outputs validated and failed designs separately
- Detailed error logging

Usage:
    python3 vhdl_validator.py --input designs.jsonl --output valid.jsonl --failed failed.jsonl
"""

import os
import re
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any
from tqdm import tqdm


class VHDLValidator:
    """VHDL design validator using GHDL."""
    
    def __init__(self, std="08", timeout=10):
        """
        Initialize validator.
        
        Args:
            std: VHDL standard (93, 02, 08)
            timeout: Compilation timeout in seconds
        """
        self.std = std
        self.timeout = timeout
        self._check_ghdl()
    
    def _check_ghdl(self):
        """Verify GHDL is installed."""
        try:
            subprocess.run(["ghdl", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("GHDL not found. Install with: sudo apt install ghdl")
    
    def extract_vhdl(self, text: str) -> str:
        """
        Extract VHDL code from text with or without markers.
        
        Supports formats:
        - --1. VHDL design START ... -- END of VHDL Design
        - Raw VHDL code
        
        Args:
            text: Input text containing VHDL
            
        Returns:
            Extracted VHDL code
        """
        # Normalize start marker (ensure newline after START)
        text = re.sub(
            r"(--\s*1\.\s*VHDL\s+design\s+START)(?!\s*\n)",
            r"\1\n",
            text,
            flags=re.IGNORECASE
        )
        
        # Try to extract between markers
        pattern = re.compile(
            r"--\s*1\.\s*VHDL\s+design\s+START\s*\n(.*?)\n--\s*END\s+of\s+VHDL\s+Design",
            re.IGNORECASE | re.DOTALL
        )
        
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        
        # No markers found - return trimmed text
        return text.strip()
    
    def validate(self, vhdl_code: str) -> Tuple[bool, str]:
        """
        Validate VHDL code with GHDL.
        
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
                timeout=self.timeout
            )
            
            success = result.returncode == 0
            error_msg = (result.stdout + result.stderr).strip()
            
            return success, error_msg
            
        except subprocess.TimeoutExpired:
            return False, f"Compilation timeout ({self.timeout}s)"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def process_jsonl(self, input_file: str, output_valid: str, output_failed: str, 
                     vhdl_key: str = "prompt"):
        """
        Process JSONL file and validate all VHDL designs.
        
        Args:
            input_file: Input JSONL file path
            output_valid: Output file for valid designs
            output_failed: Output file for failed designs
            vhdl_key: JSON key containing VHDL code
        """
        stats = {"total": 0, "valid": 0, "failed": 0}
        
        with open(input_file, 'r', encoding='utf-8') as fin, \
             open(output_valid, 'w', encoding='utf-8') as fout_valid, \
             open(output_failed, 'w', encoding='utf-8') as fout_failed:
            
            # Count total lines
            total_lines = sum(1 for _ in fin)
            fin.seek(0)
            
            for line in tqdm(fin, total=total_lines, desc="Validating VHDL"):
                stats["total"] += 1
                
                try:
                    entry = json.loads(line.strip())
                    
                    # Extract VHDL code
                    vhdl_text = entry.get(vhdl_key, "")
                    if not vhdl_text:
                        # Try alternative keys
                        vhdl_text = entry.get("vhdl_code", entry.get("code", ""))
                    
                    vhdl_code = self.extract_vhdl(vhdl_text)
                    
                    if not vhdl_code:
                        stats["failed"] += 1
                        entry["error"] = "No VHDL code found"
                        fout_failed.write(json.dumps(entry) + "\n")
                        continue
                    
                    # Validate
                    success, error_msg = self.validate(vhdl_code)
                    
                    if success:
                        stats["valid"] += 1
                        entry["validated"] = True
                        fout_valid.write(json.dumps(entry) + "\n")
                    else:
                        stats["failed"] += 1
                        entry["validated"] = False
                        entry["error"] = error_msg
                        fout_failed.write(json.dumps(entry) + "\n")
                
                except json.JSONDecodeError:
                    stats["failed"] += 1
                    continue
                except Exception as e:
                    stats["failed"] += 1
                    continue
        
        # Print statistics
        print(f"\n{'='*60}")
        print(f"VHDL Validation Results")
        print(f"{'='*60}")
        print(f"Total designs:     {stats['total']:>6}")
        print(f"Valid designs:     {stats['valid']:>6} ({stats['valid']/stats['total']*100:.1f}%)")
        print(f"Failed designs:    {stats['failed']:>6} ({stats['failed']/stats['total']*100:.1f}%)")
        print(f"{'='*60}")
        print(f"✅ Valid:  {output_valid}")
        print(f"❌ Failed: {output_failed}")


def main():
    parser = argparse.ArgumentParser(description="Validate VHDL designs with GHDL")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Output file for valid designs")
    parser.add_argument("--failed", "-f", required=True, help="Output file for failed designs")
    parser.add_argument("--key", "-k", default="prompt", help="JSON key containing VHDL code")
    parser.add_argument("--std", "-s", default="08", choices=["93", "02", "08"], 
                       help="VHDL standard")
    parser.add_argument("--timeout", "-t", type=int, default=10, 
                       help="Compilation timeout in seconds")
    
    args = parser.parse_args()
    
    validator = VHDLValidator(std=args.std, timeout=args.timeout)
    validator.process_jsonl(args.input, args.output, args.failed, vhdl_key=args.key)


if __name__ == "__main__":
    main()
