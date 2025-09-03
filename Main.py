import subprocess
import json
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from tkinter.simpledialog import askstring
from tkinter.messagebox import askyesno
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# Metadata category descriptions
METADATA_INFO = {
    "EXIF": "Camera technical data (ISO, shutter speed, aperture, GPS, lens)",
    "IPTC": "Editorial/news metadata (headline, caption, keywords, byline)",
    "XMP": "Modern extensible metadata (description, title, creator, rights)"
}

METADATA_DETAILED = """
• EXIF: Camera settings, GPS location, date/time, equipment details
• IPTC: Professional photography, journalism, stock photos, archiving
• XMP: Most flexible format, Adobe standard, web publishing, DAM systems

Common fields by category:
- EXIF: Make, Model, ISO, FNumber, ExposureTime, GPS coords
- IPTC: Headline, Caption, Keywords, Credit, Source, Copyright
- XMP: Title, Description, Creator, Rights, Subject, Rating
"""

class ExifToolManager:
    """ExifTool wrapper with JSON backup and batch operations"""
    
    def __init__(self, exiftool_path: str = "exiftool"):
        self.exiftool_path = exiftool_path
        self.verify_installation()
        self.field_to_category = {
            'Make': 'EXIF',
            'Model': 'EXIF',
            'ISO': 'EXIF',
            'FNumber': 'EXIF',
            'ExposureTime': 'EXIF',
            'GPSCoordinates': '',
            'GPSPosition': '',
            'Headline': 'IPTC',
            'Caption-Abstract': 'IPTC',
            'Keywords': 'IPTC',
            'Credit': 'IPTC',
            'Source': 'IPTC',
            'Copyright': 'EXIF',
            'CopyrightNotice': 'IPTC',
            'Title': 'XMP',
            'Description': 'XMP',
            'Creator': 'XMP',
            'Rights': 'XMP',
            'Subject': 'XMP',
            'Rating': 'XMP',
            'Artist': 'EXIF',
        }
        
    def verify_installation(self) -> bool:
        try:
            result = subprocess.run([self.exiftool_path, "-ver"], capture_output=True, text=True, check=True)
            self.version = result.stdout.strip()
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"ExifTool not found at: {self.exiftool_path}")
    
    def backup_metadata_json(self, file_path: str, is_bulk: bool = False, bulk_name: str = None) -> str:
        """Backup metadata to JSON instead of copying files"""
        backup_dir = Path("./Backup")
        backup_dir.mkdir(exist_ok=True)
        
        try:
            # Get metadata for backup
            metadata = self.get_all_metadata(file_path)
            
            if is_bulk and bulk_name:
                # For bulk operations, organize by operation name
                bulk_dir = backup_dir / f"{bulk_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                bulk_dir.mkdir(exist_ok=True)
                
                # Preserve folder structure in backup
                rel_path = Path(file_path).relative_to(Path(file_path).parent.parent) if Path(file_path).parent.parent.exists() else Path(file_path).name
                backup_path = bulk_dir / f"{rel_path.stem}_metadata.json"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # For single file operations
                backup_path = backup_dir / f"{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_metadata.json"
            
            # Save metadata with file path reference
            backup_data = {
                "original_file": str(file_path),
                "backup_date": datetime.now().isoformat(),
                "metadata": metadata
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            return str(backup_path)
        except Exception as e:
            # Fallback to empty backup if metadata read fails
            return ""
    
    def restore_metadata_from_json(self, json_path: str, target_file: str = None) -> bool:
        """Restore metadata from JSON backup"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            if not target_file:
                target_file = backup_data.get("original_file")
            
            if not target_file or not os.path.exists(target_file):
                raise RuntimeError("Target file not found")
            
            metadata = backup_data.get("metadata", {})
            
            # Restore each metadata field
            for key, value in metadata.items():
                if key not in ["SourceFile", "FileName", "Directory", "FileSize", "FileModifyDate"]:
                    try:
                        self.add_or_edit_metadata(target_file, key, str(value), backup=False)
                    except:
                        continue
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to restore metadata: {str(e)}")
    
    def add_or_edit_metadata(self, file_path: str, field: str, value: str, category: str = "", backup: bool = True) -> bool:
        if backup:
            self.backup_metadata_json(file_path)
        
        try:
            field = field.strip().replace(" ", "")
            
            if not category:
                category = self.field_to_category.get(field, '')
            
            # Special adjustments
            if field == 'GPSCoordinates':
                field = 'GPSPosition'
                category = ''
            if field == 'Copyright' and category == 'IPTC':
                field = 'CopyrightNotice'
            
            if len(value) > 10000:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp:
                    temp.write(value)
                    temp_path = temp.name
                tag = f"-{category}:{field}<={temp_path}" if category else f"-{field}<={temp_path}"
            else:
                escaped_value = value.replace('"', '\\"').replace('\\', '\\\\')
                tag = f"-{category}:{field}={escaped_value}" if category else f"-{field}={escaped_value}"
            
            cmd = [self.exiftool_path, "-overwrite_original", "-charset", "utf8", "-api", "largefilesupport=1", tag, file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if len(value) > 10000:
                os.unlink(temp_path)
            
            if result.returncode == 0:
                return "1 image files updated" in result.stdout
            else:
                error_msg = result.stderr.strip()
                if "not writable" in error_msg.lower():
                    raise RuntimeError(f"Field '{field}' is not writable. Try using 'Description' or 'Title'.")
                else:
                    raise RuntimeError(f"ExifTool failed: {error_msg}")
                    
        except Exception as e:
            raise RuntimeError(f"Error: {str(e)}")
    
    def delete_metadata(self, file_path: str, field: str, category: str = "", backup: bool = True) -> bool:
        if backup:
            self.backup_metadata_json(file_path)
        
        try:
            field = field.strip().replace(" ", "")
            
            if not category:
                category = self.field_to_category.get(field, '')
            
            # Special adjustments
            if field == 'GPSCoordinates':
                field = 'GPSPosition'
                category = ''
            if field == 'Copyright' and category == 'IPTC':
                field = 'CopyrightNotice'
            
            tag = f"-{category}:{field}=" if category else f"-{field}="
            cmd = [self.exiftool_path, "-overwrite_original", tag, file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                return "1 image files updated" in result.stdout
            else:
                raise RuntimeError(f"Failed to delete field: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Error: {str(e)}")
    
    def make_social_media_ready(self, file_path: str, backup: bool = True) -> bool:
        if backup:
            self.backup_metadata_json(file_path)
        
        try:
            cmd = [
                self.exiftool_path, "-overwrite_original",
                "-gps:all=", "-exif:make=", "-exif:model=", "-exif:serialnumber=",
                "-exif:usercomment=", "-exif:makernotes=", "-xmp:creatortool=",
                "-iptc:by-line=", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode == 0 or "files updated" in result.stdout
        except Exception as e:
            raise RuntimeError(f"Error: {str(e)}")
    
    def wipe_all_metadata(self, file_path: str, backup: bool = True) -> bool:
        if backup:
            self.backup_metadata_json(file_path)
        
        try:
            cmd = [self.exiftool_path, "-overwrite_original", "-all=", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode == 0 or "files updated" in result.stdout
        except Exception as e:
            return False
    
    def get_all_metadata(self, file_path: str) -> Dict[str, Any]:
        try:
            cmd = [self.exiftool_path, "-json", "-all", "-duplicates", "-charset", "utf8", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)[0]
        except Exception as e:
            raise RuntimeError(f"Failed to read metadata: {str(e)}")
    
    def batch_operation(self, file_list: List[str], operation: callable, args: Dict[str, Any] = {}, 
                       progress_callback: Optional[callable] = None, bulk_name: str = None) -> Dict[str, bool]:
        results = {}
        total = len(file_list)
        max_workers = min(os.cpu_count() * 2, 16)
        
        # Setup bulk backup directory if needed
        if args.get('backup', True) and bulk_name:
            backup_dir = Path("./Backup")
            backup_dir.mkdir(exist_ok=True)
            bulk_dir = backup_dir / f"{bulk_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            bulk_dir.mkdir(exist_ok=True)
            
            # Create a manifest file for bulk operation
            manifest = {
                "operation": operation.__name__,
                "timestamp": datetime.now().isoformat(),
                "total_files": total,
                "files": []
            }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(operation, file, **args): file for file in file_list}
            for i, future in enumerate(as_completed(futures)):
                file = futures[future]
                try:
                    results[file] = future.result()
                    if args.get('backup', True) and bulk_name:
                        manifest["files"].append({"file": file, "success": True})
                except Exception as e:
                    results[file] = False
                    if args.get('backup', True) and bulk_name:
                        manifest["files"].append({"file": file, "success": False, "error": str(e)})
                if progress_callback:
                    progress_callback(i + 1, total, file)
        
        # Save manifest for bulk operations
        if args.get('backup', True) and bulk_name:
            manifest_path = bulk_dir / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        
        return results

class FullScreenMetadataViewer:
    """Full screen metadata viewer with small image preview"""
    
    def __init__(self, parent, file_path, exif_manager):
        self.viewer = tk.Toplevel(parent)
        self.viewer.title(f"Metadata Viewer - {os.path.basename(file_path)}")
        self.viewer.state('zoomed')  # Full screen
        self.file_path = file_path
        self.exif = exif_manager
        
        self.setup_ui()
        self.load_metadata()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.viewer)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top bar with image preview and file info
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Small image preview
        preview_frame = ttk.LabelFrame(top_frame, text="Preview")
        preview_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, width=150, height=150, bg="gray90")
        self.preview_canvas.pack(padx=5, pady=5)
        self.load_preview()
        
        # File info
        info_frame = ttk.LabelFrame(top_frame, text="File Information")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.info_label = ttk.Label(info_frame, text="", font=("Courier", 10))
        self.info_label.pack(padx=10, pady=10, anchor=tk.W)
        
        # Control buttons
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Button(btn_frame, text="Refresh", command=self.load_metadata).pack(pady=2)
        ttk.Button(btn_frame, text="Export JSON", command=self.export_json).pack(pady=2)
        ttk.Button(btn_frame, text="Close", command=self.viewer.destroy).pack(pady=2)
        
        # Metadata display
        meta_frame = ttk.LabelFrame(main_frame, text="Metadata")
        meta_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search bar
        search_frame = ttk.Frame(meta_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_metadata)
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT)
        
        # Metadata text with scrollbar
        text_frame = ttk.Frame(meta_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.meta_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier", 10))
        self.meta_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, pady=(5, 0))
    
    def load_preview(self):
        self.preview_canvas.delete("all")
        
        if Image is None:
            self.preview_canvas.create_text(75, 75, text="No preview", font=("Arial", 9), fill="gray")
            return
        
        try:
            with Image.open(self.file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.preview_canvas.create_image(75, 75, image=photo)
                self.preview_canvas.image = photo
        except Exception as e:
            self.preview_canvas.create_text(75, 75, text="Preview error", font=("Arial", 9), fill="red")
    
    def load_metadata(self):
        try:
            # Update file info
            file_stat = os.stat(self.file_path)
            info_text = f"Path: {self.file_path}\n"
            info_text += f"Size: {file_stat.st_size / 1024:.2f} KB\n"
            info_text += f"Modified: {datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
            self.info_label.config(text=info_text)
            
            # Load metadata
            self.metadata = self.exif.get_all_metadata(self.file_path)
            self.display_metadata(self.metadata)
            self.status_label.config(text=f"Loaded {len(self.metadata)} metadata fields")
        except Exception as e:
            self.meta_text.delete("1.0", tk.END)
            self.meta_text.insert(tk.END, f"Error loading metadata: {str(e)}")
            self.status_label.config(text="Error loading metadata")
    
    def display_metadata(self, metadata):
        self.meta_text.delete("1.0", tk.END)
        formatted = json.dumps(metadata, indent=2, ensure_ascii=False)
        self.meta_text.insert(tk.END, formatted)
    
    def filter_metadata(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.display_metadata(self.metadata)
            return
        
        filtered = {k: v for k, v in self.metadata.items() 
                   if search_term in k.lower() or search_term in str(v).lower()}
        self.display_metadata(filtered)
        self.status_label.config(text=f"Showing {len(filtered)} of {len(self.metadata)} fields")
    
    def export_json(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{Path(self.file_path).stem}_metadata.json"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Metadata exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

class MetadataManagerGUI:
    def __init__(self, master):
        self.master = master
        master.title("Image Metadata Manager v1.0")
        master.geometry("1200x700")
        
        # Create About info
        self.about_text = (
        "Image Metadata Manager v1.0 is a professional tool for managing EXIF, IPTC, and XMP metadata. The project is open-source under the MIT license and available at GitHub https://github.com/official-imvoiid/Image-Metadata-Manager"
        )
        
        try:
            self.exif = ExifToolManager()
        except RuntimeError as e:
            messagebox.showerror("ExifTool Error", str(e))
            master.quit()
            return
            
        self.image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
        self.setup_gui()
        self.setup_menu()
        
    def setup_menu(self):
        """Setup menu bar with About option"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        menubar.add_command(label="About", command=self.show_about)
        
    def show_about(self):
        """Show About dialog"""
        messagebox.showinfo("About", self.about_text)
        
    def setup_gui(self):
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Single mode tab 
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="Single File")
        self.setup_single_mode()
        
        # Bulk mode tab
        self.bulk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.bulk_frame, text="Bulk Operations")
        self.setup_bulk_mode()
    
    def setup_single_mode(self):
        # File selection
        select_frame = ttk.LabelFrame(self.single_frame, text="File Selection")
        select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.single_path_var = tk.StringVar()
        ttk.Entry(select_frame, textvariable=self.single_path_var, width=80).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        ttk.Button(select_frame, text="Browse", command=self.select_single_file).pack(side=tk.LEFT, padx=5)
        
        # Content frame
        content_frame = ttk.Frame(self.single_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Preview
        preview_frame = ttk.LabelFrame(content_frame, text="Preview")
        preview_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        self.preview_canvas = tk.Canvas(preview_frame, width=300, height=300, bg="gray90")
        self.preview_canvas.pack(padx=5, pady=5)
        
        # Metadata and controls
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Metadata info panel
        info_frame = ttk.LabelFrame(right_frame, text="Metadata Categories", padding=5)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        info_label = ttk.Label(info_frame, text=METADATA_DETAILED, font=("Arial", 9), justify=tk.LEFT)
        info_label.pack(padx=5, pady=5)
        
        # Metadata display
        meta_frame = ttk.LabelFrame(right_frame, text="Metadata")
        meta_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.single_meta_text = scrolledtext.ScrolledText(meta_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.single_meta_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X)
        
        buttons = [
            ("View Metadata", self.single_view_metadata),
            ("Add/Modify", self.single_add_edit),
            ("Delete Field", self.single_delete),
            ("Social Media Ready", self.single_social_media_ready),
            ("Wipe All", self.single_wipe_all)
        ]
        
        for i, (text, command) in enumerate(buttons):
            ttk.Button(btn_frame, text=text, command=command).grid(row=i//3, column=i%3, padx=2, pady=2, sticky="ew")
        
        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
    
    def setup_bulk_mode(self):
        # Folder selection
        select_frame = ttk.LabelFrame(self.bulk_frame, text="Folder Selection")
        select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        folder_frame = ttk.Frame(select_frame)
        folder_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.bulk_path_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.bulk_path_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.select_bulk_folder).pack(side=tk.LEFT, padx=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(select_frame, text="Include Subfolders", variable=self.recursive_var, command=self.load_bulk_files).pack()
        
        # File list and operations
        content_frame = ttk.Frame(self.bulk_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # File tree with selection controls
        tree_frame = ttk.LabelFrame(content_frame, text="Files")
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Selection controls
        select_controls = ttk.Frame(tree_frame)
        select_controls.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(select_controls, text="Select All", command=self.select_all_files, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(select_controls, text="Select None", command=self.select_none_files, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(select_controls, text="Invert", command=self.invert_selection, width=12).pack(side=tk.LEFT, padx=2)
        
        self.selected_count_label = ttk.Label(select_controls, text="0 selected", foreground="green", font=("Arial", 9, "bold"))
        self.selected_count_label.pack(side=tk.RIGHT, padx=5)
        
        # File tree
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.file_tree = ttk.Treeview(tree_container, columns=("Selected", "Size"), show="tree headings")
        self.file_tree.heading("#0", text="Name")
        self.file_tree.heading("Selected", text="✓")
        self.file_tree.heading("Size", text="Size")
        self.file_tree.column("#0", width=250)
        self.file_tree.column("Selected", width=50, anchor="center")  # Centered column
        self.file_tree.column("Size", width=80)
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.file_tree.bind("<Button-1>", self.on_tree_click)
        self.file_tree.bind("<Double-Button-1>", self.on_double_click)
        
        self.selected_files = set()
        
        # Operations panel
        ops_panel = ttk.Frame(content_frame)
        ops_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        # View options
        view_frame = ttk.LabelFrame(ops_panel, text="View Options")
        view_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(view_frame, text="View Full Screen", command=self.view_fullscreen_metadata, width=20).pack(pady=2)
        ttk.Button(view_frame, text="Quick Preview", command=self.quick_preview, width=20).pack(pady=2)
        
        # Edit options
        edit_frame = ttk.LabelFrame(ops_panel, text="Edit Options")
        edit_frame.pack(fill=tk.X, pady=5)
        
        self.edit_mode = tk.StringVar(value="selected")
        ttk.Radiobutton(edit_frame, text="Selected Only", variable=self.edit_mode, value="selected").pack(anchor=tk.W)
        ttk.Radiobutton(edit_frame, text="All Files", variable=self.edit_mode, value="all").pack(anchor=tk.W)
        
        ttk.Button(edit_frame, text="Add/Modify Field", command=self.bulk_add_edit_field, width=20).pack(pady=2)
        ttk.Button(edit_frame, text="Delete Field", command=self.bulk_delete_field, width=20).pack(pady=2)
        ttk.Button(edit_frame, text="Social Media Ready", command=self.bulk_social_media, width=20).pack(pady=2)
        ttk.Button(edit_frame, text="Wipe All Metadata", command=self.bulk_wipe_all, width=20).pack(pady=2)
        
        # Backup/Restore
        backup_frame = ttk.LabelFrame(ops_panel, text="Backup/Restore")
        backup_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(backup_frame, text="View Backup Folder", command=self.open_backup_folder, width=20).pack(pady=2)
        ttk.Button(backup_frame, text="Restore from JSON", command=self.restore_from_json, width=20).pack(pady=2)
        
        # Quick metadata display
        meta_frame = ttk.LabelFrame(ops_panel, text="Quick View")
        meta_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.bulk_meta_text = scrolledtext.ScrolledText(meta_frame, width=40, height=10, wrap=tk.WORD, state=tk.DISABLED, font=("Courier", 9))
        self.bulk_meta_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress bar
        progress_frame = ttk.Frame(self.bulk_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=2)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(anchor=tk.W)
    
    def select_single_file(self):
        filetypes = [("All Images", " ".join(f"*{ext}" for ext in self.image_extensions)), ("All Files", "*.*")]
        file = filedialog.askopenfilename(filetypes=filetypes)
        if file:
            self.single_path_var.set(file)
            self.load_preview(file, self.preview_canvas, (300, 300))
    
    def select_bulk_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.bulk_path_var.set(folder)
            self.load_bulk_files()
    
    def load_bulk_files(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        folder = self.bulk_path_var.get()
        if not folder or not os.path.exists(folder):
            return
            
        threading.Thread(target=self._load_files_thread, args=(folder,), daemon=True).start()
    
    def _load_files_thread(self, folder):
        try:
            root_path = Path(folder)
            root_item = self.file_tree.insert("", "end", text=root_path.name, open=True)
            
            def insert_files(parent_item, path):
                for item in sorted(path.iterdir()):
                    if item.is_dir() and self.recursive_var.get():
                        dir_item = self.file_tree.insert(parent_item, "end", text=item.name, open=False)
                        insert_files(dir_item, item)
                    elif item.is_file() and item.suffix.lower() in self.image_extensions:
                        try:
                            size = item.stat().st_size
                            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"
                            item_id = self.file_tree.insert(parent_item, "end", text=item.name, values=("", size_str, str(item)))
                        except:
                            item_id = self.file_tree.insert(parent_item, "end", text=item.name, values=("", "?", str(item)))
            
            insert_files(root_item, root_path)
            
            file_count = self._count_image_files()
            self.status_label.config(text=f"Loaded {file_count} image files")
            self.selected_files.clear()
            self.update_selected_count()
        except Exception as e:
            self.status_label.config(text=f"Error loading files: {str(e)}")
    
    def _count_image_files(self):
        count = 0
        def count_recursive(item):
            nonlocal count
            if len(self.file_tree.item(item)["values"]) >= 3:
                count += 1
            for child in self.file_tree.get_children(item):
                count_recursive(child)
        
        for root_item in self.file_tree.get_children():
            count_recursive(root_item)
        return count

    def on_tree_click(self, event):
        region = self.file_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.file_tree.identify_column(event.x)
            if column == "#1":
                item = self.file_tree.identify_row(event.y)
                if item:
                    self.toggle_file_selection(item)
                return "break"
    
    def on_double_click(self, event):
        """Double click to view full screen metadata"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            values = item.get("values", [])
            if len(values) >= 3:
                self.view_fullscreen_metadata()
    
    def toggle_file_selection(self, item):
        values = self.file_tree.item(item)["values"]
        if len(values) >= 3:
            file_path = values[2]
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
                self.file_tree.set(item, "Selected", "")
            else:
                self.selected_files.add(file_path)
                self.file_tree.set(item, "Selected", "✓")
            self.update_selected_count()
    
    def select_all_files(self):
        def select_recursive(item):
            values = self.file_tree.item(item)["values"]
            if len(values) >= 3:
                file_path = values[2]
                self.selected_files.add(file_path)
                self.file_tree.set(item, "Selected", "✓")
            for child in self.file_tree.get_children(item):
                select_recursive(child)
        
        for root_item in self.file_tree.get_children():
            select_recursive(root_item)
        self.update_selected_count()
    
    def select_none_files(self):
        def deselect_recursive(item):
            values = self.file_tree.item(item)["values"]
            if len(values) >= 3:
                self.file_tree.set(item, "Selected", "")
            for child in self.file_tree.get_children(item):
                deselect_recursive(child)
        
        for root_item in self.file_tree.get_children():
            deselect_recursive(root_item)
        self.selected_files.clear()
        self.update_selected_count()
    
    def invert_selection(self):
        def invert_recursive(item):
            values = self.file_tree.item(item)["values"]
            if len(values) >= 3:
                file_path = values[2]
                if file_path in self.selected_files:
                    self.selected_files.remove(file_path)
                    self.file_tree.set(item, "Selected", "")
                else:
                    self.selected_files.add(file_path)
                    self.file_tree.set(item, "Selected", "✓")
            for child in self.file_tree.get_children(item):
                invert_recursive(child)
        
        for root_item in self.file_tree.get_children():
            invert_recursive(root_item)
        self.update_selected_count()
    
    def update_selected_count(self):
        count = len(self.selected_files)
        self.selected_count_label.config(text=f"{count} selected")
        total = self._count_image_files()
        self.status_label.config(text=f"{total} files loaded, {count} selected")
    
    def on_file_select(self, event):
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = self.file_tree.item(selection[0])
        values = item.get("values", [])
        
        if len(values) >= 3:
            file_path = values[2]
            if os.path.exists(file_path):
                threading.Thread(target=self._load_quick_metadata, args=(file_path,), daemon=True).start()
    
    def _load_quick_metadata(self, file_path):
        try:
            metadata = self.exif.get_all_metadata(file_path)
            # Show summary in quick view
            summary = f"File: {os.path.basename(file_path)}\n"
            summary += f"Fields: {len(metadata)}\n\n"
            
            # Show key fields
            key_fields = ['Title', 'Description', 'Keywords', 'Creator', 'Copyright', 'DateTimeOriginal']

            for field in key_fields:
                if field in metadata:
                    summary += f"{field}: {metadata[field]}\n"
            
            self.master.after(0, lambda: self._update_metadata_display(summary, self.bulk_meta_text))
        except Exception as e:
            self.master.after(0, lambda: self._update_metadata_display(f"Error: {str(e)}", self.bulk_meta_text))
    
    def view_fullscreen_metadata(self):
        """Open full screen metadata viewer"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = self.file_tree.item(selection[0])
        values = item.get("values", [])
        if len(values) < 3:
            messagebox.showwarning("Warning", "Please select a file, not a folder")
            return
        
        file_path = values[2]
        if os.path.exists(file_path):
            FullScreenMetadataViewer(self.master, file_path, self.exif)
    
    def quick_preview(self):
        """Quick preview of selected file"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = self.file_tree.item(selection[0])
        values = item.get("values", [])
        if len(values) >= 3:
            file_path = values[2]
            if os.path.exists(file_path):
                # Create preview window
                preview_win = tk.Toplevel(self.master)
                preview_win.title(f"Preview - {os.path.basename(file_path)}")
                preview_win.geometry("600x600")
                
                canvas = tk.Canvas(preview_win, bg="gray90")
                canvas.pack(fill=tk.BOTH, expand=True)
                
                if Image:
                    try:
                        with Image.open(file_path) as img:
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            canvas.create_image(300, 300, image=photo)
                            canvas.image = photo
                    except Exception as e:
                        canvas.create_text(300, 300, text=f"Error: {str(e)}", font=("Arial", 12), fill="red")
                else:
                    canvas.create_text(300, 300, text="PIL not installed", font=("Arial", 12), fill="gray")
    
    def get_target_files(self):
        """Get files based on edit mode selection"""
        if self.edit_mode.get() == "all":
            files = []
            def collect_files(item):
                values = self.file_tree.item(item)["values"]
                if len(values) >= 3:
                    files.append(values[2])
                for child in self.file_tree.get_children(item):
                    collect_files(child)
            
            for root_item in self.file_tree.get_children():
                collect_files(root_item)
            return files
        else:
            return list(self.selected_files)
    
    def bulk_add_edit_field(self):
        files = self.get_target_files()
        if not files:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Add/Edit Field - {len(files)} files")
        dialog.geometry("600x500")
        dialog.transient(self.master)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Apply to {len(files)} files", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Field Name frame
        field_frame = ttk.Frame(dialog)
        field_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(field_frame, text="Choose Field Name from dropdown list:").pack(anchor=tk.W)
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(field_frame, textvariable=field_var, values=[
        'Make', 'Model', 'ISO', 'FNumber', 'ExposureTime', 'GPSCoordinates',
        'Headline', 'Caption-Abstract', 'Keywords', 'Credit', 'Source', 'Copyright',
        'Title', 'Description', 'Creator', 'Rights', 'Subject', 'Rating', 'Artist'
        ])
        field_combo.pack(fill=tk.X, pady=2)

        # Category frame 
        cat_frame = ttk.Frame(dialog)
        cat_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(cat_frame, text="Choose Category (Optional) from dropdown list:").pack(anchor=tk.W)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(cat_frame, textvariable=category_var, values=['', 'XMP', 'IPTC', 'EXIF'])
        category_combo.pack(fill=tk.X, pady=2)

        
        # Add category descriptions
        info_frame = ttk.LabelFrame(cat_frame, text="Category Use Cases", padding=5)
        info_frame.pack(fill=tk.X, pady=5)
        
        for cat, desc in METADATA_INFO.items():
            ttk.Label(info_frame, text=f"• {cat}: {desc}", font=("Arial", 8), wraplength=550).pack(anchor=tk.W)
        
        ttk.Label(dialog, text="Value:").pack(pady=5)
        value_text = scrolledtext.ScrolledText(dialog, height=10, wrap=tk.WORD)
        value_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def apply_changes():
            field = field_var.get().strip()
            category = category_var.get().strip()
            value = value_text.get("1.0", tk.END).strip()
            
            if not field or not value:
                messagebox.showwarning("Warning", "Field name and value are required")
                return
            
            if askyesno("Confirm", f"Apply '{field}' to {len(files)} files?"):
                dialog.destroy()
                bulk_name = f"bulk_edit_{field}"
                self.run_batch(self.exif.add_or_edit_metadata, files, 
                             {"field": field, "value": value, "category": category, "backup": True},
                             bulk_name)
        
        ttk.Button(btn_frame, text="Apply", command=apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def bulk_delete_field(self):
        files = self.get_target_files()
        if not files:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Delete Field - {len(files)} files")
        dialog.geometry("400x400")
        dialog.transient(self.master)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Delete from {len(files)} files", font=("Arial", 10, "bold")).pack(pady=10, padx=20, anchor=tk.W)
        
        ttk.Label(dialog, text="Field to delete:").pack(pady=5, padx=20, anchor=tk.W)
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(dialog, textvariable=field_var, values=[
        'Make', 'Model', 'ISO', 'FNumber', 'ExposureTime', 'GPSCoordinates',
        'Headline', 'Caption-Abstract', 'Keywords', 'Credit', 'Source', 'Copyright',
        'Title', 'Description', 'Creator', 'Rights', 'Subject', 'Rating', 'Artist'
        ])
        field_combo.pack(pady=5, fill=tk.X, padx=20)
        
        # Category frame with info
        cat_frame = ttk.Frame(dialog)
        cat_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(cat_frame, text="Category (optional):").pack(anchor=tk.W)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(cat_frame, textvariable=category_var, values=['', 'XMP', 'IPTC', 'EXIF'])
        category_combo.pack(fill=tk.X, pady=2)
        
        # Add category descriptions
        info_frame = ttk.LabelFrame(cat_frame, text="Category Info", padding=5)
        info_frame.pack(fill=tk.X, pady=5)
        
        for cat, desc in METADATA_INFO.items():
            ttk.Label(info_frame, text=f"• {cat}: {desc}", font=("Arial", 8), wraplength=350).pack(anchor=tk.W)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        def delete_field():
            field = field_var.get().strip()
            category = category_var.get().strip()
            
            if not field:
                messagebox.showwarning("Warning", "Field name is required")
                return
            
            if askyesno("Confirm Delete", f"Delete '{field}' from {len(files)} files?"):
                dialog.destroy()
                bulk_name = f"bulk_delete_{field}"
                self.run_batch(self.exif.delete_metadata, files, 
                             {"field": field, "category": category, "backup": True},
                             bulk_name)
        
        ttk.Button(btn_frame, text="Delete", command=delete_field).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def bulk_social_media(self):
        files = self.get_target_files()
        if not files:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        if askyesno("Confirm", f"Make {len(files)} images social media ready?"):
            self.run_batch(self.exif.make_social_media_ready, files, 
                          {"backup": True}, "bulk_social_media")
    
    def bulk_wipe_all(self):
        files = self.get_target_files()
        if not files:
            messagebox.showwarning("Warning", "No files selected")
            return
        
        if askyesno("WARNING", f"Wipe ALL metadata from {len(files)} images?\nThis removes everything!"):
            self.run_batch(self.exif.wipe_all_metadata, files, 
                          {"backup": True}, "bulk_wipe_all")
    
    def open_backup_folder(self):
        backup_dir = Path("./Backup")
        if not backup_dir.exists():
            backup_dir.mkdir(exist_ok=True)
        
        if os.name == 'nt':  # Windows
            os.startfile(backup_dir)
        elif os.name == 'posix':  # macOS and Linux
            subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', backup_dir])
    
    def restore_from_json(self):
        filetypes = [("JSON files", "*.json"), ("All files", "*.*")]
        json_file = filedialog.askopenfilename(filetypes=filetypes, initialdir="./Backup")
        
        if json_file:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                original_file = backup_data.get("original_file")
                if original_file and os.path.exists(original_file):
                    if askyesno("Restore", f"Restore metadata to:\n{original_file}?"):
                        success = self.exif.restore_metadata_from_json(json_file)
                        if success:
                            messagebox.showinfo("Success", "Metadata restored successfully!")
                        else:
                            messagebox.showerror("Error", "Failed to restore metadata")
                else:
                    # Ask for target file
                    target = filedialog.askopenfilename(
                        title="Select target image file",
                        filetypes=[("Images", " ".join(f"*{ext}" for ext in self.image_extensions))]
                    )
                    if target:
                        success = self.exif.restore_metadata_from_json(json_file, target)
                        if success:
                            messagebox.showinfo("Success", "Metadata restored successfully!")
                        else:
                            messagebox.showerror("Error", "Failed to restore metadata")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read backup: {str(e)}")
    
    def run_batch(self, operation, files, args=None, bulk_name=None):
        if args is None:
            args = {"backup": True}
        
        def progress_callback(current, total, file):
            progress = (current / total) * 100
            self.progress_var.set(progress)
            filename = os.path.basename(file)
            self.status_label.config(text=f"Processing ({current}/{total}): {filename}")
            self.master.update_idletasks()
        
        def batch_complete(results):
            success_count = sum(results.values())
            failed_count = len(results) - success_count
            
            self.progress_var.set(0)
            self.status_label.config(text=f"Complete: {success_count} successful, {failed_count} failed")
            
            if failed_count > 0:
                messagebox.showwarning("Batch Complete", 
                                      f"Successful: {success_count}/{len(files)}\nFailed: {failed_count}")
            else:
                messagebox.showinfo("Success", f"All {success_count} files processed successfully!")
        
        def batch_thread():
            results = self.exif.batch_operation(files, operation, args, progress_callback, bulk_name)
            self.master.after(0, lambda: batch_complete(results))
        
        threading.Thread(target=batch_thread, daemon=True).start()
    
    def load_preview(self, file_path, canvas, size):
        canvas.delete("all")
        
        if Image is None:
            canvas.create_text(size[0]//2, size[1]//2, text="Preview unavailable", font=("Arial", 10), fill="gray")
            return
        
        try:
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.thumbnail(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                canvas.create_image(size[0]//2, size[1]//2, image=photo)
                canvas.image = photo
        except Exception as e:
            canvas.create_text(size[0]//2, size[1]//2, text=f"Preview error:\n{str(e)}", font=("Arial", 9), fill="red")
    
    def single_view_metadata(self):
        file = self.single_path_var.get()
        if not file or not os.path.exists(file):
            return
            
        threading.Thread(target=self._load_single_metadata, args=(file,), daemon=True).start()
    
    def _load_single_metadata(self, file):
        try:
            metadata = self.exif.get_all_metadata(file)
            formatted = json.dumps(metadata, indent=2, ensure_ascii=False)
            self.master.after(0, lambda: self._update_metadata_display(formatted, self.single_meta_text))
        except Exception as e:
            self.master.after(0, lambda: self._update_metadata_display(f"Error: {str(e)}", self.single_meta_text))
    
    def _update_metadata_display(self, text, widget):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)
    
    def single_add_edit(self):
        file = self.single_path_var.get()
        if not file or not os.path.exists(file):
            messagebox.showwarning("Warning", "Please select a valid file first")
            return
        self._show_metadata_editor(file)
    
    def single_delete(self):
        file = self.single_path_var.get()
        if not file or not os.path.exists(file):
            messagebox.showwarning("Warning", "Please select a valid file first")
            return
        self._show_metadata_deleter(file)
    
    def single_social_media_ready(self):
        file = self.single_path_var.get()
        if not file:
            return
        self._process_single_file(file, self.exif.make_social_media_ready, "social media ready")
    
    def single_wipe_all(self):
        file = self.single_path_var.get()
        if not file:
            return
        if askyesno("Warning", "Wipe ALL metadata? This removes everything including copyright!"):
            self._process_single_file(file, self.exif.wipe_all_metadata, "wiped")
    
    def _process_single_file(self, file_path, operation, operation_name):
        try:
            success = operation(file_path)
            if success:
                messagebox.showinfo("Success", f"File {operation_name} successfully!")
                self.single_view_metadata()
            else:
                messagebox.showwarning("Warning", "Operation may not have completed successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {str(e)}")
    
    def _show_metadata_editor(self, file_path):
        dialog = tk.Toplevel(self.master)
        dialog.title("Add/Edit Metadata")
        dialog.geometry("600x550")
        dialog.transient(self.master)
        dialog.grab_set()

        # Field Name frame
        field_frame = ttk.Frame(dialog)
        field_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(field_frame, text="Choose Field Name from dropdown list:").pack(anchor=tk.W)
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(field_frame, textvariable=field_var, values=[
        'Make', 'Model', 'ISO', 'FNumber', 'ExposureTime', 'GPSCoordinates',
        'Headline', 'Caption-Abstract', 'Keywords', 'Credit', 'Source', 'Copyright',
        'Title', 'Description', 'Creator', 'Rights', 'Subject', 'Rating', 'Artist'
        ])
        field_combo.pack(fill=tk.X, pady=2)

        # Category frame 
        cat_frame = ttk.Frame(dialog)
        cat_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(cat_frame, text="Choose Category (Optional) from dropdown list:").pack(anchor=tk.W)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(cat_frame, textvariable=category_var, values=['', 'XMP', 'IPTC', 'EXIF'])
        category_combo.pack(fill=tk.X, pady=2)
        
        # Add category descriptions
        info_frame = ttk.LabelFrame(cat_frame, text="Category Use Cases", padding=5)
        info_frame.pack(fill=tk.X, pady=5)
        
        for cat, desc in METADATA_INFO.items():
            ttk.Label(info_frame, text=f"• {cat}: {desc}", font=("Arial", 8), wraplength=550).pack(anchor=tk.W)
        
        ttk.Label(dialog, text="Value:").pack(pady=5)
        value_text = scrolledtext.ScrolledText(dialog, height=10, wrap=tk.WORD)
        value_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def apply_changes():
            field = field_var.get().strip()
            category = category_var.get().strip()
            value = value_text.get("1.0", tk.END).strip()
            
            if not field or not value:
                messagebox.showwarning("Warning", "Field name and value are required")
                return
            
            try:
                success = self.exif.add_or_edit_metadata(file_path, field, value, category)
                if success:
                    messagebox.showinfo("Success", "Metadata updated successfully!")
                    dialog.destroy()
                    self.single_view_metadata()
                else:
                    messagebox.showwarning("Warning", "Operation may not have completed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {str(e)}")
        
        ttk.Button(btn_frame, text="Apply", command=apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def _show_metadata_deleter(self, file_path):
        dialog = tk.Toplevel(self.master)
        dialog.title("Delete Metadata Field")
        dialog.geometry("400x400")
        dialog.transient(self.master)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Field to delete:").pack(pady=10, padx=20, anchor=tk.W)
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(dialog, textvariable=field_var, values=[
        'Make', 'Model', 'ISO', 'FNumber', 'ExposureTime', 'GPSCoordinates',
        'Headline', 'Caption-Abstract', 'Keywords', 'Credit', 'Source', 'Copyright',
        'Title', 'Description', 'Creator', 'Rights', 'Subject', 'Rating', 'Artist'
        ])
        field_combo.pack(pady=5, fill=tk.X, padx=20)
        
        # Category frame with info
        cat_frame = ttk.Frame(dialog)
        cat_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(cat_frame, text="Category (optional):").pack(anchor=tk.W)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(cat_frame, textvariable=category_var, values=['', 'XMP', 'IPTC', 'EXIF'])
        category_combo.pack(fill=tk.X, pady=2)
        
        # Add category descriptions
        info_frame = ttk.LabelFrame(cat_frame, text="Category Info", padding=5)
        info_frame.pack(fill=tk.X, pady=5)
        
        for cat, desc in METADATA_INFO.items():
            ttk.Label(info_frame, text=f"• {cat}: {desc}", font=("Arial", 8), wraplength=350).pack(anchor=tk.W)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        def delete_field():
            field = field_var.get().strip()
            category = category_var.get().strip()
            
            if not field:
                messagebox.showwarning("Warning", "Field name is required")
                return
            
            try:
                success = self.exif.delete_metadata(file_path, field, category)
                if success:
                    messagebox.showinfo("Success", "Field deleted successfully!")
                    dialog.destroy()
                    self.single_view_metadata()
                else:
                    messagebox.showwarning("Warning", "Field may not have existed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {str(e)}")
        
        ttk.Button(btn_frame, text="Delete", command=delete_field).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

def main():
    """Main function to run the GUI application"""
    import sys
    root = tk.Tk()
    try:
        app = MetadataManagerGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Critical Error", f"Failed to initialize application:\n{str(e)}")

if __name__ == "__main__":
    main()