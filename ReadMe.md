# 🖼️ Image Metadata Manager 

A comprehensive GUI-based tool for viewing, editing, adding, and removing metadata from image files. Supports both single image operations and bulk processing with recursive folder scanning.

## Features

### Core Functionality
- **View Metadata**: Display all EXIF, IPTC, and XMP metadata from images
- **Edit Metadata**: Modify existing metadata fields
- **Add Metadata**: Insert new metadata tags and values
- **Remove Metadata**: Delete specific fields or strip all metadata
- **Bulk Operations**: Process multiple images at once
- **Recursive Processing**: Handle entire folder structures including subfolders

### Supported Image Formats
- JPEG/JPG
- TIFF
- PNG (limited metadata support)
- RAW formats (CR2, NEF, ARW, etc.) - read-only for some formats

### Key Features
- **Single Image Mode**: Select and process individual images
- **Bulk Mode**: Select multiple images or entire folders
- **Recursive Option**: Process all images in subfolders when enabled
- **Backup System**: Automatically creates backups before modifying files
- **Preview Functionality**: View images while editing metadata
- **Search & Filter**: Find images by metadata criteria

## Installation

### Prerequisites
- Python 3.9 or higher
- Required Python packages (install via pip):

```bash
pip install Pillow
pip install piexif (Optional)
```

### Installation Steps
1. Clone or download the repository
2. Install required dependencies
3. Run the application:

```bash
Install_Windows_Requirement.bat
Start.bat
```
```bash
chmod +x Install_Linux_Requirement.sh
chmod +x Start.sh
./Install_Linux_Requirement.sh
./Start.sh
```
## Usage Guide

### Single File Mode

1. **Select Image**: Click "Browse" to choose an image file
2. **View Metadata**: Click "View Metadata" to display current metadata
3. **Edit Fields**: Use "Add/Modify" to add or change metadata fields
4. **Delete Fields**: Use "Delete Field" to remove specific metadata
5. **Quick Actions**:
   - "Social Media Ready": Removes GPS, camera model, and other privacy data
   - "Wipe All": Removes all metadata (use with caution)

### Bulk Operations Mode

1. **Select Folder**: Browse to a folder containing images
2. **Configure Options**: 
   - Check "Include Subfolders" for recursive processing
3. **Choose Edit Mode**:
   - "Selected Only": Process only checked files
   - "All Files": Process entire folder
4. **Apply Operations**: Use the same operations as single mode on multiple files

### Metadata Categories

**EXIF (Exchangeable Image Format)**
- Camera technical data: ISO, shutter speed, aperture, GPS coordinates
- Equipment details: Make, Model, lens information
- Use case: Technical photography data, GPS location

**IPTC (International Press Telecommunications Council)**
- Editorial metadata: Headline, caption, keywords, byline
- Professional data: Credit, source, copyright
- Use case: Professional photography, journalism, stock photos

**XMP (Extensible Metadata Platform)**
- Modern extensible format: Description, title, creator, rights
- Adobe standard with flexibility
- Use case: Web publishing, Digital Asset Management (DAM) systems

## Advanced Features

### Full-Screen Metadata Viewer
- **Complete Metadata Display**: View all metadata in formatted JSON
- **Search Functionality**: Filter metadata by field name or value
- **Image Preview**: Thumbnail preview alongside metadata
- **Export Options**: Save metadata as JSON files

### Batch Processing System
- **Multi-threading**: Parallel processing for bulk operations
- **Progress Tracking**: Real-time operation feedback with progress bars
- **Error Recovery**: Continue processing despite individual file errors
- **Smart File Selection**: Select All, Select None, Invert Selection tools

### Backup System
- **JSON-Based Backups**: Metadata backups without file duplication
- **Automatic Protection**: Backups created before any modification
- **Bulk Operation Tracking**: Organized backups with manifest files
- **Restore Functionality**: Restore metadata from JSON backups to original or new files

### Performance Optimizations
- **Memory Efficient**: JSON backups instead of copying entire files
- **Recursive Processing**: Handle entire directory trees
- **Thumbnail Generation**: Optimized image previews
- **Large File Support**: Handle files over standard size limits

## Safety Features

### Automatic Backup Protection
- **Pre-Modification Backups**: Every change automatically creates a backup
- **Timestamped Backups**: Each backup includes date/time for easy identification
- **Reversible Operations**: All changes can be undone using backup restoration
- **Bulk Operation Manifests**: Track all files modified in batch operations

### Privacy Protection
**Social Media Ready Feature** removes sensitive data:
- GPS coordinates and location information
- Camera make, model, and serial numbers
- User comments and maker notes
- Software/tool identification
- Photographer attribution data

### Data Integrity
- **Local Processing**: All operations performed locally, no cloud dependencies
- **Error Handling**: Robust error management with detailed feedback
- **File Validation**: Verify file integrity before processing
- **Safe Overwrite**: Original files preserved through backup system

### User Protection Features
- **Confirmation Dialogs**: Destructive operations require user confirmation
- **Operation Previews**: See what will be changed before applying
- **Selective Processing**: Choose exactly which files and fields to modify
- **Undo Capability**: Restore previous state from JSON backups

## File Structure
```
MetaData-Manager/
│
├── Main.py                            # Main application file
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── Install_Linux_Requirement.sh       # Install dependencies for linux
├── Install_Windows_Requirement.bat    # Install dependencies for Windows
├── Start.bat                          # Start the Program for Windows 
├── Start.sh                           # Start the Program for Linux
├── Backups/                           # Automatic backups folder
└── LICENSE                  
```

## Troubleshooting

### Common Issues
1. **"Permission Denied" Error**: Run as administrator/sudo or check file permissions
2. **Metadata Not Saving**: Ensure image format supports the metadata type
3. **Slow Processing**: Large files or many images may take time - progress bar shows status

### Supported Metadata Types
- **EXIF**: Camera settings, GPS, timestamps
- **IPTC**: Keywords, captions, copyright
- **XMP**: Adobe metadata, custom fields
- **File Properties**: Size, creation date, format

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License
This project is licensed under the MIT License - See LICENSE file for details.
