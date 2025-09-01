# Image Metadata Manager 🖼️

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
pip install piexif
pip install exifread
pip install pillow-heif  # For HEIC support
pip install tkinter       # Usually comes with Python
```

### Installation Steps
1. Clone or download the repository
2. Install required dependencies
3. Run the application:

```bash
python InatallRequirnmens.py
python main.py
```

## Usage Guide

### Starting the Application
1. Launch the application
2. Choose between Single Image or Bulk Processing mode
3. Select your target images or folders

### Single Image Mode
1. Click "Browse Image" to select an image file
2. View metadata in the left panel
3. Edit fields directly in the metadata viewer
4. Use "Add Field" to insert new metadata
5. Click "Save Changes" to apply modifications

### Bulk Processing Mode
1. Click "Select Folder" to choose a directory
2. Enable "Include Subfolders" for recursive processing
3. Preview all images that will be processed
4. Choose bulk operations:
   - Remove all metadata
   - Add specific fields to all images
   - Modify existing fields across all images
5. Click "Process All" to execute

### Metadata Operations

#### Viewing Metadata
- All metadata categories are displayed in expandable tree view
- Categories include: EXIF, IPTC, XMP, File Info
- Values are editable directly in the interface

#### Adding Metadata
- Click "Add New Field" button
- Select metadata category (EXIF, IPTC, XMP)
- Enter field name and value
- Click "Add" to insert

#### Removing Metadata
- **Single Field**: Right-click field and select "Delete"
- **Category**: Right-click category and select "Remove All"
- **Complete Strip**: Use "Remove All Metadata" button

### Advanced Features

#### Safety Features
- **Automatic Backups**: Original files backed up to `.backup` folder
- **Undo Function**: Restore from backup if needed
- **Dry Run Mode**: Preview changes without applying them

## File Structure
```
MetaData-Remover/
│
├── main.py                      # Main application file
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── InstallRequirnments.py       # Install dependencies from req.txt
└── backups/                     # Automatic backups folder
```

## Keyboard Shortcuts
- `Ctrl+O`: Open image/folder
- `Ctrl+S`: Save changes
- `Ctrl+Z`: Undo last operation
- `Ctrl+R`: Refresh metadata view
- `Delete`: Remove selected metadata field
- `F5`: Refresh file list

## Troubleshooting

### Common Issues
1. **"Permission Denied" Error**: Run as administrator or check file permissions
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
