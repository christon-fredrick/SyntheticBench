# VHDL Processing Scripts

Comprehensive toolkit for processing, validating, repairing, and generating testbenches for VHDL designs.

## 📁 Scripts Overview

| Script | Purpose | Key Features |
|--------|---------|--------------|
| **vhdl_validator.py** | Validate VHDL designs with GHDL | VHDL-2008 support, batch processing, error reporting |
| **vhdl_ai_repair.py** | AI-assisted VHDL repair | DeepSeek API integration, auto-retry, checkpointing |
| **vhdl_testbench_generator.py** | Generate testbenches with AI | Two-stage generation, corner cases, self-checking TBs |
| **vhdl_simulator.py** | Simulate VHDL with GHDL | Batch simulation, waveform generation, auto-entity detection |

## 🚀 Quick Start

### 1. Validate VHDL Designs

```bash
python3 scripts/vhdl_validator.py \
    --input raw_designs.jsonl \
    --output validated_designs.jsonl \
    --failed failed_designs.jsonl
```

**Output:**
- `validated_designs.jsonl` - Successfully compiled designs
- `failed_designs.jsonl` - Failed designs with error messages

### 2. Repair Failed Designs

```bash
export DEEPSEEK_API_KEY="your_api_key"

python3 scripts/vhdl_ai_repair.py \
    --input failed_designs.jsonl \
    --output repaired_designs.jsonl \
    --still-failed still_failed.jsonl
```

**Features:**
- Automatic error repair with AI
- Hierarchical design flattening
- Up to 3 retry attempts per design
- Checkpoint/resume support

### 3. Generate Testbenches

```bash
python3 scripts/vhdl_testbench_generator.py \
    --input validated_designs.jsonl \
    --output testbench_dataset.jsonl
```

**Generates:**
- **Stage 1**: DUT → Corner Cases
- **Stage 2**: DUT + Corner Cases → Testbench

### 4. Simulate Designs

Single simulation:
```bash
python3 scripts/vhdl_simulator.py \
    --design counter.vhd \
    --testbench counter_tb.vhd \
    --wave vcd
```

Batch simulation:
```bash
python3 scripts/vhdl_simulator.py \
    --folder simulation_tests/ \
    --wave vcd
```

## 📊 Complete Pipeline Example

```bash
# Step 1: Validate designs
python3 scripts/vhdl_validator.py \
    -i raw_vhdl_designs.jsonl \
    -o valid.jsonl \
    -f failed.jsonl

# Step 2: Repair failed designs
export DEEPSEEK_API_KEY="sk-xxx"
python3 scripts/vhdl_ai_repair.py \
    -i failed.jsonl \
    -o repaired.jsonl \
    -f still_failed.jsonl

# Step 3: Combine valid + repaired
cat valid.jsonl repaired.jsonl > all_valid_designs.jsonl

# Step 4: Generate testbenches
python3 scripts/vhdl_testbench_generator.py \
    -i all_valid_designs.jsonl \
    -o dual_stage_dataset.jsonl

# Step 5: Extract and simulate (optional)
# ... extract individual files and simulate
```

## 🔧 Requirements

### System Requirements
```bash
# Install GHDL (VHDL compiler/simulator)
sudo apt update
sudo apt install ghdl

# Verify installation
ghdl --version
```

