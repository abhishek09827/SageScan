import os
import sys
import shutil
import subprocess
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""
    def has_ext_modules(self):
        return True

class BuildPyCommand(build_py):
    """Custom build command to compile Go binary and inject wrapper."""
    def run(self):
        # 1. Run normal python build command
        super().run()
        
        # 2. Compile Go binary into the build folder
        build_lib = os.path.abspath(self.build_lib)
        package_dir = os.path.join(build_lib, "sagescan_engine")
        bin_dir = os.path.join(package_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        
        binary_name = "sagescan.exe" if sys.platform == "win32" else "sagescan"
        binary_path = os.path.join(bin_dir, binary_name)
        
        print(f"Compiling Go CLI into {{binary_path}}...")
        try:
            subprocess.check_call(["go", "build", "-o", binary_path, "./cmd/sagescan/main.go"])
        except subprocess.CalledProcessError as e:
            print(f"Failed to build Go binary: {{e}}")
            sys.exit(1)
        
        # 3. Copy `engine/main.py` into package so it can be located via SAGESCAN_ENGINE_PATH
        engine_main_source = os.path.join("engine", "main.py")
        engine_main_dest = os.path.join(package_dir, "main.py")
        print(f"Copying {{engine_main_source}} to {{engine_main_dest}}...")
        shutil.copy(engine_main_source, engine_main_dest)
        
        # 4. Create the wrapper script `sagescan_engine/cli.py`
        cli_script = os.path.join(package_dir, "cli.py")
        print(f"Generating Python CLI wrapper at {{cli_script}}...")
        with open(cli_script, "w") as f:
            f.write(f"""
import os
import sys
import subprocess

def run_sagescan():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    binary = "{binary_name}"
    bin_path = os.path.join(base_dir, "bin", binary)
    main_py_path = os.path.join(base_dir, "main.py")
    
    # Ensure binary exists
    if not os.path.exists(bin_path):
        print(f"Error: SageScan binary not found at {{bin_path}}", file=sys.stderr)
        sys.exit(1)

    # Force the Go binary to use this bundled python engine script
    os.environ["SAGESCAN_ENGINE_PATH"] = main_py_path
    
    # Execute the Go binary with all passed arguments
    sys.exit(subprocess.call([bin_path] + sys.argv[1:]))

if __name__ == "__main__":
    run_sagescan()
            """.strip())
            f.write("\n")

setup(
    name="sagescan-data",
    version="1.0.5",
    description="Production-grade, CLI-first data quality validation for modern data pipelines",
    author="SageScan Contributors",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=[
        "sagescan_engine", 
        "sagescan_engine.core", 
        "sagescan_engine.llm", 
        "sagescan_engine.rules", 
        "sagescan_engine.validators"
    ],
    package_dir={"sagescan_engine": "engine/sagescan_engine"},
    include_package_data=True,
    package_data={
        "sagescan_engine": ["bin/*", "main.py", "cli.py"],
    },
    entry_points={
        "console_scripts": [
            "sagescan=sagescan_engine.cli:run_sagescan",
        ],
    },
    install_requires=[
        "pydantic>=2.4.0",
        "PyYAML>=6.0.1",
        "pandas>=2.0.0",
        "rich>=13.0.0",
        "numpy>=1.26.0",
        "scipy>=1.11.0",
    ],
    extras_require={
        "all": ["pyarrow>=14.0.0", "openai>=1.0.0", "litellm>=1.0.0"],
        "parquet": ["pyarrow>=14.0.0"],
        "llm": ["openai>=1.0.0", "litellm>=1.0.0"]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    distclass=BinaryDistribution,
    cmdclass={
        "build_py": BuildPyCommand,
    },
)
