import time
import sys
import os
from typing import Callable
import logging

# Mute all internal SageScan warnings to prevent pollution in asciinema
logging.getLogger().setLevel(logging.CRITICAL)

# Ensure we use the proper local paths
sys.path.insert(0, os.path.abspath("engine"))

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import subprocess
import yaml

from sagescan_engine.core.runner import run_generate_rules, run_report
from sagescan_engine.llm.rule_generator import LLMRuleGenerator

console = Console()

def type_text(text: str, speed: float = 0.05, prompt: str = "(build_env) PS E:\Personal Projects\SageScan> "):
    """Simulate realistic typing."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    time.sleep(0.5)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    time.sleep(0.3)
    sys.stdout.write("\n")
    sys.stdout.flush()

def fake_pip_install():
    type_text("pip install sagescan-data[all]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Downloading sagescan-data...", total=100)
        while not progress.finished:
            progress.update(task, advance=2)
            time.sleep(0.05)
        
        task2 = progress.add_task("[green]Installing dependencies...", total=100)
        while not progress.finished:
            progress.update(task2, advance=3)
            time.sleep(0.04)
            
    console.print("Successfully installed sagescan-data-1.0.5 pydantic pyyaml pandas scipy numpy rich openai")
    console.print()

def real_generate_rules():
    cmd = "sagescan generate-rules -i examples/data/taxi_jan2024.parquet -o examples/rules/taxi_llm_rules.yaml --context 'NYC taxi trip data' --llm-model gpt-4o"
    type_text(cmd, speed=0.03)
    
    console.print("🤖 Generating validation rules from: examples/data/taxi_jan2024.parquet")
    console.print("🔧 Context: NYC TAXI TRIP DATA")
    console.print("📁 Output:  examples/rules/taxi_llm_rules.yaml")
    console.print("🧠 Model:   gpt-4o")
    console.print("────────────────────────────────────────────────────────────")
    
    with console.status("[cyan]Reading 3 Million rows and prompting OpenAI...", spinner="bouncingBar"):
        # Actually run the code!
        config = {
            "source": {"type": "parquet", "path": "examples/data/taxi_jan2024.parquet"},
            "context": "NYC taxi trip data",
            "output_file": "examples/rules/taxi_llm_rules.yaml",
            "llm_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "llm_model": "gpt-4o",
        }
        res = run_generate_rules(config)
    
    msg = res.get("summary", {}).get("message", "Error generating rules.")
    console.print("✓ Rules generation completed")
    console.print(f"✅ {msg}")
    console.print()

def real_report():
    cmd = "sagescan report examples/rules/taxi_llm_rules.yaml"
    type_text(cmd, speed=0.05)
    
    console.print("📄 Generating report from: examples/rules/taxi_llm_rules.yaml")
    console.print("🔧 Context: NYC TAXI TRIP DATA")
    console.print("────────────────────────────────────────────────────────────")
    
    with console.status("[magenta]Validating dataset against 17 AI rules...", spinner="dots"):
        with open("examples/rules/taxi_llm_rules.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        res = run_report(config)
    
    console.print("✓ Report generation completed")
    
    # Extract the beautifully rendered ANSI tables we built
    msg = res.get("summary", {}).get("message", "")
    report_text = msg.replace("Report generated:\n\n", "")
    
    # Print the raw rich ansi text directly to terminal
    sys.stdout.write(report_text)
    sys.stdout.write("\n")
    sys.stdout.flush()

def main():
    os.system("cls" if os.name == "nt" else "clear")
    time.sleep(1)
    
    fake_pip_install()
    time.sleep(2)
    
    os.system("cls" if os.name == "nt" else "clear")
    real_generate_rules()
    time.sleep(3)
    
    os.system("cls" if os.name == "nt" else "clear")
    real_report()
    
    console.print("\n[bold green]DEMO COMPLETE! Stop your screen recorder.[/bold green]")

if __name__ == "__main__":
    main()