### Python Requirements
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
requests>=2.31.0
tqdm>=4.66.0
```

## 📝 Data Format

### Input Format (JSONL)

```json
{
  "prompt": "--1. VHDL design START\nlibrary ieee;\nuse ieee.std_logic_1164.all;\n...\n-- END of VHDL Design",
  "source": "dataset_name",
  "metadata": {...}
}
```

Alternative keys supported: `vhdl_code`, `code`

### Output Formats

**Validated Designs:**
```json
{
  "prompt": "...",
  "validated": true,
  "source": "..."
}
```

**Failed Designs:**
```json
{
  "prompt": "...",
  "validated": false,
  "error": "ghdl error message...",
  "source": "..."
}
```

**Repaired Designs:**
```json
{
  "original_code": "...",
  "original_error": "...",
  "repaired_code": "...",
  "repair_attempts": 2,
  "source": "..."
}
```

**Dual-Stage Testbench Dataset:**
```json
{
  "stage": 1,
  "entity": "counter",
  "messages": [
    {"role": "user", "content": "counter VHDL Design:\n..."},
    {"role": "assistant", "content": "Corner cases:\n1. Reset...\n2. Overflow..."}
  ]
}
{
  "stage": 2,
  "entity": "counter",
  "testbench_entity": "counter_tb",
  "messages": [
    {"role": "user", "content": "counter VHDL Design:\n...\n\nCorner Cases:\n..."},
    {"role": "assistant", "content": "library ieee;\n...testbench code..."}
  ]
}
```

## 🎯 Script Details

### vhdl_validator.py

**Purpose:** Validate VHDL designs with GHDL compiler

**Options:**
```bash
--input, -i      Input JSONL file
--output, -o     Output file for valid designs
--failed, -f     Output file for failed designs
--key, -k        JSON key containing VHDL (default: "prompt")
--std, -s        VHDL standard: 93, 02, 08 (default: 08)
--timeout, -t    Compilation timeout in seconds (default: 10)
```

**Features:**
- Automatic VHDL extraction from markers
- GHDL-2008 compilation
- Detailed error messages
- Progress bar with tqdm
- Summary statistics

---

### vhdl_ai_repair.py

**Purpose:** AI-assisted repair of failed VHDL designs

**Options:**
```bash
--input, -i          Input JSONL with failed designs
--output, -o         Output file for repaired designs
--still-failed, -f   Output file for still-failed designs
--api-key            API key (or DEEPSEEK_API_KEY env var)
--api-url            API endpoint (default: DeepSeek)
--model              Model name (default: deepseek-chat)
--max-retries        Max repair attempts (default: 3)
--std, -s            VHDL standard (default: 08)
--checkpoint         Checkpoint file (default: repair_checkpoint.json)
```

**AI Repair Strategy:**
1. Send original code + error to AI
2. AI fixes syntax/compilation errors
3. AI flattens hierarchical designs if needed
4. Validate repaired code with GHDL
5. Retry up to max_retries times

**Checkpoint System:**
- Saves progress after each design
- Resume from checkpoint on restart
- Handles API errors gracefully

---

### vhdl_testbench_generator.py

**Purpose:** Generate comprehensive testbenches with AI

**Options:**
```bash
--input, -i      Input JSONL with validated designs
--output, -o     Output JSONL with dual-stage dataset
--api-key        API key (or DEEPSEEK_API_KEY env var)
--api-url        API endpoint (default: DeepSeek)
--model          Model name (default: deepseek-chat)
--std, -s        VHDL standard (default: 08)
```

**Two-Stage Process:**
1. **Stage 1:** Generate corner cases
   - AI identifies edge cases for design
   - Boundary conditions, reset behaviors, overflows
2. **Stage 2:** Generate testbench
   - Self-checking testbench with assertions
   - Covers all Stage 1 corner cases
   - Validated with GHDL

**Prompt Variation:**
- Multiple prompt templates for diversity
- Random selection per design
- Improves dataset variety

---

### vhdl_simulator.py

**Purpose:** Simulate VHDL designs with GHDL

**Options:**
```bash
--design, -d      Design VHDL file
--testbench, -t   Testbench VHDL file
--folder, -f      Folder with design+testbench pairs
--std, -s         VHDL standard (default: 08)
--wave, -w        Generate waveform (vcd or ghw)
```

**Simulation Process:**
1. Extract entity names from files
2. Analyze design with `ghdl -a`
3. Analyze testbench with `ghdl -a`
4. Elaborate with `ghdl -e`
5. Run simulation with `ghdl -r`
6. Optional: Generate VCD/GHW waveforms

**Batch Mode:**
- Processes all .vhd files in folder
- Auto-matches designs with testbenches
- Summary statistics

## 🔍 Troubleshooting

### GHDL Not Found
```bash
sudo apt update
sudo apt install ghdl
```

### API Rate Limits
- Use checkpoint system to resume
- Implement exponential backoff
- Consider using different API keys

### Memory Issues
- Process files in smaller batches
- Use `--max-retries 1` for faster processing
- Clear GHDL work library periodically

### Validation Failures
- Check VHDL standard compatibility
- Verify library dependencies
- Review GHDL error messages in failed.jsonl

## 📈 Performance Tips

1. **Parallel Processing:** Run multiple validators on split files
2. **Batch Size:** Process 1000-5000 designs per run
3. **Checkpoints:** Enable for long-running operations
4. **API Optimization:** Use higher temperature for diverse outputs

## 🤝 Contributing

Improvements welcome:
- Additional AI model support (OpenAI, Anthropic)
- More validation tools (ModelSim, Vivado)
- Enhanced error categorization
- Performance optimizations

## 📄 License

See main repository LICENSE file.

## 📧 Support

For issues or questions about these scripts, please open an issue in the repository.

---

**Last Updated:** January 5, 2026
