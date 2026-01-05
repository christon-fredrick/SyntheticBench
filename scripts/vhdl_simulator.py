#!/usr/bin/env python3
"""
VHDL GHDL Simulator

Simulates VHDL designs and testbenches using GHDL.
Supports batch processing of design+testbench pairs.

Features:
- Automatic design and testbench compilation
- Entity name extraction
- Elaboration and simulation
- Waveform generation (optional)
- Batch processing support

Usage:
    python3 vhdl_simulator.py --design design.vhd --testbench tb.vhd
    python3 vhdl_simulator.py --folder simulation_tests/
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple


class VHDLSimulator:
    """GHDL-based VHDL simulator."""
    
    def __init__(self, std: str = "08", wave_format: Optional[str] = None):
        """
        Initialize simulator.
        
        Args:
            std: VHDL standard (93, 02, 08)
            wave_format: Waveform format (vcd, ghw, None)
        """
        self.std = std
        self.wave_format = wave_format
        self._check_ghdl()
    
    def _check_ghdl(self):
        """Verify GHDL is installed."""
        try:
            subprocess.run(["ghdl", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("GHDL not found. Install with: sudo apt install ghdl")
    
    def extract_entity_name(self, vhdl_file: Path) -> Optional[str]:
        """Extract entity name from VHDL file."""
        try:
            with open(vhdl_file, 'r') as f:
                content = f.read()
                match = re.search(r'\bentity\s+(\w+)\s+is', content, re.IGNORECASE)
                return match.group(1) if match else None
        except Exception:
            return None
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Run shell command.
        
        Args:
            cmd: Command and arguments
            cwd: Working directory
            
        Returns:
            Tuple of (success, output)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = result.returncode == 0
            output = (result.stdout + result.stderr).strip()
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)
    
    def simulate(self, design_file: Path, testbench_file: Path, 
                 output_dir: Optional[Path] = None) -> bool:
        """
        Simulate design with testbench.
        
        Args:
            design_file: Path to design VHDL file
            testbench_file: Path to testbench VHDL file
            output_dir: Optional output directory for waveforms
            
        Returns:
            True if simulation successful
        """
        if not design_file.exists() or not testbench_file.exists():
            print(f"❌ Files not found")
            return False
        
        # Extract entity names
        design_entity = self.extract_entity_name(design_file)
        tb_entity = self.extract_entity_name(testbench_file)
        
        if not design_entity or not tb_entity:
            print(f"❌ Could not extract entity names")
            return False
        
        print(f"🚀 Simulating: {design_entity} with {tb_entity}")
        
        # Step 1: Analyze design
        print(f"   → Analyzing design: {design_file.name}")
        success, output = self.run_command([
            "ghdl", "-a", f"--std={self.std}", str(design_file)
        ])
        
        if not success:
            print(f"❌ Design analysis failed:\n{output}")
            return False
        
        # Step 2: Analyze testbench
        print(f"   → Analyzing testbench: {testbench_file.name}")
        success, output = self.run_command([
            "ghdl", "-a", f"--std={self.std}", str(testbench_file)
        ])
        
        if not success:
            print(f"❌ Testbench analysis failed:\n{output}")
            return False
        
        # Step 3: Elaborate
        print(f"   → Elaborating: {tb_entity}")
        success, output = self.run_command([
            "ghdl", "-e", f"--std={self.std}", tb_entity
        ])
        
        if not success:
            print(f"❌ Elaboration failed:\n{output}")
            return False
        
        # Step 4: Run simulation
        run_cmd = ["ghdl", "-r", f"--std={self.std}", tb_entity]
        
        if self.wave_format:
            wave_file = output_dir / f"{tb_entity}.{self.wave_format}" if output_dir else f"{tb_entity}.{self.wave_format}"
            if self.wave_format == "vcd":
                run_cmd.extend([f"--vcd={wave_file}"])
            elif self.wave_format == "ghw":
                run_cmd.extend([f"--wave={wave_file}"])
        
        print(f"   → Running simulation...")
        success, output = self.run_command(run_cmd)
        
        if success:
            print(f"✅ Simulation successful")
            if output:
                print(f"   Output:\n{output}")
            return True
        else:
            print(f"❌ Simulation failed:\n{output}")
            return False
    
    def simulate_folder(self, folder: Path) -> dict:
        """
        Simulate all design+testbench pairs in folder.
        
        Args:
            folder: Folder containing VHDL files
            
        Returns:
            Dictionary with simulation statistics
        """
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")
        
        # Find VHDL files
        vhdl_files = list(folder.glob("*.vhd"))
        design_files = [f for f in vhdl_files if not re.search(r'(tb|testbench)', f.name, re.IGNORECASE)]
        tb_files = [f for f in vhdl_files if re.search(r'(tb|testbench)', f.name, re.IGNORECASE)]
        
        if not design_files or not tb_files:
            print(f"❌ No design or testbench files found in {folder}")
            return {"total": 0, "success": 0, "failed": 0}
        
        stats = {"total": len(design_files), "success": 0, "failed": 0}
        
        print(f"\n{'='*60}")
        print(f"Simulating folder: {folder}")
        print(f"{'='*60}")
        
        for design_file in design_files:
            # Find matching testbench
            design_entity = self.extract_entity_name(design_file)
            if not design_entity:
                stats["failed"] += 1
                continue
            
            # Look for testbench with matching name
            tb_file = None
            for tb in tb_files:
                if design_entity.lower() in tb.name.lower():
                    tb_file = tb
                    break
            
            if not tb_file and tb_files:
                tb_file = tb_files[0]  # Use first testbench
            
            if tb_file:
                success = self.simulate(design_file, tb_file, folder)
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            else:
                print(f"❌ No testbench found for {design_file.name}")
                stats["failed"] += 1
            
            print()
        
        print(f"{'='*60}")
        print(f"Simulation Summary")
        print(f"{'='*60}")
        print(f"Total:     {stats['total']:>3}")
        print(f"Success:   {stats['success']:>3}")
        print(f"Failed:    {stats['failed']:>3}")
        print(f"{'='*60}")
        
        return stats


def main():
    parser = argparse.ArgumentParser(description="VHDL GHDL simulator")
    parser.add_argument("--design", "-d", type=Path, help="Design VHDL file")
    parser.add_argument("--testbench", "-t", type=Path, help="Testbench VHDL file")
    parser.add_argument("--folder", "-f", type=Path, help="Folder with design+testbench pairs")
    parser.add_argument("--std", "-s", default="08", choices=["93", "02", "08"], 
                       help="VHDL standard")
    parser.add_argument("--wave", "-w", choices=["vcd", "ghw"], 
                       help="Generate waveform file")
    
    args = parser.parse_args()
    
    simulator = VHDLSimulator(std=args.std, wave_format=args.wave)
    
    if args.folder:
        simulator.simulate_folder(args.folder)
    elif args.design and args.testbench:
        simulator.simulate(args.design, args.testbench)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
