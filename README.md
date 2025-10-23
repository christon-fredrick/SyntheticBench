# Synthetic VHDL Testbench Dataset

## Overview
This repository contains a **synthetic dataset** of VHDL design and testbench pairs, derived from 
[`rtl-llm/vhdl_github_deduplicated`](https://huggingface.co/datasets/rtl-llm/vhdl_github_deduplicated) 
and extended with **synthetic testbenches** generated using **DeepSeek-V3** and validated to be simulatable using **GHDL**.  

The dataset is intended for **LLM fine-tuning** and **digital design verification** research.

The VHDL designs are given in two kinds of dataset for comparitative analysis. 
- **Single-stage prompt Dataset** - This contains all the VHDL design and its VHDL testbench alone.
- **Dual-stage prompt Dataset** - This contains VHDL designs + Corner cases and VHDL testbench as the output for training LLMs for the generation of VHDL testbench for a given VHDL design.

---

## Contents
- Cleaned VHDL-only subset (Verilog removed)
- Synthetic testbenches for each VHDL entity
- JSONL entries containing:
- **Single-stage prompt**
  - `dut_code`: Original VHDL design
  - `tb_code`: DeepSeek-generated testbench
- **Dual-stage prompt**
  - `dut_code`: Original VHDL design
  - `corner_cases` : Corner-cases for functional coverage
  - `tb_code`: DeepSeek-generated testbench
---

## Example Entry

**1.Single-stage prompt and 2.Dual-stage prompt**
```json
{
  prompt: "dut_code": "-- VHDL entity code here",
  response: "tb_code": "-- Corresponding synthetic testbench here",
  }


{
 {
  prompt: "dut_code": "-- VHDL entity code here",
  response: "corner_cases": "-- Corresponding relevant corner cases for coverage",
  }
{
  prompt: "dut_code + corner_cases"
  response: "tb_code": "-- Corresponding synthetic testbench here"
}
}




