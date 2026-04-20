"""
Hardwareless AI — Model Conversion Utilities
Convert between model formats (GGUF ↔ CTranslate2 ↔ PyTorch).
"""
import os
import subprocess
from pathlib import Path
from typing import Optional


class ModelConverter:
    """
    Convert models between inference formats.
    Supported paths:
      GGUF (llama.cpp) → CTranslate2 (int8 float16)
      PyTorch (HuggingFace) → CTranslate2
      PyTorch → GGUF (via llama.cpp convert script)
    """
    
    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """Check which conversion tools are installed."""
        tools = {
            "ctranslate2": False,
            "transformers": False,
            "llama_cpp": False,
        }
        try:
            import ctranslate2
            tools["ctranslate2"] = True
        except ImportError:
            pass
        try:
            import transformers
            tools["transformers"] = True
        except ImportError:
            pass
        try:
            import llama_cpp
            tools["llama_cpp"] = True
        except ImportError:
            pass
        return tools
    
    @staticmethod
    def gguf_to_ctranslate2(
        gguf_path: str,
        output_dir: str,
        quantization: str = "int8"
    ) -> bool:
        """
        Convert a GGUF model to CTranslate2 format.
        Note: This requires the original PyTorch model or uses an intermediate conversion.
        Currently, there's no direct GGUF→CT2 converter. You'd need the original HF model.
        
        This stub records the intent and recommended path.
        """
        print(
            f"WARNING: Direct GGUF→CTranslate2 conversion is not supported.\n"
            f"To use CTranslate2 backend, you need the original PyTorch model.\n"
            f"Recommended steps:\n"
            f"  1. Download original Qwen2.5-7B from HuggingFace (~14GB)\n"
            f"  2. Run: ctranslate2-converter --model /path/to/qwen2.5-7b --quantization {quantization}\n"
            f"  3. Set QWEN_MODEL_PATH to the converted directory"
        )
        return False
    
    @staticmethod
    def pytorch_to_ctranslate2(
        pytorch_model_dir: str,
        output_dir: str,
        quantization: str = "int8",
        force: bool = False
    ) -> bool:
        """
        Convert a PyTorch HuggingFace model to CTranslate2 format.
        """
        try:
            import ctranslate2
        except ImportError:
            print("ERROR: ctranslate2 not installed. pip install ctranslate2")
            return False
        
        output_path = Path(output_dir)
        if output_path.exists() and not force:
            print(f"Output dir {output_dir} already exists. Use force=True to overwrite.")
            return False
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "ctranslate2-converter",
            "--model", pytorch_model_dir,
            "--output_dir", output_dir,
            "--quantization", quantization
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Conversion failed:\n{result.stderr}")
            return False
        
        print(f"Conversion successful. Model saved to {output_dir}")
        return True
    
    @staticmethod
    def pytorch_to_gguf(
        pytorch_model_dir: str,
        output_path: str,
        quantization: str = "q4_k_m"
    ) -> bool:
        """
        Convert PyTorch model to GGUF format using llama.cpp convert script.
        Requires llama.cpp repository with convert.py.
        """
        # Implementation would require llama.cpp convert script
        print(
            "PyTorch→GGUF conversion requires llama.cpp's convert.py.\n"
            "Steps:\n"
            "  1. Clone https://github.com/ggerganov/llama.cpp\n"
            "  2. python3 llama.cpp/convert.py --model_dir <pytorch_dir> --outfile <output.gguf>"
        )
        return False
