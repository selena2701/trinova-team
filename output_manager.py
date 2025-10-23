"""
Output Manager - Optimized Structure
Handles output management and verification only
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class OutputManager:
    
    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = base_dir
        self.metadata = {
            "timestamp_start": datetime.now().isoformat(),
            "solutions": {},
            "total_files": 0,
            "total_size_mb": 0
        }
        self._setup_directories()
    
    def _setup_directories(self):
        """Create basic directory structure"""
        for dir_path in [self.base_dir, f"{self.base_dir}/intermediate", f"{self.base_dir}/final"]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        print("Created output directories")
    
    def create_solution_folder(self, solution_number: int, solution_name: str) -> str:
        """Create folder for solution"""
        solution_folder = f"{self.base_dir}/solution_{solution_number:02d}_{solution_name.replace(' ', '_').lower()}"
        
        for subdir in [f"{solution_folder}/intermediate", f"{solution_folder}/final"]:
            Path(subdir).mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        self.metadata["solutions"][f"solution_{solution_number:02d}"] = {
            "solution_number": solution_number,
            "solution_name": solution_name,
            "folder": solution_folder,
            "timestamp_start": datetime.now().isoformat(),
            "steps": []
        }
        
        print(f"Created folder for solution {solution_number}: {solution_folder}")
        return solution_folder
    
    def create_de_folder(self, de_number: int, de_name: str) -> str:
        """Backward compatibility method"""
        return self.create_solution_folder(de_number, de_name)
    
    def save_final_file(self, file_path: str, solution_number: int, solution_name: str, file_type: str = "video") -> str:
        """Save final file to output directory"""
        solution_folder = self._get_solution_folder(solution_number)
        
        # File extensions mapping
        extensions = {"video": ".mp4", "image": ".png", "audio": ".mp3", "pdf": ".pdf", "text": ".txt"}
        ext = extensions.get(file_type, os.path.splitext(file_path)[1])
        
        # Create main filename (no timestamp for main file)
        main_filename = f"solution_{solution_number:02d}_final{ext}"
        main_path = f"{solution_folder}/final/{main_filename}"
        
        # Copy main file
        shutil.copy(file_path, main_path)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"solution_{solution_number:02d}_final_{timestamp}{ext}"
        backup_path = f"{solution_folder}/final/{backup_filename}"
        shutil.copy(file_path, backup_path)
        
        file_size = os.path.getsize(main_path)
        print(f"Saved final file ({file_type}): {main_path} ({file_size / (1024*1024):.2f} MB)")
        
        # Update metadata
        self._add_step(solution_number, {
            "name": f"Final {file_type}",
            "file": main_path,
            "backup": backup_path,
            "size_mb": file_size / (1024*1024),
            "file_type": file_type,
            "timestamp": datetime.now().isoformat()
        })
        
        self.metadata["total_files"] += 1
        self.metadata["total_size_mb"] += file_size / (1024*1024)
        
        return main_path
    
    def save_metadata(self, file_path: str, solution_number: int, solution_name: str, file_type: str = "video"):
        """Save metadata for solution"""
        solution_folder = self._get_solution_folder(solution_number)
        
        try:
            # Get file information
            file_info = self._get_file_info(file_path, file_type)
            
            # Create metadata
            metadata = {
                "solution_info": {
                    "solution_number": solution_number,
                    "solution_name": solution_name,
                    "file_type": file_type,
                    "timestamp": datetime.now().isoformat()
                },
                "file_info": file_info,
                "requirements_check": self._check_requirements(file_path, file_type)
            }
            
            # Save metadata
            metadata_path = f"{solution_folder}/final/metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"Saved metadata: {metadata_path}")
            
        except Exception as e:
            print(f"Could not get metadata: {e}")
    
    def _get_file_info(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Get file-specific information"""
        if file_type in ["video", "audio"]:
            return self._get_media_info(file_path)
        elif file_type == "image":
            return self._get_image_info(file_path)
        elif file_type == "pdf":
            return {"size_bytes": os.path.getsize(file_path), "format": "PDF"}
        elif file_type == "text":
            return self._get_text_info(file_path)
        return {}
    
    def _get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media file information using ffprobe"""
        try:
            command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return {}
    
    def _get_image_info(self, file_path: str) -> Dict[str, Any]:
        """Get image file information"""
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "size_bytes": os.path.getsize(file_path)
                }
        except Exception:
            return {"size_bytes": os.path.getsize(file_path)}
    
    def _get_text_info(self, file_path: str) -> Dict[str, Any]:
        """Get text file information"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "size_bytes": os.path.getsize(file_path),
                "char_count": len(content),
                "line_count": len(content.splitlines()),
                "encoding": "UTF-8"
            }
        except Exception:
            return {"size_bytes": os.path.getsize(file_path)}
    
    def _check_requirements(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Check technical requirements for file type"""
        base_requirements = {
            "video": {"format": "MP4", "resolution": "1920x1080", "has_audio": True},
            "image": {"format": "PNG/JPG", "resolution": "1024x1024", "quality": "high"},
            "audio": {"format": "MP3/WAV", "sample_rate": "44100Hz", "channels": "mono/stereo"},
            "pdf": {"format": "PDF", "pages": "5-10", "quality": "print_ready"},
            "text": {"format": "TXT", "encoding": "UTF-8", "length": "appropriate"}
        }
        
        requirements = base_requirements.get(file_type, {})
        
        # Add actual file verification for video
        if file_type == "video" and file_path:
            try:
                media_info = self._get_media_info(file_path)
                if media_info:
                    requirements["actual_info"] = media_info
            except Exception as e:
                requirements["verification_error"] = str(e)
        
        return requirements
    
    def _get_solution_folder(self, solution_number: int) -> str:
        """Get solution folder path"""
        solution_key = f"solution_{solution_number:02d}"
        if solution_key in self.metadata["solutions"]:
            return self.metadata["solutions"][solution_key]["folder"]
        return f"{self.base_dir}/solution_{solution_number:02d}_unknown"
    
    def _add_step(self, solution_number: int, step_info: Dict[str, Any]):
        """Add step to solution metadata"""
        solution_key = f"solution_{solution_number:02d}"
        if solution_key in self.metadata["solutions"]:
            self.metadata["solutions"][solution_key]["steps"].append(step_info)
    
    def print_summary(self, solution_number: int = None):
        """Print summary of files"""
        print("\n" + "=" * 50)
        print("OUTPUT SUMMARY")
        print("=" * 50)
        
        if solution_number:
            solution_key = f"solution_{solution_number:02d}"
            if solution_key in self.metadata["solutions"]:
                solution_info = self.metadata["solutions"][solution_key]
                print(f"\n{solution_info['folder']} (Solution {solution_number})")
                print(f"Files: {len(solution_info['steps'])}")
        else:
            print(f"Total files: {self.metadata['total_files']}")
            print(f"Total size: {self.metadata['total_size_mb']:.2f} MB")
            for solution_key, solution_info in self.metadata["solutions"].items():
                print(f"{solution_info['folder']} ({solution_info['solution_name']})")
        
        print("=" * 50)

if __name__ == "__main__":
    # Test the OutputManager
    om = OutputManager()
    solution_folder = om.create_solution_folder(1, "Test Solution")
    print(f"Created folder: {solution_folder}")
    om.print_summary(1)

