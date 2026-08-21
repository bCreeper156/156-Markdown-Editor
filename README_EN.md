# 156 Markdown Editor

[中文简体](README.md) · [English](README_EN.md)

> A lightweight Markdown editor designed for a native Win11 experience

## Features

- Real-time outline navigation

- File creation/opening/saving/saving as

- Light/dark theme switching

- Silent saving (Ctrl+S)

## Characteristics
A 25.4MB native WYSIWYG editor that rejects Chromium and uses Tk for its UI.

Employs a hybrid rendering mode of regular expressions and Mistune for greater stability!

This software is specifically designed for Windows x64. Other platforms require the corresponding dependencies to be installed and built before use!

## Building from source code

### 1. Install Python

Please go to the official Python website to download Python 3.11.3, and check the option to add it to your environment variables during installation.

### 2. Install pip dependencies

```bash pip install -r requirements.txt

```
### 3. Install other dependencies

Create a bin folder and place wkhtmltopdf.exe and pandoc.exe inside.

### 4. Using the Build Script

Double-click build.bat (for Windows users) / build.sh (not yet written, for Linux and macOS users)
